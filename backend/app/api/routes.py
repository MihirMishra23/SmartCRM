from flask import Blueprint, jsonify, request
from ..models.contact import Contact
from ..models.contact_method import ContactMethod
from ..models.email import Email
from ..models.base import db
from ..services.email_service import EmailService
from ..services.contact_service import ContactService
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
    """Get all contacts with optional filtering"""
    try:
        # Allow filtering by name, email, company
        name = request.args.get("name")
        email = request.args.get("email")
        company = request.args.get("company")

        contacts = ContactService.get_contacts(name=name, email=email, company=company)
        return jsonify([ContactService.format_contact_response(c) for c in contacts])
    except Exception as e:
        raise BadRequestError(f"Failed to fetch contacts: {str(e)}")


@api.route("/contacts", methods=["POST"])
def create_contact():
    """Create a new contact"""
    data = request.json
    if not isinstance(data, dict):
        raise BadRequestError("Invalid request data")

    # Validate input data
    validate_contact_data(data)

    try:
        contact = ContactService.create_contact(data)
        # Return the created contact data instead of just ID
        return jsonify(ContactService.format_contact_response(contact)), 201
    except ValueError as e:
        if "already associated with another contact" in str(e):
            raise ConflictError(str(e))
        raise BadRequestError(f"Invalid data format: {str(e)}")
    except SQLAlchemyError as e:
        raise


@api.route("/contacts/<string:email>", methods=["DELETE"])
def delete_contact(email: str):
    """Delete a contact by their email address"""
    try:
        if not ContactService.delete_contact_by_email(email):
            raise NotFoundError(f"Contact with email {email} not found")
        return jsonify({"message": "Contact deleted successfully"})
    except SQLAlchemyError as e:
        raise


@api.route("/contacts/<string:email>/emails", methods=["GET"])
def get_contact_emails(email: str):
    """Get emails for a specific contact"""
    try:
        contact = ContactService.get_contact_by_email(email)
        if not contact:
            raise NotFoundError(f"Contact with email {email} not found")

        emails = EmailService.get_emails_for_contacts([contact.id])
        return jsonify([EmailService.format_email_response(e) for e in emails])
    except Exception as e:
        raise BadRequestError(f"Failed to fetch emails: {str(e)}")


@api.route("/contacts/<string:email>/sync-emails", methods=["POST"])
def sync_contact_emails(email: str):
    """Sync emails for a specific contact"""
    try:
        contact = ContactService.get_contact_by_email(email)
        if not contact:
            raise NotFoundError(f"Contact with email {email} not found")

        # Initialize email service
        email_service = EmailService(
            token_path="gmail_token.json", credentials_path="gmail_credentials.json"
        )

        # Get email methods for the contact
        email_methods = [
            cm.value for cm in contact.contact_methods if cm.method_type == "email"
        ]

        if not email_methods:
            raise BadRequestError("No email addresses found for the contact")

        query = " OR ".join(f"from:{email}" for email in email_methods)

        # Fetch and save emails
        emails = email_service.fetch_emails(query)
        email_service.save_emails_to_db(emails, [contact])

        return jsonify(
            {"message": "Emails synced successfully", "email_count": len(emails)}
        )
    except RuntimeError as e:
        raise BadRequestError(f"Failed to sync emails: {str(e)}")
    except Exception as e:
        raise


@api.route("/emails/sync", methods=["POST"])
def sync_all_emails():
    """Sync emails for all contacts or filtered by search criteria"""
    try:
        data = request.json
        if not isinstance(data, dict):
            raise BadRequestError("Invalid request data")

        # Allow filtering contacts by name, email, company
        name = data.get("name")
        email = data.get("email")
        company = data.get("company")

        # Get contacts based on filters
        contacts = ContactService.get_contacts(name=name, email=email, company=company)

        if not contacts:
            raise NotFoundError("No contacts found matching the criteria")

        # Initialize email service
        email_service = EmailService(
            token_path="gmail_token.json", credentials_path="gmail_credentials.json"
        )

        # Build query for email addresses
        email_addresses = []
        for contact in contacts:
            email_methods = [
                cm.value for cm in contact.contact_methods if cm.method_type == "email"
            ]
            email_addresses.extend(email_methods)

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
