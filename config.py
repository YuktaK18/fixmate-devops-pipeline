import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'fixmate-super-secret-key-vesit-2026-demo')
    
    # SQLAlchemy configuration
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Uploads configuration
    BASE_DIR = BASE_DIR
    UPLOAD_FOLDER = os.path.abspath(os.getenv('UPLOAD_FOLDER', BASE_DIR / 'var' / 'uploads'))
    DOCUMENTS_FOLDER = os.path.join(UPLOAD_FOLDER, 'documents')
    COMPLAINTS_FOLDER = os.path.join(UPLOAD_FOLDER, 'complaints')
    INVOICES_FOLDER = os.path.join(UPLOAD_FOLDER, 'invoices')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 5 * 1024 * 1024))  # 5 MB
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
    ALLOWED_MIME_TYPES = {'application/pdf', 'image/png', 'image/jpeg'}
    
    # Business Rules (Defaults from SRS)
    COMMISSION_PERCENTAGE = float(os.getenv('COMMISSION_PERCENTAGE', 10.0))
    CANCELLATION_FEE_PERCENTAGE = float(os.getenv('CANCELLATION_FEE_PERCENTAGE', 10.0))
    CANCELLATION_WINDOW_MINUTES = int(os.getenv('CANCELLATION_WINDOW_MINUTES', 15))
    GST_PERCENTAGE = float(os.getenv('GST_PERCENTAGE', 18.0))
    
    # Rate Limiting
    RATELIMIT_DEFAULT = "300 per day; 100 per hour"
    RATELIMIT_STORAGE_URI = "memory://"
    
    # Flask-Login & Cookie Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_HTTPONLY = True
    
    # Demo & Email Configuration
    DEMO_MODE = os.getenv('DEMO_MODE', 'True').lower() in ('true', '1', 't', 'yes')
    MAIL_SERVER = os.getenv('MAIL_SERVER', '')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@fixmate.local')


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'mysql+pymysql://root:@127.0.0.1:3307/fixmate_db?charset=utf8mb4'
    )
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False


class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'TEST_DATABASE_URL',
        'mysql+pymysql://root:@127.0.0.1:3307/fixmate_test_db?charset=utf8mb4'
    )
    # Use temporary or testing upload folder
    UPLOAD_FOLDER = os.path.abspath(Config.BASE_DIR / 'var' / 'test_uploads')
    DOCUMENTS_FOLDER = os.path.join(UPLOAD_FOLDER, 'documents')
    COMPLAINTS_FOLDER = os.path.join(UPLOAD_FOLDER, 'complaints')
    INVOICES_FOLDER = os.path.join(UPLOAD_FOLDER, 'invoices')


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
