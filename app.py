# app.py
from flask import Flask, session
from extensions import db, migrate, login_manager, mail  # Import from extensions
from routes import routes  # Now safe to import
from config import Config
from flask_login import LoginManager
from models import User
import os



app = Flask(__name__)
app.config.from_object(Config)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'd21ffasda-secret-key'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Or your mail server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'cpd@maluktimor.org'
# app.config['MAIL_USERNAME'] = 'joaodorego@maluktimor.org'
# app.config['MAIL_PASSWORD'] = 'tsel jnik ygve uabl'  # use App Password if Private Gmail
# app.config['MAIL_PASSWORD'] = 'dxjp zdhg oyod xept'  # use App Password if Work Gmail
app.config['MAIL_PASSWORD'] = 'kvbm dhsr noqk srnz'  # use App Password if Work Gmail
mail.init_app(app)

db.init_app(app)
migrate.init_app(app, db)
login_manager.init_app(app)
login_manager.login_view = 'routes.login'  # Set the login view for Flask-Login

app.register_blueprint(routes)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()  # Make sure tables are created
    
    # Check if super admin already exists
    if not User.query.filter_by(username='superadmin@maluktimor.org').first():
        super_admin = User(
            username='superadmin@maluktimor.org',
            role='super_admin'
        )
        super_admin.set_password('superadmin')  # default password
        db.session.add(super_admin)
        db.session.commit()
        print("Super Admin created.")
    else:
        print("Super Admin already exists.")