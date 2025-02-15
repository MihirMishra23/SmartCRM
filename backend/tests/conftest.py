import pytest
import os
from datetime import datetime
from backend.app import create_app
from backend.app.models.base import db
from backend.app.models.contact import Contact
from backend.app.models.contact_method import ContactMethod
from backend.app.models.email import Email
from backend.app.models.contact_email import ContactEmail
from backend.app.config import Config


@pytest.fixture
def app():
    """Create and configure a test Flask application instance."""

    # Use a test configuration
    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        SECRET_KEY = "test-key"

    app = create_app(TestConfig)

    # Create tables in the test database
    with app.app_context():
        db.create_all()

    yield app

    # Clean up after test
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test CLI runner for the app."""
    return app.test_cli_runner()


@pytest.fixture
def _db(app):
    """Provide the database instance for testing."""
    with app.app_context():
        yield db


@pytest.fixture
def sample_contact(_db):
    """Create a sample contact for testing."""
    contact = Contact()
    contact.name = "Test User"
    contact.company = "Test Company"
    contact.position = "Test Position"
    contact.notes = "Test notes"
    contact.warm = True
    contact.reminder = False

    _db.session.add(contact)
    _db.session.commit()

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

    _db.session.add_all([email_method, phone_method])
    _db.session.commit()

    return contact


@pytest.fixture
def sample_email(_db, sample_contact):
    """Create a sample email for testing."""
    email = Email()
    email.subject = "Test Email"
    email.content = "Test content"
    email.date = datetime.now()
    email.summary = "Test summary"

    _db.session.add(email)
    _db.session.commit()

    # Link email to contact
    contact_email = ContactEmail()
    contact_email.contact_id = sample_contact.id
    contact_email.email_id = email.id

    _db.session.add(contact_email)
    _db.session.commit()

    return email
