import os
from dotenv import load_dotenv

load_dotenv()  # Load from .env file

class Config:
    # SQLAlchemy Database URI format: mysql+pymysql://username:password@host/database_name
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}"
        f"@{os.getenv('MYSQL_HOST')}/{os.getenv('MYSQL_DB')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Disable unnecessary overhead
    SECRET_KEY = os.getenv('SECRET_KEY') or 'd21ffasda-secret-key'
