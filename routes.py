from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from models import Event, Report, Employee, User, AuditLog
from flask_login import login_user, login_required, logout_user, login_required, current_user
from functools import wraps
from extensions import db, login_manager, mail
from datetime import date, datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import extract, func
from sqlalchemy.sql import func
from sqlalchemy import desc
from datetime import datetime, timezone
now_utc = datetime.now(timezone.utc)
import csv
import io 
from io import TextIOWrapper
from flask import Response
import random
import string
from flask_mail import Message


routes = Blueprint('routes', __name__)


# Login Required   !!!!!!!!!!!!!!!!!!!!!

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('routes.loginadmin'))
        return f(*args, **kwargs)
    return decorated_function

# Redirect Base "/" to login or employee page based on login status

@routes.route('/base')
def base():
    employees = get_all_employees()
    events = get_all_events()
    return render_template('base.html', employees=employees, events=events)


# ================================= Routes for Home =========================#
@routes.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('routes.login'))


    today = date.today()

    upcoming_events = Event.query.filter(Event.date >= today).order_by(Event.date.asc()).limit(5).all()
    total_user = User.query.count()

    recent_events = Event.query.order_by(Event.date.desc()).limit(5).all()

    top_employees = (
            db.session.query(
                Employee.name,
                db.func.sum(Report.cpd_points).label('total_points')
            )
            .join(Report, Employee.id == Report.employee_id)
            .group_by(Employee.id, Employee.name)  # include Employee.name in group_by
            .order_by(desc('total_points'))        # correct usage
            .limit(5)
            .all()
        )


    return render_template(
        'home.html',
        username=session.get('username'),
        upcoming_events=upcoming_events,
        total_user=total_user,
        top_employees=top_employees,
        recent_events=recent_events
    )
#======================= Routes for login admin/user ===========================#

@routes.route('/', methods=['GET', 'POST'])
def loginadmin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Get user from database using SQLAlchemy
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            session['logged_in'] = True
            session['user_id'] = user.user_id
            session['username'] = user.username
            session['role'] = user.role

            log_action(f"User logged in: {user.username}")

            if user.must_change_password:
                flash("You must change your password before proceeding.", "warning")
                return  redirect(url_for('routes.change_password'))
            return redirect(url_for('routes.home'))
        else:
            flash("Wrong username or password")

    return render_template('login.html')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@routes.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('routes.loginadmin'))

@routes.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('routes.change_password'))

        user_id = session.get('user_id')
        user = User.query.get(user_id)
        if user:
            user.password = generate_password_hash(new_password)
            user.must_change_password = False  # Reset the flag
            db.session.commit()

        flash("Password changed successfully", "success")
        return redirect(url_for('routes.home'))  # or dashboard/home page

    # This line was missing — needed for GET requests
    return render_template('change_password.html')


def generate_random_password(length=8):
    """Generate a random password with letters, digits, and special characters."""
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for _ in range(length))

@routes.route('/reset_password/<int:user_id>', methods=['GET'])
@login_required
def reset_password(user_id):
    user = User.query.get(user_id)
    if user:
        new_password = generate_random_password()
        user.password = generate_password_hash(new_password)
        user.must_change_password = True
        db.session.commit()

        flash(f"Password rest. New password: {new_password}", "info")
        # Optionally, you can send the new password via email
    else:
        flash("User not found!", "danger")
    return redirect(url_for('routes.users'))


#===============================Routes for register users==============================#
@routes.route('/users', methods=['GET'])
@login_required
def users():
    search = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    per_page = 20

    query = User.query.filter(User.username.ilike(f'%{search}%'))
    total = query.count()
    users = query.order_by(User.user_id.asc()).limit(per_page).offset((page - 1) * per_page).all()
    total_pages = (total + per_page - 1) // per_page

    return render_template('register.html',
                           users=users,  # Changed from user=users to users=users
                           search=search,
                           current_page=page,
                           pages=total_pages,
                           total=total)  # Added total for the badge count

@routes.route('/add_users', methods=['POST'])
@login_required
def add_users():
    username = request.form.get('username')
    role = request.form.get('role')

    # Generate a random password
    generated_password = generate_random_password()
    hashed_password = generate_password_hash(generated_password)

    new_user = User(
        username=username,
        password=hashed_password,
        role=role,
        must_change_password=True  # force change on first login
    )

    db.session.add(new_user)
    db.session.commit()

    # Show the password on screen or send via email (you choose)
    flash(f"User added successfully. Temporary password: {generated_password}", "info")
    log_action(f"Added user: {username} with role: {role}")
    return redirect(url_for('routes.users'))


@routes.route('/edit_users/<int:user_id>', methods=['GET'])
@login_required
def edit_users(user_id):
    user = User.query.get(user_id)
    log_action(f"Accessed edit page for user: {user.username} (ID: {user.user_id})")
    return render_template('edit_users.html', user=user)


@routes.route('/update_users/<int:user_id>', methods=['POST'])
@login_required
def update_users(user_id):
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    role = request.form.get('role')

    if password != confirm_password:
        flash('Passwords do not match!', 'danger')
        return redirect(url_for('routes.edit_users', user_id=user_id))

    user = User.query.get(user_id)
    if user:
        user.username = username
        user.password = password
        user.role = role
        db.session.commit()
        log_action(f"Updated user: {username} (ID: {user.user_id})")
    return redirect(url_for('routes.users'))


@routes.route('/delete_users/<int:user_id>', methods=['GET'])
@login_required
def delete_users(user_id):
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        log_action(f"Deleted user: {user.username} (ID: {user.user_id})")
    return redirect(url_for('routes.users'))



def get_users_by_username(username):
    return User.query.filter_by(username=username).first()

def get_all_users():
    return User.query.all()

def get_users_by_id(user_id):
    return User.query.get(user_id)

def update_users(user_id, username, password, role):
    user = User.query.get(user_id)
    if user:
        user.username = username
        user.password = password
        user.role = role
        db.session.commit()

def delete_users_from_db(user_id):
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()

def get_users_paginated(search='', page=1, per_page=5):
    query = User.query.filter(User.username.ilike(f'%{search}%'))
    total = query.count()
    users = query.order_by(User.user_id.asc()).limit(per_page).offset((page - 1) * per_page).all()
    return users, total




#=======================================Routes for employee=============================#
@routes.route('/employee', methods=['GET'])
@login_required
def employee():
    search = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    per_page = 10

    data, total = get_employee_paginated(search, page, per_page)
    total_pages = (total + per_page - 1) // per_page

    return render_template('employee.html',
                           employee=data,
                           total=total,
                           search=search,
                           page=page,
                           pages=total_pages)

@routes.route('/add_employee', methods=['POST'])
@login_required
def add_employee():
    employeeid = request.form.get('employeeid')
    name = request.form.get('name')
    gender = request.form.get('gender')
    email = request.form.get('email')
    add_employee_to_db(employeeid, name, gender, email)
    log_action(f"Added employee: {name} (ID: {employeeid})")
    return redirect(url_for('routes.employee'))

@routes.route('/edit/<int:id>')
def edit_employee(id):
    employee = get_employee_by_id(id)
    log_action(f"Accessed edit page for employee: {employee.name} (ID: {employee.employeeid})")
    return render_template('edit_employee.html', employee=employee)

@routes.route('/update/<int:id>', methods=['POST'])
def update_employee(id):
    employeeid = request.form.get('employeeid')
    name = request.form.get('name')
    gender = request.form.get('gender')
    email = request.form.get('email')
    update_employee_in_db(id, employeeid, name, gender, email)
    log_action(f"Updated employee: {name} (ID: {employeeid})")
    return redirect(url_for('routes.employee'))

@routes.route('/delete/<int:id>')
def delete_employee(id):
    employee = get_employee_by_id(id)
    if employee:
        delete_employee_from_db(id)
        log_action(f"Deleted employee: {employee.name} (ID: {employee.employeeid})")
    return redirect(url_for('routes.employee'))


def get_all_employees():
    return Employee.query.all()

def add_employee_to_db(employeeid, name, gender, email):
    new_employee = Employee(employeeid=employeeid, name=name, gender=gender, email=email)
    db.session.add(new_employee)
    db.session.commit()

def get_employee_by_id(id):
    return Employee.query.get(id)

def update_employee_in_db(id, employeeid, name, gender, email):
    emp = Employee.query.get(id)
    emp.employeeid = employeeid
    emp.name = name
    emp.gender = gender
    emp.email = email
    db.session.commit()

def delete_employee_from_db(id):
    emp = Employee.query.get(id)
    db.session.delete(emp)
    db.session.commit()

def get_employee_paginated(search='', page=1, per_page=5):
    query = Employee.query.filter(
        db.or_(
            Employee.name.like(f"%{search}%"),
            Employee.gender.like(f"%{search}%"),
            Employee.email.like(f"%{search}%")

        )
    ).order_by(Employee.id.desc())

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    return paginated.items, paginated.total




#=================================== Routes events ================================#
@routes.route('/events', methods=['GET'])
@login_required
def events():
    search = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    per_page = 20

    data, total = get_events_paginated(search, page, per_page)
    total_pages = (total + per_page - 1) // per_page

    return render_template('events.html',
                           events=data,
                           total=total,
                           search=search,
                           page=page,
                           pages=total_pages)



def generate_custom_id_event():
    # Randomly choose between 4 and 5 digits
    digit_length = random.choice([4, 5])
    digits = str(random.randint(10**(digit_length-1), 10**digit_length - 1))
    
    letter = random.choice(string.ascii_uppercase)
    position = random.randint(0, len(digits))
    
    return digits[:position] + letter + digits[position:]


@routes.route('/add_events', methods=['POST'])
@login_required
def add_events():
    # Auto-generate a unique id_event
    id_event = generate_custom_id_event()
    
    # Check for duplicate
    while Event.query.get(id_event):
        id_event = generate_custom_id_event()

  
    date = request.form.get('date')
    time = request.form.get('time')
    organizer = request.form.get('organizer')
    cpd_points = request.form.get('cpd_points')
    session_title = request.form.get('session_title')
    session_topic = request.form.get('session_topic')
    session_subtopic = request.form.get('session_subtopic')

    # Create event with SQLAlchemy
    new_event = Event(
        id_event=id_event,
        date=date,
        time=time,
        organizer=organizer,
        cpd_points=cpd_points,
        session_title=session_title,
        session_topic=session_topic,
        session_subtopic=session_subtopic
    )

    db.session.add(new_event)
    db.session.commit()
    log_action(f"Added event: {session_title} (ID: {id_event})")
    return redirect(url_for('routes.events'))


@routes.route('/events/edit/<id_event>', methods=['GET'])
@login_required
def edit_event(id_event):
   
    event = get_event_by_id(id_event)
    log_action(f"Accessed edit page for event: {event.session_title} (ID: {id_event})")
    return render_template('edit_event.html', event=event)

@routes.route('/events/update/<id_event>', methods=['POST'])
@login_required
def update_event(id_event):

    date = request.form.get('date')
    time = request.form.get('time')
    organizer = request.form.get('organizer')
    cpd_points = request.form.get('cpd_points')
    session_title = request.form.get('session_title')
    session_topic = request.form.get('session_topic')
    session_subtopic = request.form.get('session_subtopic')

    update_event_in_db(id_event, date, time, organizer, cpd_points, session_title, session_topic, session_subtopic)

    log_action(f"Updated event: {session_title} (ID: {id_event})")
    return redirect(url_for('routes.events'))

@routes.route('/delete_event/<string:id_event>')
@login_required
def delete_event(id_event):
    delete_event_by_id(id_event)
    return redirect(url_for('routes.events'))


def get_all_events():
    return Event.query.all()

def add_event_to_db(id_event, date, time, organizer, cpd_points, session_title, session_topic, session_subtopic):
    new_event = Event(
        id_event=id_event,
        date=date,
        time=time,
        organizer=organizer,
        cpd_points=cpd_points,
        session_title=session_title,
        session_topic=session_topic,
        session_subtopic=session_subtopic
    )
    db.session.add(new_event)
    db.session.commit()



def get_events_paginated(search='', page=1, per_page=5):
    query = Event.query.filter(
        db.or_(
            Event.session_title.like(f"%{search}%"),
            Event.session_topic.like(f"%{search}%"),
            Event.session_subtopic.like(f"%{search}%")
        )
    ).order_by(Event.date.desc())

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    return paginated.items, paginated.total

def get_event_by_id(id_event):
    return Event.query.filter_by(id_event=id_event).first()

def update_event_in_db(id_event, date, time, organizer, cpd_points, session_title, session_topic, session_subtopic):
    event = Event.query.filter_by(id_event=id_event).first()
    if event:
        event.date = date
        event.time = time
        event.organizer = organizer
        event.cpd_points = cpd_points
        event.session_title = session_title
        event.session_topic = session_topic
        event.session_subtopic = session_subtopic
        db.session.commit()

def delete_event_by_id(id_event):
    event = Event.query.filter_by(id_event=id_event).first()
    if event:
        db.session.delete(event)
        db.session.commit()


# #======================= General Report routes ==============================


@routes.route('/report')
@login_required
def report():
    search = request.args.get('search', '', type=str)
    page = request.args.get('page', 1, type=int)
    per_page = 20

    reports, total, pages = get_report_paginated(search, page, per_page)

    return render_template('reports.html',
                           reports=reports,
                           total=total,
                           page=page,
                           pages=pages,
                           search=search)

@routes.route('/report/delete/<int:id_report>')
def delete_report(id_report):
    delete_report_from_db(id_report)
    log_action(f"Deleted report: {id_report}")
    return redirect(url_for('routes.report'))



#============================================= Routes for participant report =================================#

@routes.route('/general_report', methods=['GET', 'POST'])
def general_report():
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')

    start_date = None
    end_date = None

    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    except ValueError:
        flash('Invalid date format.', 'danger')
        return redirect(url_for('routes.general_report'))

    query = db.session.query(
        Employee.employeeid,
        Employee.name,
        Employee.gender,
        Employee.email,
        func.sum(Report.cpd_points).label('total_points')
    ).join(Report, Employee.id == Report.employee_id)

    if start_date and end_date:
        query = query.filter(Report.date.between(start_date, end_date))

    query = query.group_by(Employee.employeeid, Employee.name, Employee.gender, Employee.email)\
                 .order_by(func.sum(Report.cpd_points).desc())

    data = query.all()

    return render_template(
        'general_report.html',
        data=data,
        start_date=start_date_str,
        end_date=end_date_str
    )


@routes.route('/export_report')
def export_report():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    start_date = None
    end_date = None

    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    except ValueError:
        flash('Invalid date format.', 'danger')
        return redirect(url_for('routes.general_report'))

    query = db.session.query(
        Employee.employeeid,
        Employee.name,
        Employee.gender,
        Employee.email,
        func.sum(Report.cpd_points).label('total_points')
    ).join(Report, Employee.id == Report.employee_id)

    if start_date and end_date:
        query = query.filter(Report.date.between(start_date, end_date))

    query = query.group_by(Employee.employeeid, Employee.name, Employee.email)\
                 .order_by(func.sum(Report.cpd_points).desc())

    data = query.all()

    # Create CSV response
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Employee ID', 'Name', 'Gender', 'Email', 'Total CPD Points'])

    for row in data:
        writer.writerow([row[0], row[1], row[2], row[3], int(row[4]) if row[4] else 0])

    output.seek(0)
    return Response(
        output,
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=general_report_{start_date_str}_to_{end_date_str}.csv'
        }
    )


#========================================== Individual Report ===========================================#

@routes.route('/get_report', methods=['POST'])
def get_report():
    employeeid = request.form['employeeid']
    year = request.form.get('year')

    # Look up the primary key for this employeeid
    employee = Employee.query.filter_by(employeeid=employeeid).first()
    if not employee:
        flash('No such employee ID!', 'danger')
        return redirect(url_for('routes.base'))

    # Build the query using employee_id (the integer PK)
    query = db.session.query(
        Report.id_report,
        Employee.employeeid,  # or Report.employee_id if you want the PK
        Employee.name,
        Employee.gender,
        Employee.email,
        Event.date,
        Report.id_event,
        Event.session_title,
        Event.cpd_points,
        Report.comment
    ).join(Employee, Report.employee_id == Employee.id
    ).join(Event, Report.id_event == Event.id_event
    ).filter(Report.employee_id == employee.id)

    if year:
        query = query.filter(extract('year', Event.date) == int(year))

    individual_reports = query.order_by(Event.date.desc()).all()

    if not individual_reports:
        flash('No reports found for this employee ID or year!', 'warning')
        return redirect(url_for('routes.base'))

    # cpd_points is at index 7
    total_points = sum(int(report[7]) for report in individual_reports)

    year_query = db.session.query(
        extract('year', Event.date).label('year')
    ).join(Report, Report.id_event == Event.id_event
    ).filter(Report.employee_id == employee.id
    ).distinct().order_by(db.desc('year'))

    years = [row.year for row in year_query]

    return render_template(
        'individual_report.html',
        reports=individual_reports,
        total_points=total_points,
        employee_name=employee.name,
        years=years,
        selected_year=int(year) if year else None
    )


def delete_report_from_db(id_report):
    report = Report.query.filter_by(id_report=id_report).first()
    if report:
        db.session.delete(report)
        db.session.commit()

#================ To show date in table form report =============== #
def get_report_paginated(search, page, per_page):
    offset = (page - 1) * per_page
    search_term = f"%{search}%"

    query = db.session.query(
        Report.id_report,
        Report.timestamp,
        Employee.employeeid,  # ✅ show employeeid not employee_id
        Employee.name,
        Employee.gender,
        Event.date,
        Employee.email,
        Report.id_event,
        Event.session_title,
        Event.cpd_points,
        Report.comment
    ).join(Employee, Report.employee_id == Employee.id
    ).join(Event, Report.id_event == Event.id_event
    ).filter(
        db.or_(
            Employee.name.ilike(search_term),
            Employee.email.ilike(search_term),
            Event.session_title.ilike(search_term)
        )
    ).order_by(Report.id_report.desc())

    total = query.count()
    pages = (total + per_page - 1) // per_page
    reports = query.limit(per_page).offset(offset).all()

    return reports, total, pages  # ✅ return 3 values




def count_report(search):
    search_term = f"%{search}%"
    total = db.session.query(Report).filter(
        db.or_(
            Report.name.ilike(search_term),
            db.cast(Report.id_report, db.String).ilike(search_term)
        )
    ).count()
    return total


# #====================================== Routes download report ========================================#



#=============================== Routes for participant to register at event ===============================#

@routes.route('/register_event', methods=['POST'])
def register_event():
    employeeid = request.form['employee_id']  # Get the string employee code
    id_event = request.form['id_event']
    comment = request.form.get('comment', '')

    event = Event.query.filter_by(id_event=id_event).first()
    if not event:
        flash('Event not found!', 'danger')
        return redirect(url_for('routes.base'))

    # Look up employee by code!
    employee = Employee.query.filter_by(employeeid=employeeid).first()
    if not employee:
        flash('Employee not found!', 'danger')
        return redirect(url_for('routes.base'))

    session_title = event.session_title
    cpd_points = event.cpd_points

    # Pass the PK (integer) to save_report!
    success = save_report(employee.id, id_event, session_title, cpd_points, comment)

    if success:
        flash('Event registered successfully!', 'success')
    else:
        flash('Could not register event. Duplicate entry?', 'danger')
    log_action(f"Added report for employee: {employee.name} (ID: {employee.employeeid}) for event: {event.session_title} (ID: {id_event})")
    return redirect(url_for('routes.base'))



def save_report(employee_id, id_event, session_title, cpd_points, comment):
    try:
        # Check for duplicate
        existing = Report.query.filter_by(employee_id=employee_id, id_event=id_event).first()
        if existing:
            flash('You have already registered for this event.', 'warning')
            return False

        # Get employee info
        employee = Employee.query.get(employee_id)
        if not employee:
            flash('Employee ID not found.', 'danger')
            return False

        # Get event info
        event = Event.query.filter_by(id_event=id_event).first()
        if not event:
            flash('Event not found.', 'danger')
            return False

        report = Report(
            employee_id=employee_id,
            email=employee.email,
            name=employee.name,
            date=event.date,
            id_event=id_event,
            session_title=session_title,
            cpd_points=cpd_points,
            comment=comment
        )
        db.session.add(report)
        db.session.commit()
        return True

    except Exception as e:
        db.session.rollback()
        flash('Database error: ' + str(e), 'danger')
        return False


def get_report_by_id(id_report):
    return Report.query.filter_by(id_report=id_report).first()


@routes.route('/export_report_csv')
def export_report_csv():
    # Build your query (add filters if needed)
    query = db.session.query(
        Report.id_report,
        Report.timestamp,
        Report.employee_id,
        Employee.employeeid,
        Employee.name,
        Employee.gender,
        Event.date,
        Employee.email,
        Report.id_event,
        Event.session_title,
        Event.cpd_points,
        Report.comment
    ).join(Employee, Report.employee_id == Employee.id
    ).join(Event, Report.id_event == Event.id_event
    ).order_by(Report.id_report.asc())
    
    reports = query.all()

    # Use StringIO as a file-like buffer
    si = io.StringIO()
    cw = csv.writer(si)
    # Write header
    cw.writerow([
        "Report ID", "Timestamp", "Employee DB ID", "Employee Code",
        "Employee Name", "Employee Gender", "Event Date", "Employee Email", "Event ID",
        "Session Title", "CPD Points", "Comment"
    ])
    # Write rows
    for r in reports:
        cw.writerow([str(field) if field is not None else "" for field in r])

    output = si.getvalue()
    si.close()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=cpd_report.csv"}
    )


def parse_date(date_str):
    for fmt in ("%Y-%m-%d", "%Y-%b-%d", "%Y-%B-%d"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Date format not supported: {date_str}")



@routes.route('/import_report_csv', methods=['POST'])
def import_report_csv():
    if 'csv_file' not in request.files:
        flash('No file uploaded', 'danger')
        return redirect(url_for('routes.report'))

    file = request.files['csv_file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('routes.report'))

    stream = TextIOWrapper(file.stream, encoding='utf-8-sig')
    reader = csv.DictReader(stream)

    imported = 0
    for row in reader:
        try:
            employee = Employee.query.filter_by(employeeid=row['employeeid']).first()
            event = Event.query.filter_by(id_event=row['id_event']).first()
            if not employee or not event:
                continue

            timestamp = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
            event_date = parse_date(row['date'])

            report = Report(
                timestamp=timestamp,
                employee_id=employee.id,
                email=row['email'],
                name=row['name'],
                gender=row['gender'],
                date=event_date,
                id_event=row['id_event'],
                session_title=row['session_title'],
                cpd_points=int(row['cpd_points']),
                comment=row.get('comment', '')
            )
            db.session.add(report)
            imported += 1

        except Exception as e:
            print(f"Error importing row: {row} - {e}")
            continue

    db.session.commit()
    flash(f'Successfully imported {imported} reports', 'success')
    return redirect(url_for('routes.report'))

# This is Routes for sending emails about upcoming events

def send_upcoming_events_email(recipient, events):
    with current_app.app_context():
        # build table rows
        rows = ""
        for event in events:
            date_str = event.date.strftime('%d %B %Y') if hasattr(event.date, 'strftime') else event.date
            time_str = event.time.strftime('%H:%M') if hasattr(event.time, 'strftime') else event.time
            organizer_str = (event.organizer.strforganizer('string')
                             if hasattr(event.organizer, 'strforganizer')
                             else event.organizer)

            rows += f"""
            <tr>
              <td style="padding:8px; border-bottom:1px solid #ddd;">
                <strong>{event.session_title}</strong>
              </td>
              <td style="padding:8px; border-bottom:1px solid #ddd;">
                {date_str} at {time_str}
              </td>
              <td style="padding:8px; border-bottom:1px solid #ddd;">
                {organizer_str}
              </td>
            </tr>
            """

        # styled HTML email body
        html_body = f"""
        <div style="
            font-family: Arial, sans-serif;
            background-color: #f4f6f8;
            padding: 20px;
        ">
          <h2 style="
              color: #2c3e50;
              margin-bottom: 10px;
              border-left: 5px solid #3498db;
              padding-left: 10px;
          ">
            Upcoming CPD Events
          </h2>
          <table style="
              width: 100%;
              border-collapse: collapse;
              background: #ffffff;
              box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          ">
            <thead>
              <tr>
                <th align="left" style="padding:8px; border-bottom:2px solid #3498db;">
                  Title
                </th>
                <th align="left" style="padding:8px; border-bottom:2px solid #3498db;">
                  Date &amp; Time
                </th>
                <th align="left" style="padding:8px; border-bottom:2px solid #3498db;">
                  Organizer
                </th>
              </tr>
            </thead>
            <tbody>
              {rows}
            </tbody>
          </table>
          <p style="
              margin-top: 20px;
              font-size: 16px;
              color: #34495e;
          ">
            Make sure to <strong>register</strong> in time!
            </p>
            <br>
            <footer style="
              margin-top: 20px;
                font-size: 10px;
                color: #7f8c8d;
            ">
            <footer>
            Do not reply to this email, as it is automatically generated.
            </footer>
        </div>
        """

        msg = Message(
            subject="Upcoming CPD Events",
            recipients=[recipient],
            html=html_body,
            sender=current_app.config['MAIL_USERNAME']
        )
        mail.send(msg)


@routes.route('/send_upcoming_emails')
def send_upcoming_emails():
    today = datetime.today().date()
    upcoming_events = Event.query.filter(Event.date >= today).order_by(Event.date).limit(5).all()

    users = User.query.all()
    for user in users:
        send_upcoming_events_email(user.username, upcoming_events)

    return "Emails sent to all users."

@routes.route('/send_email_to_users', methods=['POST'])
@login_required
def send_email_to_users():
    from datetime import datetime
    today = datetime.today().date()

    upcoming_events = Event.query.filter(Event.date >= today).order_by(Event.date).limit(5).all()
    users = User.query.all()

    for user in users:
        send_upcoming_events_email(user.username, upcoming_events)

    flash('Upcoming event emails sent to all users.', 'success')
    return redirect(url_for('routes.home'))

#================================= Audit Log Routes =================================#

def log_action(action):
    if current_user.is_authenticated:
        log = AuditLog(
            user_id=current_user.user_id,
            username=current_user.username,
            action=action,
            ip_address=request.remote_addr
            )
        db.session.add(log)
        db.session.commit()

        # Delete the older logs
        total_logs = AuditLog.query.count()
        if total_logs > 200:
            # Get logs to delete (oldest ones)
            extra_logs = AuditLog.query.order_by(AuditLog.timestamp.asc()).limit(total_logs - 200).all()
            for old_log in extra_logs:
                db.session.delete(old_log)
            db.session.commit()

@routes.route('/audit_log')
@login_required
def audit_log():
    print(f"User role is: {current_user.role}")
    if getattr(current_user, 'role', None) not in ['admin', 'super_admin']:
        return "Access denied", 403

    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    return render_template("audit_log.html", logs=logs)