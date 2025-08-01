from extensions import db
from datetime import datetime
from sqlalchemy.sql import func
from sqlalchemy import text
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import pytz


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False) 
    must_change_password = db.Column(db.Boolean, default=False, nullable=False)

    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=True)
    employee = db.relationship('Employee', backref='user', uselist=False)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


    def get_id(self):
        return self.user_id

class Employee(db.Model):
    __tablename__ = 'employee'
    id = db.Column(db.Integer, primary_key=True)
    employeeid = db.Column(db.String(50), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    reports = db.relationship('Report', backref='employee', lazy=True)


class Event(db.Model):
    __tablename__ = 'events'

    id_event = db.Column(db.String(10), primary_key=True)
    timestamp = db.Column(
        db.DateTime(timezone=True),
        server_default=text('CURRENT_TIMESTAMP'),
        default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(50), nullable=False)
    organizer = db.Column(db.String(100), nullable=False)
    cpd_points = db.Column(db.Integer, nullable=False)
    session_title = db.Column(db.String(200), nullable=False)
    session_topic = db.Column(db.String(200), nullable=False)
    session_subtopic = db.Column(db.String(200), nullable=False)

    reports = db.relationship('Report', backref='events', lazy=True)

class Report(db.Model):
    __tablename__ = 'report'

    id_report = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(
        db.DateTime(timezone=True),
        server_default=text('CURRENT_TIMESTAMP'),
        default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    date = db.Column(db.Date, nullable=False)
    id_event = db.Column(db.String(10), db.ForeignKey('events.id_event'), nullable=False)
    session_title = db.Column(db.String(50), nullable=False)
    cpd_points = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)


def current_timor_time():
    tz = pytz.timezone('Asia/Dili')
    return datetime.now(tz)
class AuditLog(db.Model):
    __tablename__='audit_log'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(100), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(
        db.DateTime(timezone=True),
        server_default=text('CURRENT_TIMESTAMP'),
        default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    ip_address = db.Column(db.String(50), nullable=False)