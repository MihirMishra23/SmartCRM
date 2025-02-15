from flask import Blueprint, jsonify, request
from ..models.contact import Contact
from ..models.contact_method import ContactMethod
from ..models.email import Email
from ..models.base import db
from ..services.email_service import EmailService
from datetime import datetime
from typing import List, Optional
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError
import traceback

api = Blueprint("api", __name__)


class APIError(Exception):
    """Base class for API errors"""

    def __init__(self, message, status_code):
        super().__init__()
        self.message = message
        self.status_code = status_code


class BadRequestError(APIError):
    """400 Bad Request"""

    def __init__(self, message="Bad Request"):
        super().__init__(message, 400)


class ForbiddenError(APIError):
    """403 Forbidden"""

    def __init__(self, message="Forbidden"):
        super().__init__(message, 403)


class NotFoundError(APIError):
    """404 Not Found"""

    def __init__(self, message="Resource not found"):
        super().__init__(message, 404)


class ConflictError(APIError):
    """409 Conflict"""

    def __init__(self, message="Resource already exists"):
        super().__init__(message, 409)


@api.errorhandler(APIError)
def handle_api_error(error):
    response = jsonify({"error": error.message})
    response.status_code = error.status_code
    return response


@api.errorhandler(SQLAlchemyError)
def handle_db_error(error):
    response = jsonify({"error": "Database error occurred", "details": str(error)})
    response.status_code = 500
    return response


@api.errorhandler(Exception)
def handle_generic_error(error):
    response = jsonify({"error": "An unexpected error occurred", "details": str(error)})
    response.status_code = 500
    return response


def validate_contact_data(data):
    if not data:
        raise BadRequestError("No data provided")

    required_fields = ["name"]
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise BadRequestError(f"Missing required fields: {', '.join(missing_fields)}")

    if "contact_methods" in data:
        for method in data["contact_methods"]:
            if "type" not in method or "value" not in method:
                raise BadRequestError("Contact methods must include type and value")


@api.route("/contacts", methods=["GET"])
def get_contacts():
    """Get all contacts"""
    try:
        contacts = Contact.query.all()
        return jsonify(
            [
                {
                    "id": c.id,
                    "name": c.name,
                    "company": c.company,
                    "position": c.position,
                    "last_contacted": (
                        c.last_contacted.isoformat() if c.last_contacted else None
                    ),
                    "follow_up_date": (
                        c.follow_up_date.isoformat() if c.follow_up_date else None
                    ),
                    "warm": c.warm,
                    "reminder": c.reminder,
                    "notes": c.notes,
                    "contact_methods": [
                        {
                            "type": cm.method_type,
                            "value": cm.value,
                            "is_primary": cm.is_primary,
                        }
                        for cm in c.contact_methods
                    ],
                }
                for c in contacts
            ]
        )
    except Exception as e:
        raise BadRequestError(f"Failed to fetch contacts: {str(e)}")


@api.route("/contacts", methods=["POST"])
def create_contact():
    """Create a new contact"""
    data = request.json
    if not data:
        raise BadRequestError("No data provided")

    # Validate input data
    validate_contact_data(data)

    try:
        # Create contact instance with validated data
        contact = Contact()
        contact.name = data["name"]
        contact.company = data.get("company")
        contact.position = data.get("position")
        contact.last_contacted = (
            datetime.fromisoformat(data["last_contacted"]).date()
            if data.get("last_contacted")
            else None
        )
        contact.follow_up_date = (
            datetime.fromisoformat(data["follow_up_date"]).date()
            if data.get("follow_up_date")
            else None
        )
        contact.warm = data.get("warm", False)
        contact.reminder = data.get("reminder", True)
        contact.notes = data.get("notes")

        # Add contact methods
        for method in data.get("contact_methods", []):
            contact_method = ContactMethod()
            contact_method.method_type = method["type"]
            contact_method.value = method["value"]
            contact_method.is_primary = method.get("is_primary", False)
            contact.contact_methods.append(contact_method)

        db.session.add(contact)
        db.session.commit()

        return (
            jsonify({"id": contact.id, "message": "Contact created successfully"}),
            201,
        )
    except ValueError as e:
        raise BadRequestError(f"Invalid date format: {str(e)}")
    except SQLAlchemyError as e:
        db.session.rollback()
        if "contact_methods_contact_id_value_key" in str(e):
            raise ConflictError("Contact method already exists for this contact")
        raise


@api.route("/contacts/<int:contact_id>", methods=["DELETE"])
def delete_contact(contact_id: int):
    """Delete a contact"""
    contact = Contact.query.get(contact_id)
    if not contact:
        raise NotFoundError(f"Contact with ID {contact_id} not found")

    try:
        # Delete associated contact methods
        ContactMethod.query.filter_by(contact_id=contact_id).delete()
        db.session.delete(contact)
        db.session.commit()
        return jsonify({"message": "Contact deleted successfully"})
    except SQLAlchemyError as e:
        db.session.rollback()
        raise


@api.route("/emails", methods=["GET"])
def get_emails():
    """Get emails for contacts"""
    try:
        contact_ids = request.args.getlist("contact_ids", type=int)

        query = Email.query
        if contact_ids:
            # Verify all contacts exist
            existing_contacts = Contact.query.filter(Contact.id.in_(contact_ids)).all()
            if len(existing_contacts) != len(contact_ids):
                raise NotFoundError("One or more contacts not found")

            query = query.join(Email.contacts).filter(Contact.id.in_(contact_ids))

        emails = query.order_by(Email.date.desc()).all()

        return jsonify(
            [
                {
                    "id": e.id,
                    "date": e.date.isoformat(),
                    "content": e.content,
                    "summary": e.summary,
                    "contacts": [{"id": c.id, "name": c.name} for c in e.contacts],
                }
                for e in emails
            ]
        )
    except Exception as e:
        raise BadRequestError(f"Failed to fetch emails: {str(e)}")


@api.route("/sync-emails", methods=["POST"])
def sync_emails():
    """Sync emails from Gmail"""
    try:
        data = request.json
        if not data:
            raise BadRequestError("No data provided")

        contact_ids = data.get("contact_ids", [])

        # Initialize email service
        email_service = EmailService(
            token_path="gmail_token.json", credentials_path="gmail_credentials.json"
        )

        # Get contacts
        contacts = []
        if contact_ids:
            contacts = Contact.query.filter(Contact.id.in_(contact_ids)).all()
            if len(contacts) != len(contact_ids):
                raise NotFoundError("One or more contacts not found")
        else:
            contacts = Contact.query.all()

        # Build query for email addresses
        email_addresses = []
        for contact in contacts:
            email_methods = [
                cm for cm in contact.contact_methods if cm.method_type == "email"
            ]
            email_addresses.extend(cm.value for cm in email_methods)

        if not email_addresses:
            raise BadRequestError("No email addresses found for the specified contacts")

        query = " OR ".join(f"from:{email}" for email in email_addresses)

        # Fetch and save emails
        emails = email_service.fetch_emails(query)
        email_service.save_emails_to_db(emails, contacts)

        return jsonify(
            {"message": "Emails synced successfully", "email_count": len(emails)}
        )
    except RuntimeError as e:
        raise BadRequestError(f"Failed to sync emails: {str(e)}")
    except Exception as e:
        raise
