import pytest
import json
from datetime import datetime, date


def test_get_contacts_empty(client):
    """Test getting contacts when database is empty."""
    response = client.get("/api/contacts")
    assert response.status_code == 200
    assert response.json == []


def test_create_contact(client):
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
    result = response.json
    assert result["name"] == "John Doe"
    assert result["company"] == "Test Corp"
    assert len(result["contact_methods"]) == 2
    assert any(m["value"] == "john@example.com" for m in result["contact_methods"])


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
    assert "Missing required fields" in response.json["error"]

    # Test missing contact methods
    data = {"name": "Test User"}
    response = client.post("/api/contacts", json=data, content_type="application/json")
    assert response.status_code == 400


def test_get_contact_by_email(client, sample_contact):
    """Test getting a contact by email."""
    response = client.get("/api/contacts", query_string={"email": "test@example.com"})
    assert response.status_code == 200
    result = response.json
    assert len(result) == 1
    assert result[0]["name"] == "Test User"
    assert any(m["value"] == "test@example.com" for m in result[0]["contact_methods"])


def test_delete_contact(client, sample_contact):
    """Test deleting a contact."""
    response = client.delete("/api/contacts/test@example.com")
    assert response.status_code == 200

    # Verify contact is deleted
    response = client.get("/api/contacts", query_string={"email": "test@example.com"})
    assert response.status_code == 200
    assert response.json == []


def test_delete_nonexistent_contact(client):
    """Test deleting a non-existent contact."""
    response = client.delete("/api/contacts/nonexistent@example.com")
    assert response.status_code == 404
    assert "not found" in response.json["error"].lower()


def test_get_contact_emails(client, sample_contact, sample_email):
    """Test getting emails for a contact."""
    response = client.get("/api/contacts/test@example.com/emails")
    assert response.status_code == 200
    result = response.json
    assert len(result) == 1
    assert result[0]["subject"] == "Test Email"
    assert result[0]["content"] == "Test content"


def test_get_emails_nonexistent_contact(client):
    """Test getting emails for a non-existent contact."""
    response = client.get("/api/contacts/nonexistent@example.com/emails")
    assert response.status_code == 404
    assert "not found" in response.json["error"].lower()


def test_duplicate_contact_method(client, sample_contact):
    """Test creating a contact with a duplicate contact method."""
    data = {
        "name": "Another User",
        "contact_methods": [
            {
                "type": "email",
                "value": "test@example.com",  # Already used by sample_contact
                "is_primary": True,
            }
        ],
    }
    response = client.post("/api/contacts", json=data, content_type="application/json")
    assert response.status_code == 409  # Conflict
    assert "already" in response.json["error"].lower()
