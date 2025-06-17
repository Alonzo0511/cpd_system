# models.py
from extensions import db
from sqlalchemy import Column, DateTime, func
from datetime import datetime


class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)

class Employee(db.Model):
    __tablename__ = 'employee'

    id = db.Column(db.Integer, primary_key=True)
    employeeid = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)


class Event(db.Model):
    __tablename__ = 'events'

    id_event = db.Column(db.Integer, primary_key=True)
    timestamp = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    organizer = db.Column(db.String(100), nullable=False)
    cpd_points = db.Column(db.Numeric(10, 2), nullable=False)
    session_title = db.Column(db.String(200), nullable=False)
    session_topic = db.Column(db.String(200), nullable=False)
    session_subtopic = db.Column(db.String(200), nullable=False)

class Report(db.Model):
    __tablename__ = 'report'

    id_report = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    employeeid = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    id_event = db.Column(db.String(50), nullable=False)
    session_title = db.Column(db.String(50), nullable=False)
    cpd_points = db.Column(db.Text, nullable=False)
    comment = db.Column(db.Text, nullable=True)