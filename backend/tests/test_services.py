import pytest
from datetime import datetime, date
from backend.app.services.contact_service import ContactService
from backend.app.services.email_service import EmailService
from backend.app.models.contact import Contact
from backend.app.models.contact_method import ContactMethod
from backend.app.models.email import Email


def test_create_contact_service(_db):
    """Test contact creation through service layer."""
    contact_data = {
        "name": "Service Test User",
        "contact_methods": [
            {"type": "email", "value": "service.test@example.com", "is_primary": True}
        ],
        "company": "Service Corp",
        "position": "Service Tester",
        "notes": "Service test notes",
        "warm": True,
        "reminder": False,
    }

    contact = ContactService.create_contact(contact_data)
    assert contact.name == "Service Test User"
    assert contact.company == "Service Corp"
    assert len(contact.contact_methods) == 1
    assert contact.contact_methods[0].value == "service.test@example.com"


def test_get_contacts_service(_db, sample_contact):
    """Test retrieving contacts through service layer."""
    # Test getting all contacts
    contacts = ContactService.get_contacts()
    assert len(contacts) == 1
    assert contacts[0].name == "Test User"

    # Test filtering by email
    contacts = ContactService.get_contacts(email="test@example.com")
    assert len(contacts) == 1
    assert contacts[0].name == "Test User"

    # Test filtering by company
    contacts = ContactService.get_contacts(company="Test Company")
    assert len(contacts) == 1
    assert contacts[0].name == "Test User"

    # Test filtering with no matches
    contacts = ContactService.get_contacts(email="nonexistent@example.com")
    assert len(contacts) == 0


def test_delete_contact_service(_db, sample_contact):
    """Test contact deletion through service layer."""
    assert ContactService.delete_contact_by_email("test@example.com") is True
    contacts = ContactService.get_contacts()
    assert len(contacts) == 0


def test_delete_nonexistent_contact_service(_db):
    """Test deleting a non-existent contact through service layer."""
    assert ContactService.delete_contact_by_email("nonexistent@example.com") is False


def test_get_contact_by_email_service(_db, sample_contact):
    """Test getting a single contact by email through service layer."""
    contact = ContactService.get_contact_by_email("test@example.com")
    assert contact is not None
    assert contact.name == "Test User"
    assert contact.company == "Test Company"


def test_format_contact_response_service(sample_contact):
    """Test contact response formatting through service layer."""
    formatted = ContactService.format_contact_response(sample_contact)
    assert isinstance(formatted, dict)
    assert formatted["name"] == "Test User"
    assert formatted["company"] == "Test Company"
    assert len(formatted["contact_methods"]) == 2
    assert any(m["value"] == "test@example.com" for m in formatted["contact_methods"])
    assert any(m["value"] == "123-456-7890" for m in formatted["contact_methods"])


def test_get_emails_for_contacts_service(_db, sample_contact, sample_email):
    """Test retrieving emails for contacts through service layer."""
    emails = EmailService.get_emails_for_contacts([sample_contact.id])
    assert len(emails) == 1
    email = emails[0]
    assert hasattr(email, "content")
    assert email.content == "Test content"
    assert hasattr(email, "subject")
    assert email.subject == "Test Email"


def test_format_email_response_service(sample_email):
    """Test email response formatting through service layer."""
    formatted = EmailService.format_email_response(sample_email)
    assert isinstance(formatted, dict)
    assert "subject" in formatted
    assert formatted["subject"] == "Test Email"
    assert "content" in formatted
    assert formatted["content"] == "Test content"
    assert "summary" in formatted
    assert formatted["summary"] == "Test summary"
    assert "date" in formatted


def test_create_contact_validation(_db):
    """Test contact data validation through service layer."""
    # Valid data
    valid_data = {
        "name": "Valid User",
        "contact_methods": [
            {"type": "email", "value": "valid@example.com", "is_primary": True}
        ],
    }
    try:
        contact = ContactService.create_contact(valid_data)
        assert contact.name == "Valid User"
    except ValueError:
        pytest.fail("Valid contact data raised ValueError")

    # Invalid data - missing name
    invalid_data = {
        "contact_methods": [
            {"type": "email", "value": "invalid@example.com", "is_primary": True}
        ]
    }
    with pytest.raises(ValueError):
        ContactService.create_contact(invalid_data)

    # Invalid data - missing contact methods
    invalid_data = {"name": "Invalid User"}
    with pytest.raises(ValueError):
        ContactService.create_contact(invalid_data)


def test_duplicate_contact_method_service(_db, sample_contact):
    """Test handling of duplicate contact methods through service layer."""
    duplicate_data = {
        "name": "Duplicate User",
        "contact_methods": [
            {
                "type": "email",
                "value": "test@example.com",  # Already used by sample_contact
                "is_primary": True,
            }
        ],
    }
    with pytest.raises(ValueError) as exc_info:
        ContactService.create_contact(duplicate_data)
    assert "already associated with another contact" in str(exc_info.value)
