import pytest
import json
from datetime import datetime, date
from unittest.mock import MagicMock, patch
from app.services.email_service import EmailService
from app.models.email import Email
from app.models.contact import Contact
from app.models.base import db


@pytest.mark.read_only
def test_get_contacts_empty(session_client):
    """Test getting contacts when database is empty."""
    response = session_client.get("/api/contacts")
    assert response.status_code == 200
    assert response.json["status"] == "success"
    assert len(response.json["data"]) > 0  # Base contact exists


@pytest.mark.modifying
def test_create_contact(client, test_session):
    """Test creating a new contact."""
    data = {
        "name": "John Doe",
        "contact_methods": [
            {"type": "email", "value": "john@example.com", "is_primary": True},
            {"type": "phone", "value": "123-456-7890", "is_primary": False},
        ],
        "company": "Test Corp",
        "position": "Developer",
        "notes": "Test notes",
        "warm": True,
        "reminder": False,
    }

    response = client.post("/api/contacts", json=data, content_type="application/json")

    assert response.status_code == 201
    assert response.json["status"] == "success"
    result = response.json["data"]
    assert result["name"] == "John Doe"
    assert result["company"] == "Test Corp"
    assert len(result["contact_methods"]) == 2
    assert any(m["value"] == "john@example.com" for m in result["contact_methods"])


@pytest.mark.read_only
def test_create_contact_invalid_data(client):
    """Test creating a contact with invalid data."""
    # Test missing name
    data = {
        "contact_methods": [
            {"type": "email", "value": "test@example.com", "is_primary": True}
        ]
    }
    response = client.post("/api/contacts", json=data, content_type="application/json")
    assert response.status_code == 400
    assert response.json["status"] == "error"
    assert "Missing required fields: name" in response.json["error"]["message"]

    # Test missing contact methods
    data = {"name": "Test User"}
    response = client.post("/api/contacts", json=data, content_type="application/json")
    assert response.status_code == 400
    assert response.json["status"] == "error"
    assert (
        "Missing required fields: contact_methods" in response.json["error"]["message"]
    )

    # Test empty contact methods
    data = {"name": "Test User", "contact_methods": []}
    response = client.post("/api/contacts", json=data, content_type="application/json")
    assert response.status_code == 400
    assert response.json["status"] == "error"
    assert "Contact methods cannot be empty" in response.json["error"]["message"]

    # Test invalid contact method type
    data = {
        "name": "Test User",
        "contact_methods": [{"type": "invalid", "value": "test@example.com"}],
    }
    response = client.post("/api/contacts", json=data, content_type="application/json")
    assert response.status_code == 400
    assert response.json["status"] == "error"
    assert "Invalid contact method type" in response.json["error"]["message"]


@pytest.mark.read_only
def test_get_contact_by_email(session_client, base_contact):
    """Test getting a contact by email."""
    response = session_client.get(f"/api/contacts/lookup/email/base@example.com")
    assert response.status_code == 200
    assert response.json["status"] == "success"
    result = response.json["data"]
    assert len(result) == 1
    assert result[0]["name"] == "Base User"
    assert any(m["value"] == "base@example.com" for m in result[0]["contact_methods"])


@pytest.mark.modifying
def test_delete_contact(client, sample_contact):
    """Test deleting a contact."""
    # Test deletion
    response = client.delete("/api/contacts/test@example.com")
    assert response.status_code == 200
    assert response.json["status"] == "success"
    assert "Contact deleted successfully" in response.json["message"]

    # Verify contact is deleted
    response = client.get("/api/contacts/lookup/email/test@example.com")
    assert response.status_code == 200
    assert response.json["data"] == []


@pytest.mark.read_only
def test_delete_nonexistent_contact(client):
    """Test deleting a non-existent contact."""
    response = client.delete("/api/contacts/nonexistent@example.com")
    assert response.status_code == 404
    assert response.json["status"] == "error"
    assert "not found" in response.json["error"]["message"].lower()


@pytest.mark.read_only
def test_get_contact_emails(session_client, base_contact, base_email):
    """Test getting emails for a contact."""
    response = session_client.get("/api/contacts/base@example.com/emails")
    assert response.status_code == 200
    assert response.json["status"] == "success"
    result = response.json["data"]
    assert len(result) == 1
    assert result[0]["subject"] == "Base Email"
    assert result[0]["content"] == "Base content"


@pytest.mark.read_only
def test_get_emails_nonexistent_contact(session_client):
    """Test getting emails for a non-existent contact."""
    response = session_client.get("/api/contacts/nonexistent@example.com/emails")
    assert response.status_code == 404
    assert response.json["status"] == "error"
    assert "not found" in response.json["error"]["message"].lower()


@pytest.mark.modifying
def test_duplicate_contact_method(client, base_contact):
    """Test creating a contact with a duplicate contact method."""
    data = {
        "name": "Another User",
        "contact_methods": [
            {
                "type": "email",
                "value": "base@example.com",  # Already used by base_contact
                "is_primary": True,
            }
        ],
    }
    response = client.post("/api/contacts", json=data, content_type="application/json")
    assert response.status_code == 409  # Conflict
    assert response.json["status"] == "error"
    assert "already" in response.json["error"]["message"].lower()


# Email Service Tests
@pytest.fixture
def mock_gmail_service():
    with patch("googleapiclient.discovery.build") as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        yield mock_service


@pytest.fixture
def email_service():
    service = EmailService(
        token_path="test_token.pickle", credentials_path="test_credentials.json"
    )
    return service


@pytest.mark.unit
def test_email_service_init(email_service):
    """Test EmailService initialization."""
    assert email_service.token_path == "test_token.pickle"
    assert email_service.credentials_path == "test_credentials.json"
    assert email_service.creds is None
    assert email_service.service is None


@pytest.mark.unit
@patch("os.path.exists")
@patch("builtins.open")
@patch("pickle.load")
@patch("google.oauth2.credentials.Credentials")
def test_authenticate_existing_token(
    mock_creds, mock_pickle, mock_open, mock_exists, email_service
):
    """Test authentication with existing valid token."""
    mock_exists.return_value = True
    mock_creds.valid = True
    mock_pickle.return_value = mock_creds

    email_service.authenticate()

    mock_exists.assert_called_once_with(email_service.token_path)
    mock_open.assert_called_once()
    mock_pickle.assert_called_once()


@pytest.mark.unit
@patch("os.path.exists")
@patch("builtins.open")
@patch("pickle.load")
@patch("google.oauth2.credentials.Credentials")
def test_authenticate_expired_token(
    mock_creds, mock_pickle, mock_open, mock_exists, email_service
):
    """Test authentication with expired token that needs refresh."""
    mock_exists.return_value = True
    mock_creds.valid = False
    mock_creds.expired = True
    mock_creds.refresh_token = True
    mock_pickle.return_value = mock_creds

    email_service.authenticate()

    mock_creds.refresh.assert_called_once()
    assert mock_open.call_count == 2  # One read, one write


@pytest.mark.unit
@patch("os.path.exists")
@patch("google_auth_oauthlib.flow.InstalledAppFlow")
def test_authenticate_new_token(mock_flow, mock_exists, email_service):
    """Test authentication when no token exists."""
    mock_exists.return_value = False
    mock_flow_instance = MagicMock()
    mock_flow.from_client_secrets_file.return_value = mock_flow_instance

    email_service.authenticate()

    mock_flow.from_client_secrets_file.assert_called_once_with(
        email_service.credentials_path, email_service.SCOPES
    )
    mock_flow_instance.run_local_server.assert_called_once_with(port=0)


@pytest.mark.unit
def test_fetch_emails_no_service(email_service):
    """Test fetching emails when Gmail service fails to initialize."""
    email_service.service = None
    with patch.object(email_service, "authenticate") as mock_auth:
        mock_auth.return_value = None
        with pytest.raises(RuntimeError, match="Failed to initialize Gmail service"):
            email_service.fetch_emails()


@pytest.mark.unit
def test_fetch_emails_api_error(email_service, mock_gmail_service):
    """Test handling of Gmail API errors."""
    mock_gmail_service.users().messages().list().execute.side_effect = Exception(
        "API Error"
    )
    email_service.service = mock_gmail_service

    with pytest.raises(RuntimeError, match="Error fetching emails"):
        email_service.fetch_emails()


@pytest.mark.unit
def test_fetch_emails_malformed_response(email_service, mock_gmail_service):
    """Test handling of malformed email data."""
    # Mock response with missing or malformed data
    mock_messages = {"messages": [{"id": "123"}]}
    mock_message_data = {
        "payload": {
            "headers": [],  # Missing headers
            "body": {"data": "invalid_base64"},  # Invalid base64
        }
    }

    mock_gmail_service.users().messages().list().execute.return_value = mock_messages
    mock_gmail_service.users().messages().get().execute.return_value = mock_message_data

    email_service.service = mock_gmail_service
    emails = email_service.fetch_emails()

    assert len(emails) == 1
    assert emails[0]["subject"] == "No Subject"
    assert emails[0]["from"] == "Unknown"
    assert emails[0]["content"] == ""


@pytest.mark.integration
def test_save_emails_to_db(email_service, test_session):
    """Test saving emails to database."""
    # Create test contact
    contact = Contact()
    contact.name = "Test User"
    test_session.add(contact)
    test_session.commit()

    emails = [
        {
            "subject": "Test Email",
            "content": "Test Content",
            "date": "Mon, 1 Jan 2024 12:00:00 +0000",
        }
    ]

    email_service.save_emails_to_db(emails, [contact])

    saved_email = Email.query.first()
    assert saved_email is not None
    assert saved_email.content == "Test Content"
    assert contact in saved_email.contacts


@pytest.mark.integration
def test_save_emails_invalid_date(email_service, test_session):
    """Test saving emails with invalid date format."""
    contact = Contact()
    contact.name = "Test User"
    test_session.add(contact)
    test_session.commit()

    emails = [
        {
            "subject": "Test Email",
            "content": "Test Content",
            "date": "Invalid Date Format",  # Invalid date
        }
    ]

    email_service.save_emails_to_db(emails, [contact])
    saved_emails = Email.query.all()
    assert len(saved_emails) == 0  # Should skip invalid emails


@pytest.mark.integration
def test_save_emails_db_error(email_service, test_session):
    """Test database error handling when saving emails."""
    contact = Contact()
    contact.name = "Test User"
    test_session.add(contact)
    test_session.commit()

    emails = [
        {
            "subject": "Test Email",
            "content": "Test Content",
            "date": "Mon, 1 Jan 2024 12:00:00 +0000",
        }
    ]

    with patch.object(db.session, "commit") as mock_commit:
        mock_commit.side_effect = Exception("Database Error")
        with pytest.raises(RuntimeError, match="Error saving emails to database"):
            email_service.save_emails_to_db(emails, [contact])


@pytest.mark.integration
def test_get_emails_for_nonexistent_contacts(email_service):
    """Test retrieving emails for non-existent contacts."""
    emails = email_service.get_emails_for_contacts([999999])  # Non-existent ID
    assert len(emails) == 0


@pytest.mark.integration
def test_get_emails_with_multiple_contacts(email_service, test_session):
    """Test retrieving emails linked to multiple contacts."""
    # Create two contacts
    contact1 = Contact()
    contact1.name = "User 1"
    contact2 = Contact()
    contact2.name = "User 2"
    test_session.add_all([contact1, contact2])
    test_session.commit()

    # Create an email linked to both contacts
    email = Email()
    email.subject = "Shared Email"
    email.content = "Shared Content"
    email.date = date(2024, 1, 1)
    email.contacts.extend([contact1, contact2])
    test_session.add(email)
    test_session.commit()

    # Test retrieval for each contact
    emails1 = email_service.get_emails_for_contacts([contact1.id])
    emails2 = email_service.get_emails_for_contacts([contact2.id])
    emails_both = email_service.get_emails_for_contacts([contact1.id, contact2.id])

    assert len(emails1) == 1
    assert len(emails2) == 1
    assert len(emails_both) == 1
    assert emails1[0].id == email.id
    assert emails2[0].id == email.id


@pytest.mark.integration
def test_get_emails_for_contacts(email_service, test_session):
    """Test retrieving emails for specific contacts."""
    # Create test data
    contact = Contact()
    contact.name = "Test User"
    test_session.add(contact)
    test_session.commit()

    email = Email()
    email.subject = "Test Email"
    email.content = "Test Content"
    email.date = date(2024, 1, 1)
    email.contacts.append(contact)
    test_session.add(email)
    test_session.commit()

    # Test retrieval
    emails = email_service.get_emails_for_contacts([contact.id])
    assert len(emails) == 1
    assert emails[0].subject == "Test Email"

    # Test retrieval without contact filter
    all_emails = email_service.get_emails_for_contacts()
    assert len(all_emails) == 1


@pytest.mark.unit
def test_format_email_response(email_service):
    """Test email response formatting."""
    email = Email()
    email.id = 1
    email.subject = "Test Email"
    email.content = "Test Content"
    email.summary = "Test Summary"
    email.date = date(2024, 1, 1)

    formatted = email_service.format_email_response(email)
    assert formatted["id"] == 1
    assert formatted["subject"] == "Test Email"
    assert formatted["content"] == "Test Content"
    assert formatted["summary"] == "Test Summary"
    assert formatted["date"] == "2024-01-01"
