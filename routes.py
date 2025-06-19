from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import Event, Report, Employee, User
from flask_login import login_required, current_user
from functools import wraps
from extensions import db
from sqlalchemy import extract, func
from datetime import datetime
import csv
import io
from flask import Response





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
@routes.route('/home', methods=['GET'])
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('home.html', username=session.get('username'))

#======================= Routes for login admin/user ===========================#

@routes.route('/', methods=['GET', 'POST'])
def loginadmin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Get user from database using SQLAlchemy
        user = User.query.filter_by(username=username, password=password).first()

        if user:
            session['logged_in'] = True
            session['user_id'] = user.user_id
            session['username'] = user.username
            session['role'] = user.role
            return redirect(url_for('routes.home'))
        else:
            flash("Wrong username or password")

    return render_template('login.html')


# Logout Routes



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
    password = request.form.get('password')
    role = request.form.get('role')

    new_user = User(username=username, password=password, role=role)
    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for('routes.users'))


@routes.route('/edit_users/<int:user_id>', methods=['GET'])
@login_required
def edit_users(user_id):
    user = User.query.get(user_id)
    return render_template('edit_users.html', user=user)


@routes.route('/update_users/<int:user_id>', methods=['POST'])
@login_required
def update_users(user_id):
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')

    user = User.query.get(user_id)
    if user:
        user.username = username
        user.password = password
        user.role = role
        db.session.commit()

    return redirect(url_for('routes.users'))


@routes.route('/delete_users/<int:user_id>', methods=['GET'])
@login_required
def delete_users(user_id):
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
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
    email = request.form.get('email')
    add_employee_to_db(employeeid, name, email)
    return redirect(url_for('routes.employee'))

@routes.route('/edit/<int:id>')
def edit_employee(id):
    employee = get_employee_by_id(id)
    return render_template('edit_employee.html', employee=employee)

@routes.route('/update/<int:id>', methods=['POST'])
def update_employee(id):
    employeeid = request.form.get('employeeid')
    name = request.form.get('name')
    email = request.form.get('email')
    update_employee_in_db(id, employeeid, name, email)
    return redirect(url_for('routes.employee'))

@routes.route('/delete/<int:id>')
def delete_employee(id):
    delete_employee_from_db(id)
    return redirect(url_for('routes.employee'))


def get_all_employees():
    return Employee.query.all()

def add_employee_to_db(employeeid, name, email):
    new_employee = Employee(employeeid=employeeid, name=name, email=email)
    db.session.add(new_employee)
    db.session.commit()

def get_employee_by_id(id):
    return Employee.query.get(id)

def update_employee_in_db(id, employeeid, name, email):
    emp = Employee.query.get(id)
    emp.employeeid = employeeid
    emp.name = name
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
            Employee.email.like(f"%{search}%")
        )
    ).order_by(Employee.id.asc())

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




@routes.route('/add_events', methods=['POST'])
@login_required
def add_events():
    id_event = request.form.get('id_event')
    timestamp = request.form.get('timestamp')    
    date = request.form.get('date')
    time = request.form.get('time')
    organizer = request.form.get('organizer')
    cpd_points = request.form.get('cpd_points')
    session_title = request.form.get('session_title')
    session_topic = request.form.get('session_topic')
    session_subtopic = request.form.get('session_subtopic')
    add_event_to_db(id_event, timestamp, date, time, organizer, cpd_points, session_title, session_topic, session_subtopic)
    return redirect(url_for('routes.events'))



@routes.route('/events/edit/<id_event>', methods=['GET'])
@login_required
def edit_event(id_event):
   
    event = get_event_by_id(id_event)
    return render_template('edit_event.html', event=event)

@routes.route('/events/update/<id_event>', methods=['POST'])
@login_required
def update_event(id_event):
    timestamp = request.form.get('timestamp')
    date = request.form.get('date')
    time = request.form.get('time')
    organizer = request.form.get('organizer')
    cpd_points = request.form.get('cpd_points')
    session_title = request.form.get('session_title')
    session_topic = request.form.get('session_topic')
    session_subtopic = request.form.get('session_subtopic')

    update_event_in_db(id_event, timestamp, date, time, organizer, cpd_points, session_title, session_topic, session_subtopic)
    return redirect(url_for('routes.events'))

@routes.route('/delete_event/<int:id_event>')
@login_required
def delete_event(id_event):
    delete_event_by_id(id_event)
    return redirect(url_for('routes.events'))


def get_all_events():
    return Event.query.all()

def add_event_to_db(id_event, timestamp, date, time, organizer, cpd_points, session_title, session_topic, session_subtopic):
    new_event = Event(
        id_event=id_event,
        timestamp=timestamp,
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

def update_event_in_db(id_event, timestamp, date, time, organizer, cpd_points, session_title, session_topic, session_subtopic):
    event = Event.query.filter_by(id_event=id_event).first()
    if event:
        event.timestamp = timestamp
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
#==================================== END ==========================================#


# #======================= General Report routes ==============================


@routes.route('/report')
@login_required
def report():
    search = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    per_page = 20

    data, total = get_report_paginated(search, page, per_page)
    total_pages = (total + per_page - 1) // per_page

    return render_template('reports.html',
                           reports=data,
                           total=total,
                           search=search,
                           page=page,
                           pages=total_pages)



@routes.route('/report/delete/<int:id_report>')
def delete_report(id_report):
    delete_report_from_db(id_report)
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
        Employee.email,
        func.sum(Report.cpd_points).label('total_points')
    ).join(Report, Employee.id == Report.employee_id)

    if start_date and end_date:
        query = query.filter(Report.date.between(start_date, end_date))

    query = query.group_by(Employee.employeeid, Employee.name, Employee.email)\
                 .order_by(func.sum(Report.cpd_points).desc())

    data = query.all()

    return render_template(
        'general_report.html',
        data=data,
        start_date=start_date_str,
        end_date=end_date_str
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
        Report.employee_id,
        Employee.employeeid,
        Employee.name,
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
    ).order_by(Report.id_report.asc())

    reports = query.limit(per_page).offset(offset).all()
    total = query.count()

    return reports, total



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
        "Employee Name", "Event Date", "Employee Email", "Event ID",
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


#================================= Routes for backup event =========================#

# @routes.route('/backup_events', methods=['POST'])
# def backup_events():
#     year = request.form['year']

#     cur = mysql.connection.cursor()
#     cur.execute("""
#         SELECT * FROM events WHERE YEAR(timestamp) = %s
#     """, (year,))
#     events = cur.fetchall()

#     # CSV headers
#     headers = [i[0] for i in cur.description]

#     # Save to CSV

#     si = StringIO()
#     cw = csv.writer(si)
#     cw.writerow(headers)
#     cw.writerows(events)

#     cur.close()

#     return Response(
#         si.getvalue(),
#         mimetype='text/csv',
#         headers={"Content-Disposition": f"attachment;filename=events_backup_{year}.csv"}
#     )



#================================= Routes for import backups =========================#

# @routes.route('/import_backup', methods=['GET', 'POST'])
# def import_backup():
#     if request.method == 'POST':
#         file = request.files['csv_file']
#         if file:
#             filename = secure_filename(file.filename)
#             filepath = os.path.join('backups', filename)
#             file.save(filepath)

#             if filename.endswith('.sql'):
#                 try:
#                     cmd = f'mysql -u root cpd_db < "{filepath}"'
#                     subprocess.call(cmd, shell=True)
#                     flash('SQL backup imported successfully.', 'success')
#                 except Exception as e:
#                     flash(f'Error importing SQL backup: {str(e)}', 'danger')

#             elif filename.endswith('.csv'):
#                 try:
#                     with open(filepath, newline='', encoding='utf-8') as csvfile:
#                         reader = csv.reader(csvfile)
#                         headers = next(reader)  # Skip header row

#                         conn = mysql.connection
#                         cursor = conn.cursor()

#                         for row in reader:
#                             # example for employee table: adjust for your own table/columns
#                             cursor.execute("INSERT INTO employee (id, name, email) VALUES (%s, %s, %s)", row)

#                         conn.commit()
#                         cursor.close()

#                     flash('CSV data imported successfully.', 'success')
#                 except Exception as e:
#                     flash(f'Error importing CSV: {str(e)}', 'danger')

#             else:
#                 flash('Please upload a valid .sql or .csv file.', 'warning')

#         return redirect(url_for('routes.report'))

#     return render_template('import_backup.html')



# ======================= for tracking backend activity ====================================#

# def log_action(user_id, action, table_name, record_id, details=''):
#     cur = mysql.connection.cursor()
#     cur.execute("""
#         INSERT INTO audit_log (id, action, table_name, record_id, details)
#         VALUES (%s, %s, %s, %s, %s)
#     """, (user_id, action, table_name, record_id, details))
#     mysql.connection.commit()
#     cur.close()



# ====================== Routes to view audit logs =================================#
# @routes.route('/audit_log')
# @login_required
# def audit_log():
#     if current_user.role not in ['super_admin']:
#         flash('Access denied.', 'danger')
#         return redirect(url_for('routes.employee'))  # or another page

#     cur = mysql.connection.cursor()
#     cur.execute("""
#         SELECT a.id, u.username, a.action, a.table_name, a.record_id, a.timestamp, a.details
#         FROM audit_log a
#         JOIN users u ON a.id = u.id
#         ORDER BY a.timestamp DESC
#     """)
#     logs = cur.fetchall()
#     cur.close()
#     return render_template('audit_log.html', logs=logs)
