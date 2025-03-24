import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "inbox_manager")

# Email configuration
USER_EMAILS = os.getenv("USER_EMAILS", "").split(",")
GMAIL_TOKEN_PATH = os.getenv("GMAIL_TOKEN_PATH", "gmail_token.json")
GMAIL_CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS_PATH", "gmail_credentials.json")

# Application configuration
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-please-change-in-production")


class Config:
    # Flask
    SECRET_KEY = SECRET_KEY

    # API Keys
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    APIFY_API_KEY = os.environ.get("APIFY_API_KEY")

    # Database
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Email
    USER_EMAILS = USER_EMAILS
    GMAIL_TOKEN_PATH = GMAIL_TOKEN_PATH
    GMAIL_CREDENTIALS_PATH = GMAIL_CREDENTIALS_PATH
