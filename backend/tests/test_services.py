import pytest
from datetime import datetime, date
from backend.app.services.contact_service import ContactService
from backend.app.services.email_service import EmailService
from backend.app.models.contact import Contact
from backend.app.models.contact_method import ContactMethod
from backend.app.models.email import Email


@pytest.mark.modifying
def test_create_contact_service(test_session):
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


@pytest.mark.read_only
def test_get_contacts_service(base_contact):
    """Test retrieving contacts through service layer."""
    # Test getting all contacts
    contacts = ContactService.get_contacts()
    assert len(contacts) >= 1
    assert any(c.name == "Base User" for c in contacts)

    # Test filtering by email
    contacts = ContactService.get_contacts(email="base@example.com")
    assert len(contacts) == 1
    assert contacts[0].name == "Base User"

    # Test filtering by company
    contacts = ContactService.get_contacts(company="Base Company")
    assert len(contacts) == 1
    assert contacts[0].name == "Base User"

    # Test filtering with no matches
    contacts = ContactService.get_contacts(email="nonexistent@example.com")
    assert len(contacts) == 0


@pytest.mark.modifying
def test_delete_contact_service(test_session, sample_contact):
    """Test contact deletion through service layer."""
    assert ContactService.delete_contact_by_email("test@example.com") is True
    contacts = ContactService.get_contacts(email="test@example.com")
    assert len(contacts) == 0


@pytest.mark.read_only
def test_delete_nonexistent_contact_service():
    """Test deleting a non-existent contact through service layer."""
    assert ContactService.delete_contact_by_email("nonexistent@example.com") is False


@pytest.mark.read_only
def test_get_contact_by_email_service(base_contact):
    """Test getting a single contact by email through service layer."""
    contact = ContactService.get_contact_by_email("base@example.com")
    assert contact is not None
    assert contact.name == "Base User"
    assert contact.company == "Base Company"


@pytest.mark.read_only
def test_format_contact_response_service(base_contact):
    """Test contact response formatting through service layer."""
    formatted = ContactService.format_contact_response(base_contact)
    assert isinstance(formatted, dict)
    assert formatted["name"] == "Base User"
    assert formatted["company"] == "Base Company"
    assert len(formatted["contact_methods"]) == 2
    assert any(m["value"] == "base@example.com" for m in formatted["contact_methods"])
    assert any(m["value"] == "111-111-1111" for m in formatted["contact_methods"])


@pytest.mark.read_only
def test_get_emails_for_contacts_service(base_contact, base_email):
    """Test retrieving emails for contacts through service layer."""
    emails = EmailService.get_emails_for_contacts([base_contact.id])
    assert len(emails) >= 1
    email = next(e for e in emails if e.content == "Base content")
    assert hasattr(email, "content")
    assert email.content == "Base content"
    assert hasattr(email, "subject")
    assert email.subject == "Base Email"


@pytest.mark.read_only
def test_format_email_response_service(base_email):
    """Test email response formatting through service layer."""
    formatted = EmailService.format_email_response(base_email)
    assert isinstance(formatted, dict)
    assert "subject" in formatted
    assert formatted["subject"] == "Base Email"
    assert "content" in formatted
    assert formatted["content"] == "Base content"
    assert "summary" in formatted
    assert formatted["summary"] == "Base summary"
    assert "date" in formatted


@pytest.mark.modifying
def test_create_contact_validation(test_session):
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


@pytest.mark.modifying
def test_duplicate_contact_method_service(test_session, base_contact):
    """Test handling of duplicate contact methods through service layer."""
    duplicate_data = {
        "name": "Duplicate User",
        "contact_methods": [
            {
                "type": "email",
                "value": "base@example.com",  # Already used by base_contact
                "is_primary": True,
            }
        ],
    }
    with pytest.raises(ValueError) as exc_info:
        ContactService.create_contact(duplicate_data)
    assert "already associated with another contact" in str(exc_info.value)
