import pytest
import json
from datetime import datetime, date


@pytest.mark.read_only
def test_get_contacts_empty(session_client):
    """Test getting contacts when database is empty."""
    response = session_client.get("/api/contacts")
    assert response.status_code == 200
    assert len(response.json) > 0  # Base contact exists


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
    result = response.json["data"]  # Access the data field from the response
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
    assert "Missing required fields: name" in response.json["error"]["message"]

    # Test missing contact methods
    data = {"name": "Test User"}
    response = client.post("/api/contacts", json=data, content_type="application/json")
    assert response.status_code == 400
    assert (
        "Missing required fields: contact_methods" in response.json["error"]["message"]
    )

    # Test empty contact methods
    data = {"name": "Test User", "contact_methods": []}
    response = client.post("/api/contacts", json=data, content_type="application/json")
    assert response.status_code == 400
    assert "Contact methods cannot be empty" in response.json["error"]["message"]

    # Test invalid contact method type
    data = {
        "name": "Test User",
        "contact_methods": [{"type": "invalid", "value": "test@example.com"}],
    }
    response = client.post("/api/contacts", json=data, content_type="application/json")
    assert response.status_code == 400
    assert "Invalid contact method type" in response.json["error"]["message"]


@pytest.mark.read_only
def test_get_contact_by_email(session_client, base_contact):
    """Test getting a contact by email."""
    response = session_client.get(f"/api/contacts/lookup/email/base@example.com")
    assert response.status_code == 200
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
    result = response.json
    assert len(result) == 1
    assert result[0]["subject"] == "Base Email"
    assert result[0]["content"] == "Base content"


@pytest.mark.read_only
def test_get_emails_nonexistent_contact(session_client):
    """Test getting emails for a non-existent contact."""
    response = session_client.get("/api/contacts/nonexistent@example.com/emails")
    assert response.status_code == 404
    assert "not found" in response.json["error"].lower()


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
    assert "already" in response.json["error"].lower()
