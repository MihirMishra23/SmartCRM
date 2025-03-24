import pytest
import json
from datetime import datetime, date
from unittest.mock import MagicMock, patch
from app.services.email_service import EmailService
from app.models.email import Email
from app.models.contact import Contact
from app.models.contact_method import ContactMethod
from app.models.base import db
import base64
from sqlalchemy.exc import SQLAlchemyError
import logging
from google.oauth2.credentials import Credentials
import os


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
    assert result[0]["sender"]["id"] == base_contact.id
    assert result[0]["sender"]["email"] == base_contact.primary_email
    assert len(result[0]["receivers"]) == 0  # Base email has no receivers in test

    # Verify metadata
    assert response.json["meta"]["total"] == 1
    assert response.json["meta"]["sent_count"] == 1
    assert response.json["meta"]["received_count"] == 0


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
    """Create a mock Gmail service for testing."""
    with patch("googleapiclient.discovery.build") as mock_build:
        # Create a mock service
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Create a test token file
        test_token = {
            "token": "test_token",
            "refresh_token": "test_refresh_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
        }

        with open("test_token.json", "w") as f:
            json.dump(test_token, f)

        yield mock_service

        # Cleanup
        try:
            os.remove("test_token.json")
        except OSError:
            pass


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


class MockCredentials:
    def __init__(self, valid=True, expired=False, refresh_token=False):
        self.valid = valid
        self.expired = expired
        self.refresh_token = refresh_token

    def refresh(self, request):
        pass  # Mock refresh method; no operation needed


@pytest.mark.unit
@patch("googleapiclient.discovery.build")
@patch("os.path.exists")
@patch("builtins.open")
@patch("pickle.load")
@patch("google.oauth2.credentials.Credentials")
def test_authenticate_existing_token(
    mock_credentials_class,
    mock_pickle_load,
    mock_open_file,
    mock_path_exists,
    mock_build,
    email_service,  # Assuming this is a fixture that provides an EmailService instance
):
    """Test authentication with an existing valid token."""

    # Setup mocks
    mock_path_exists.return_value = True

    # Configure the mock Credentials object using MockCredentials
    mock_creds_instance = MockCredentials(
        valid=True, expired=False, refresh_token=False
    )
    mock_credentials_class.return_value = mock_creds_instance

    mock_pickle_load.return_value = mock_creds_instance

    # Configure the mock build function to return a mock service
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Call the function under test
    email_service.authenticate()

    # Verify the authentication flow
    mock_path_exists.assert_called_once_with(email_service.token_path)
    mock_open_file.assert_called_once_with(email_service.token_path, "rb")
    mock_pickle_load.assert_called_once_with(mock_open_file.return_value)
    mock_build.assert_called_once_with("gmail", "v1", credentials=mock_creds_instance)

    # Verify the service was set
    assert email_service.service == mock_service
    assert email_service.creds == mock_creds_instance

    # Ensure that refresh was not called
    assert not mock_creds_instance.refresh.called


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

    email_service.save_emails_to_db(emails, sender=contact)

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


@pytest.mark.read_only
def test_get_emails_with_sender_receiver(session_client, test_session):
    """Test retrieving emails with sender and receiver relationships."""
    # Create sender
    sender = Contact()
    sender.name = "Sender"
    test_session.add(sender)
    method = ContactMethod(
        contact=sender, method_type="email", value="sender@example.com", is_primary=True
    )
    sender.contact_methods.append(method)

    # Create receiver
    receiver = Contact()
    receiver.name = "Receiver"
    test_session.add(receiver)
    method = ContactMethod(
        contact=receiver,
        method_type="email",
        value="receiver@example.com",
        is_primary=True,
    )
    receiver.contact_methods.append(method)

    test_session.commit()

    # Create an email
    email = Email()
    email.subject = "Test Email"
    email.content = "Test Content"
    email.date = date(2024, 1, 1)
    email.sender = sender
    email.receivers.append(receiver)
    test_session.add(email)
    test_session.commit()

    # Test sender's view
    response = session_client.get("/api/contacts/sender@example.com/emails")
    assert response.status_code == 200
    sender_result = response.json["data"]
    assert len(sender_result) == 1
    assert sender_result[0]["sender"]["id"] == sender.id
    assert len(sender_result[0]["receivers"]) == 1
    assert sender_result[0]["receivers"][0]["id"] == receiver.id
    assert response.json["meta"]["sent_count"] == 1
    assert response.json["meta"]["received_count"] == 0

    # Test receiver's view
    response = session_client.get("/api/contacts/receiver@example.com/emails")
    assert response.status_code == 200
    receiver_result = response.json["data"]
    assert len(receiver_result) == 1
    assert receiver_result[0]["sender"]["id"] == sender.id
    assert len(receiver_result[0]["receivers"]) == 1
    assert receiver_result[0]["receivers"][0]["id"] == receiver.id
    assert response.json["meta"]["sent_count"] == 0
    assert response.json["meta"]["received_count"] == 1


@pytest.mark.modifying
def test_sync_contact_emails(client, test_session, mock_gmail_service):
    """Test syncing emails for a contact."""
    # Create sender contact
    sender = Contact()
    sender.name = "Sender"
    test_session.add(sender)
    method = ContactMethod(
        contact=sender, method_type="email", value="sender@example.com", is_primary=True
    )
    sender.contact_methods.append(method)

    # Create receiver contact
    receiver = Contact()
    receiver.name = "Receiver"
    test_session.add(receiver)
    method = ContactMethod(
        contact=receiver,
        method_type="email",
        value="receiver@example.com",
        is_primary=True,
    )
    receiver.contact_methods.append(method)

    test_session.commit()

    # Mock Gmail API response
    mock_gmail_service.users().messages().list().execute.return_value = {
        "messages": [{"id": "123"}]
    }
    mock_gmail_service.users().messages().get().execute.return_value = {
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Test Subject"},
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "receiver@example.com"},
                {"name": "Date", "value": "Mon, 1 Jan 2024 12:00:00 +0000"},
            ],
            "body": {"data": base64.b64encode(b"Test content").decode()},
        }
    }

    # Test syncing
    response = client.post("/api/contacts/sender@example.com/sync-emails")
    assert response.status_code == 200
    assert response.json["status"] == "success"
    assert response.json["meta"]["sent_emails_count"] == 1

    # Verify email was saved correctly
    email = Email.query.first()
    assert email is not None
    assert email.subject == "Test Subject"
    assert email.sender_id == sender.id
    assert len(email.receivers) == 1
    assert email.receivers[0].id == receiver.id


@pytest.mark.modifying
def test_sync_all_emails(client, test_session, mock_gmail_service):
    """Test syncing emails for multiple contacts."""
    logger = logging.getLogger(__name__)
    logger.info("Starting test_sync_all_emails test")

    # Create contacts
    contacts = []
    for i in range(3):
        logger.debug(f"Creating contact {i}")
        contact = Contact()
        contact.name = f"Contact {i}"
        test_session.add(contact)
        method = ContactMethod(
            contact_id=contact.id,
            method_type="email",
            value=f"contact{i}@example.com",
            is_primary=True,
        )
        contact.contact_methods.append(method)
        contacts.append(contact)
    test_session.commit()
    logger.info(f"Created {len(contacts)} test contacts")

    # Mock Gmail API response
    logger.debug("Setting up Gmail API mock responses")
    mock_gmail_service.users().messages().list().execute.return_value = {
        "messages": [{"id": "123"}, {"id": "456"}]
    }
    mock_gmail_service.users().messages().get().execute.side_effect = [
        {
            "payload": {
                "headers": [
                    {"name": "Subject", "value": f"Test Subject {i}"},
                    {"name": "From", "value": "contact0@example.com"},
                    {"name": "To", "value": "contact1@example.com"},
                    {"name": "Date", "value": "Mon, 1 Jan 2024 12:00:00 +0000"},
                ],
                "body": {"data": base64.b64encode(b"Test content").decode()},
            }
        }
        for i in range(2)
    ]
    logger.info("Gmail API mock responses configured")

    # Test syncing with proper Content-Type and empty JSON body
    logger.info("Making sync request to /api/emails/sync")
    response = client.post(
        "/api/emails/sync",
        json={},  # Empty JSON body for no filters
        headers={"Content-Type": "application/json"},
    )
    logger.debug(f"Sync response status code: {response.status_code}")
    logger.debug(f"Sync response data: {response.json}")

    assert response.status_code == 200
    assert response.json["status"] == "success"
    assert response.json["meta"]["email_count"] > 0
    assert response.json["meta"]["contact_count"] == len(contacts)

    # Verify emails were saved correctly
    logger.info("Verifying saved emails")
    emails = Email.query.all()
    logger.debug(f"Found {len(emails)} saved emails")

    assert len(emails) > 0
    for idx, email in enumerate(emails):
        logger.debug(f"Checking email {idx + 1}:")
        logger.debug(f"  - Sender ID: {email.sender_id}")
        logger.debug(f"  - Subject: {email.subject}")
        logger.debug(f"  - Receivers: {[r.id for r in email.receivers]}")

        assert email.sender_id == contacts[0].id  # All from contact0
        assert len(email.receivers) == 1
        assert email.receivers[0].id == contacts[1].id  # All to contact1

    logger.info("Test completed successfully")


@pytest.mark.read_only
def test_search_emails(session_client, test_session):
    """Test searching emails with various filters."""
    # Create test data
    sender = Contact()
    sender.name = "Sender"
    test_session.add(sender)
    method = ContactMethod(
        contact=sender, method_type="email", value="sender@example.com", is_primary=True
    )
    sender.contact_methods.append(method)

    receiver = Contact()
    receiver.name = "Receiver"
    test_session.add(receiver)
    method = ContactMethod(
        contact=receiver,
        method_type="email",
        value="receiver@example.com",
        is_primary=True,
    )
    receiver.contact_methods.append(method)
    test_session.commit()

    # Create test emails
    emails = []
    for i in range(3):
        email = Email()
        email.subject = f"Test Subject {i}"
        email.content = f"Test Content {i}"
        email.date = date(2024, 1, i + 1)
        email.sender = sender
        email.receivers.append(receiver)
        emails.append(email)
    test_session.add_all(emails)
    test_session.commit()

    # Test basic search
    response = session_client.get("/api/emails/search")
    assert response.status_code == 200
    assert len(response.json["data"]) == 3
    assert response.json["meta"]["total"] == 3
    assert not response.json["meta"]["has_more"]

    # Test text search
    response = session_client.get("/api/emails/search?q=Subject 1")
    assert response.status_code == 200
    assert len(response.json["data"]) == 1
    assert "Subject 1" in response.json["data"][0]["subject"]

    # Test date filtering
    response = session_client.get("/api/emails/search?start_date=2024-01-02")
    assert response.status_code == 200
    assert len(response.json["data"]) == 2

    # Test contact filtering
    response = session_client.get(
        f"/api/emails/search?contact_id={sender.id}&is_sender=true"
    )
    assert response.status_code == 200
    assert len(response.json["data"]) == 3

    response = session_client.get(
        f"/api/emails/search?contact_id={receiver.id}&is_sender=false"
    )
    assert response.status_code == 200
    assert len(response.json["data"]) == 3

    # Test pagination
    response = session_client.get("/api/emails/search?limit=2")
    assert response.status_code == 200
    assert len(response.json["data"]) == 2
    assert response.json["meta"]["has_more"]


@pytest.mark.read_only
def test_search_emails_invalid_params(session_client):
    """Test email search with invalid parameters."""
    # Test invalid date format
    response = session_client.get("/api/emails/search?start_date=invalid")
    assert response.status_code == 400
    assert "Invalid parameter format" in response.json["error"]["message"]

    # Test invalid limit
    response = session_client.get("/api/emails/search?limit=invalid")
    assert response.status_code == 400
    assert "Invalid parameter format" in response.json["error"]["message"]


@pytest.mark.read_only
def test_get_email_statistics(session_client, test_session):
    """Test getting email statistics for a contact."""
    # Create test data
    sender = Contact()
    sender.name = "Sender"
    test_session.add(sender)
    method = ContactMethod(
        contact=sender, method_type="email", value="sender@example.com", is_primary=True
    )
    sender.contact_methods.append(method)

    receivers = []
    for i in range(3):
        receiver = Contact()
        receiver.name = f"Receiver {i}"
        test_session.add(receiver)
        method = ContactMethod(
            contact=receiver,
            method_type="email",
            value=f"receiver{i}@example.com",
            is_primary=True,
        )
        receiver.contact_methods.append(method)
        receivers.append(receiver)
    test_session.commit()

    # Create test emails with varying patterns
    # Sender sends multiple emails to different receivers
    for receiver in receivers:
        for _ in range(2):  # Each receiver gets 2 emails
            email = Email()
            email.subject = "Test Email"
            email.content = "Test Content"
            email.date = date(2024, 1, 1)
            email.sender = sender
            email.receivers.append(receiver)
            test_session.add(email)

    # Receivers send some emails back
    for i, receiver in enumerate(receivers):
        for _ in range(i + 1):  # Each receiver sends different number of emails
            email = Email()
            email.subject = "Reply Email"
            email.content = "Reply Content"
            email.date = date(2024, 1, 2)
            email.sender = receiver
            email.receivers.append(sender)
            test_session.add(email)

    test_session.commit()

    # Test statistics endpoint
    response = session_client.get(f"/api/contacts/{sender.id}/email-stats")
    assert response.status_code == 200
    stats = response.json["data"]

    # Verify counts
    assert stats["total_sent"] == 6  # 2 emails to each of 3 receivers
    assert stats["total_received"] == 6  # 1 + 2 + 3 emails from receivers

    # Verify frequent contacts
    assert len(stats["most_frequent_senders"]) <= 5
    assert len(stats["most_frequent_receivers"]) <= 5

    # Verify monthly volume
    assert len(stats["email_volume_by_month"]) > 0

    # Verify metadata
    assert response.json["meta"]["total_emails"] == 12


@pytest.mark.read_only
def test_get_email_statistics_nonexistent_contact(session_client):
    """Test getting email statistics for a non-existent contact."""
    response = session_client.get("/api/contacts/999999/email-stats")
    assert response.status_code == 404
    assert "not found" in response.json["error"]["message"].lower()
