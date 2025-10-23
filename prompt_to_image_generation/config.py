import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or 'your-secret-key-here'
    MYSQL_HOST = os.getenv('MYSQL_HOST') or 'localhost'
    MYSQL_USER = os.getenv('MYSQL_USER') or 'root'
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD') or ''
    MYSQL_DB = os.getenv('MYSQL_DB') or 'criminal_composite_db'
    UPLOAD_FOLDER = 'static/generated'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}