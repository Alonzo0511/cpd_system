# app.py
from flask import Flask, session
from extensions import db, migrate, login_manager  # Import from extensions
from routes import routes  # Now safe to import
from config import Config




app = Flask(__name__)
app.config.from_object(Config)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/cpd_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'd21ffasda-secret-key'


db.init_app(app)
migrate.init_app(app, db)
login_manager.init_app(app)
login_manager.login_view = 'routes.login'  # Set the login view for Flask-Login

app.register_blueprint(routes)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
