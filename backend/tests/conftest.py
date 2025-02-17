import pytest
import os
import sys
from datetime import datetime
from pathlib import Path
from backend.app import create_app
from backend.app.models.base import db
from backend.app.models.contact import Contact
from backend.app.models.contact_method import ContactMethod
from backend.app.models.email import Email
from backend.app.models.contact_email import ContactEmail
from backend.app.config import Config
from sqlalchemy.orm import scoped_session, sessionmaker

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "test-key"
    GMAIL_TOKEN_PATH = "test_token.pickle"
    GMAIL_CREDENTIALS_PATH = "test_credentials.json"


def create_base_data(session):
    """Create base test data that will persist throughout the test session."""
    # Create a base contact
    base_contact = Contact()
    base_contact.name = "Base User"
    base_contact.company = "Base Company"
    base_contact.position = "Base Position"
    base_contact.notes = "Base notes"
    base_contact.warm = True
    base_contact.reminder = False

    session.add(base_contact)
    session.commit()

    # Add contact methods
    base_email = ContactMethod()
    base_email.contact_id = base_contact.id
    base_email.method_type = "email"
    base_email.value = "base@example.com"
    base_email.is_primary = True

    base_phone = ContactMethod()
    base_phone.contact_id = base_contact.id
    base_phone.method_type = "phone"
    base_phone.value = "111-111-1111"
    base_phone.is_primary = False

    session.add_all([base_email, base_phone])
    session.commit()

    # Create a base email
    base_email_msg = Email()
    base_email_msg.subject = "Base Email"
    base_email_msg.content = "Base content"
    base_email_msg.date = datetime.now()
    base_email_msg.summary = "Base summary"

    session.add(base_email_msg)
    session.commit()

    # Link email to contact
    base_contact_email = ContactEmail()
    base_contact_email.contact_id = base_contact.id
    base_contact_email.email_id = base_email_msg.id

    session.add(base_contact_email)
    session.commit()

    return base_contact, base_email_msg


@pytest.fixture(scope="session")
def app():
    """Create and configure a test Flask application instance for the entire test session."""
    app = create_app(TestConfig)

    # Create tables and session-level test data
    with app.app_context():
        db.create_all()
        create_base_data(db.session)

    yield app

    # Clean up after all tests
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope="session")
def _db(app):
    """Provide the database instance for the entire test session."""
    with app.app_context():
        yield db


@pytest.fixture(scope="session")
def session_client(app):
    """Create a test client for read-only operations that persists across the session."""
    return app.test_client()


@pytest.fixture(scope="function")
def client(app):
    """Create a test client for modifying operations that's recreated for each test."""
    return app.test_client()


@pytest.fixture(scope="function")
def test_session(_db):
    """Create a new database session for a test."""
    connection = _db.engine.connect()
    transaction = connection.begin()

    # Create a session-local transaction
    session_factory = sessionmaker(bind=connection)
    session = scoped_session(session_factory)

    # Store the original session and replace it with our test session
    old_session = _db.session
    _db.session = session

    yield session

    # Cleanup after the test
    _db.session = old_session  # Restore the original session
    session.remove()  # Remove the scoped session
    transaction.rollback()  # Rollback the transaction
    connection.close()  # Close the connection


@pytest.fixture(scope="function")
def sample_contact(test_session):
    """Create a temporary contact for testing that will be rolled back."""
    contact = Contact()
    contact.name = "Test User"
    contact.company = "Test Company"
    contact.position = "Test Position"
    contact.notes = "Test notes"
    contact.warm = True
    contact.reminder = False

    test_session.add(contact)
    test_session.commit()

    # Add contact methods
    email_method = ContactMethod()
    email_method.contact_id = contact.id
    email_method.method_type = "email"
    email_method.value = "test@example.com"
    email_method.is_primary = True

    phone_method = ContactMethod()
    phone_method.contact_id = contact.id
    phone_method.method_type = "phone"
    phone_method.value = "123-456-7890"
    phone_method.is_primary = False

    test_session.add_all([email_method, phone_method])
    test_session.commit()

    return contact


@pytest.fixture(scope="function")
def sample_email(test_session, sample_contact):
    """Create a temporary email for testing that will be rolled back."""
    email = Email()
    email.subject = "Test Email"
    email.content = "Test content"
    email.date = datetime.now()
    email.summary = "Test summary"

    test_session.add(email)
    test_session.commit()

    # Link email to contact
    contact_email = ContactEmail()
    contact_email.contact_id = sample_contact.id
    contact_email.email_id = email.id

    test_session.add(contact_email)
    test_session.commit()

    return email


@pytest.fixture(scope="session")
def base_contact(app, _db):
    """Provide access to the base contact that persists across all tests."""
    with app.app_context():
        contact = Contact.query.filter_by(name="Base User").first()
        return contact


@pytest.fixture(scope="session")
def base_email(app, _db):
    """Provide access to the base email that persists across all tests."""
    with app.app_context():
        email = Email.query.filter_by(subject="Base Email").first()
        return email
