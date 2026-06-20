import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-digital-evidence-integrity-system-secure-key-12903810')
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql+pymysql://root:password@localhost:3306/chainproof_db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Folders for evidence storage
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    ENCRYPTED_FOLDER = os.path.join(BASE_DIR, 'encrypted')
    REPORTS_FOLDER = os.path.join(BASE_DIR, 'reports')
    
    # Security: AES-256 key must be exactly 32 bytes.
    # We will pad/encode the provided key to ensure exact length.
    RAW_ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', 'default-secure-32-byte-aes-key')
    
    # Rate Limits & Upload Restrictions
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB upload limit
    
    # Mail settings
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@digital-evidence-integrity-system-vault.local')
    
    # Allowed categories and file extensions
    ALLOWED_EXTENSIONS = {
        'image': {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'},
        'video': {'mp4', 'mkv', 'avi', 'mov', 'wmv'},
        'audio': {'mp3', 'wav', 'ogg', 'flac', 'aac'},
        'document': {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'csv'},
        'malware': {'exe', 'elf', 'bin', 'dll', 'sys', 'apk'},
        'network': {'pcap', 'pcapng', 'cap'},
        'mobile': {'sqlite', 'db', 'plist', 'xml', 'log'}
    }

    @classmethod
    def init_app(cls, app):
        # Ensure directories exist
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(cls.ENCRYPTED_FOLDER, exist_ok=True)
        os.makedirs(cls.REPORTS_FOLDER, exist_ok=True)
        os.makedirs(os.path.join(app.static_folder, 'qr'), exist_ok=True)
