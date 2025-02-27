import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    
    # API Keys
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    APIFY_API_KEY = os.environ.get('APIFY_API_KEY')
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://localhost/inbox_manager'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Email
    GMAIL_TOKEN_PATH = 'gmail_token.json'
    GMAIL_CREDENTIALS_PATH = 'gmail_credentials.json'
