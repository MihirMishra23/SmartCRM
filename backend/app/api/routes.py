from flask import Blueprint, jsonify, request, Response
from ..models.contact import Contact
from ..models.contact_method import ContactMethod
from ..models.email import Email
from ..models.base import db
from ..services.email_service import EmailService
from ..services.contact_service import ContactService
from datetime import datetime
from typing import List, Optional, Dict, Any, Union, Tuple, TypedDict
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError
import traceback
from flasgger import swag_from
from .swagger_docs import (
    GET_CONTACTS_DOCS,
    CREATE_CONTACT_DOCS,
    DELETE_CONTACT_DOCS,
    GET_CONTACT_EMAILS_DOCS,
    SYNC_CONTACT_EMAILS_DOCS,
    SYNC_ALL_EMAILS_DOCS,
    GET_CONTACT_BY_EMAIL_DOCS,
)

api = Blueprint("api", __name__)


class APIError(Exception):
    """Base class for API errors.

    Attributes:
        message (str): Human readable error message
        status_code (int): HTTP status code for the error
    """

    def __init__(self, message: str, status_code: int):
        super().__init__()
        self.message = message
        self.status_code = status_code


class BadRequestError(APIError):
    """400 Bad Request - Client provided invalid data."""

    def __init__(self, message: str = "Bad Request"):
        super().__init__(message, 400)


class ForbiddenError(APIError):
    """403 Forbidden - Client lacks required permissions."""

    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, 403)


class NotFoundError(APIError):
    """404 Not Found - Requested resource does not exist."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, 404)


class ConflictError(APIError):
    """409 Conflict - Resource already exists or state conflict."""

    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, 409)


class MetaData(TypedDict, total=False):
    """Type definition for response metadata.

    All fields are optional and can be None. This allows for flexible
    metadata structures across different endpoint responses.
    """

    page: Optional[int]
    per_page: Optional[int]
    total: Optional[int]
    email_count: Optional[int]
    contact_count: Optional[int]
    # Add any other potential meta fields here


class APIResponse:
    """Helper class to standardize API responses.

    This class provides static methods to create consistent JSON responses
    for both successful operations and errors.
    """

    @staticmethod
    def success(
        data: Any = None, message: Optional[str] = None, meta: Optional[MetaData] = None
    ) -> Response:
        """Create a success response.

        Args:
            data: The response payload
            message: Optional success message
            meta: Optional metadata about the response

        Returns:
            Flask Response object containing the JSON response
        """
        response: Dict[str, Any] = {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
        }
        if message:
            response["message"] = message
        if data is not None:
            response["data"] = data
        if meta:
            response["meta"] = meta
        return jsonify(response)

    @staticmethod
    def error(
        message: str, status_code: int, details: Optional[str] = None
    ) -> Tuple[Response, int]:
        """Create an error response.

        Args:
            message: Error message describing what went wrong
            status_code: HTTP status code
            details: Optional additional error details

        Returns:
            Tuple of (Flask Response object, status_code)
        """
        response = {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": {"message": message, "code": status_code},
        }
        if details:
            response["error"]["details"] = details
        return jsonify(response), status_code


@api.errorhandler(APIError)
def handle_api_error(error):
    return APIResponse.error(error.message, error.status_code)


@api.errorhandler(SQLAlchemyError)
def handle_db_error(error):
    return APIResponse.error("Database error occurred", 500, str(error))


@api.errorhandler(Exception)
def handle_generic_error(error):
    return APIResponse.error("An unexpected error occurred", 500, str(error))


def validate_contact_data(data: Dict) -> None:
    """Validate contact data before creation/update.

    Args:
        data: Dictionary containing contact data

    Raises:
        BadRequestError: If required fields are missing or invalid
    """
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
@swag_from(GET_CONTACTS_DOCS)
def get_contacts():
    """
    Retrieve a paginated list of all contacts.

    Returns:
        APIResponse: JSON response containing:
            - data: List of Contact objects
            - meta: Pagination metadata
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    pagination = Contact.query.paginate(page=page, per_page=per_page, error_out=False)

    return APIResponse.success(
        data=[
            ContactService.format_contact_response(contact)
            for contact in pagination.items
        ],
        meta={
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
        },
    )


@api.route("/contacts/lookup/email/<string:email>", methods=["GET"])
@swag_from(GET_CONTACT_BY_EMAIL_DOCS)
def get_contact_by_email(email: str):
    """
    Lookup a contact by their email address.

    Args:
        email: Email address to search for

    Returns:
        APIResponse: JSON response containing the matching contact(s)
    """
    contacts = (
        Contact.query.join(Contact.contact_methods)
        .filter(ContactMethod.method_type == "email", ContactMethod.value == email)
        .all()
    )

    return APIResponse.success(
        data=[ContactService.format_contact_response(contact) for contact in contacts],
        meta={"total": len(contacts)},
    )


@api.route("/contacts", methods=["POST"])
@swag_from(CREATE_CONTACT_DOCS)
def create_contact():
    """Create a new contact with the provided information.

    The request must include at least a name. Contact methods (email, phone, etc.)
    can be provided optionally.

    Returns:
        APIResponse: JSON response containing the created contact

    Raises:
        BadRequestError: If the request data is invalid
        ConflictError: If a contact with the same email already exists
    """
    data = request.json
    if not isinstance(data, dict):
        raise BadRequestError("Invalid request data")

    validate_contact_data(data)

    try:
        contact = ContactService.create_contact(data)
        return (
            APIResponse.success(
                data=ContactService.format_contact_response(contact),
                message="Contact created successfully",
            ),
            201,
        )
    except ValueError as e:
        if "already associated with another contact" in str(e):
            raise ConflictError(str(e))
        raise BadRequestError(f"Invalid data format: {str(e)}")
    except SQLAlchemyError as e:
        raise


@api.route("/contacts/<string:email>", methods=["DELETE"])
@swag_from(DELETE_CONTACT_DOCS)
def delete_contact(email: str):
    """Delete a contact by their email address.

    Args:
        email: Email address of the contact to delete

    Returns:
        APIResponse: Success message if deleted

    Raises:
        NotFoundError: If the contact doesn't exist
    """
    try:
        if not ContactService.delete_contact_by_email(email):
            raise NotFoundError(f"Contact with email {email} not found")
        return APIResponse.success(message="Contact deleted successfully")
    except SQLAlchemyError as e:
        raise


@api.route("/contacts/<string:email>/emails", methods=["GET"])
@swag_from(GET_CONTACT_EMAILS_DOCS)
def get_contact_emails(email: str):
    """Get all emails associated with a specific contact.

    Args:
        email: Email address of the contact

    Returns:
        APIResponse: JSON response containing:
            - data: List of Email objects
            - meta: Email count metadata

    Raises:
        NotFoundError: If the contact doesn't exist
        BadRequestError: If email fetching fails
    """
    try:
        contact = ContactService.get_contact_by_email(email)
        if not contact:
            raise NotFoundError(f"Contact with email {email} not found")

        emails = EmailService.get_emails_for_contacts([contact.id])
        return APIResponse.success(
            data=[EmailService.format_email_response(e) for e in emails],
            meta={"total": len(emails)},
        )
    except Exception as e:
        raise BadRequestError(f"Failed to fetch emails: {str(e)}")


@api.route("/contacts/<string:email>/sync-emails", methods=["POST"])
@swag_from(SYNC_CONTACT_EMAILS_DOCS)
def sync_contact_emails(email: str):
    """Synchronize emails for a specific contact from Gmail.

    This endpoint will:
    1. Verify the contact exists
    2. Get all email addresses associated with the contact
    3. Fetch emails from Gmail for these addresses
    4. Save the emails to the database

    Args:
        email: Email address of the contact

    Returns:
        APIResponse: Success message with email count

    Raises:
        NotFoundError: If the contact doesn't exist
        BadRequestError: If sync operation fails
    """
    try:
        contact = ContactService.get_contact_by_email(email)
        if not contact:
            raise NotFoundError(f"Contact with email {email} not found")

        email_service = EmailService(
            token_path="gmail_token.json", credentials_path="gmail_credentials.json"
        )

        email_methods = [
            cm.value for cm in contact.contact_methods if cm.method_type == "email"
        ]

        if not email_methods:
            raise BadRequestError("No email addresses found for the contact")

        query = " OR ".join(f"from:{email}" for email in email_methods)

        emails = email_service.fetch_emails(query)
        email_service.save_emails_to_db(emails, [contact])

        return APIResponse.success(
            message="Emails synced successfully", meta={"email_count": len(emails)}
        )
    except RuntimeError as e:
        raise BadRequestError(f"Failed to sync emails: {str(e)}")
    except Exception as e:
        raise


@api.route("/emails/sync", methods=["POST"])
@swag_from(SYNC_ALL_EMAILS_DOCS)
def sync_all_emails():
    """Synchronize emails for all contacts or filtered by search criteria.

    This endpoint will:
    1. Find contacts matching the search criteria (if provided)
    2. Get all email addresses for these contacts
    3. Fetch emails from Gmail for these addresses
    4. Save the emails to the database

    The request body can include optional filters:
    - name: Filter contacts by name
    - email: Filter contacts by email
    - company: Filter contacts by company

    Returns:
        APIResponse: Success message with email and contact counts

    Raises:
        NotFoundError: If no contacts match the criteria
        BadRequestError: If sync operation fails
    """
    try:
        data = request.json
        if not isinstance(data, dict):
            raise BadRequestError("Invalid request data")

        name = data.get("name")
        email = data.get("email")
        company = data.get("company")

        contacts = ContactService.get_contacts(name=name, email=email, company=company)

        if not contacts:
            raise NotFoundError("No contacts found matching the criteria")

        email_service = EmailService(
            token_path="gmail_token.json", credentials_path="gmail_credentials.json"
        )

        email_addresses = []
        for contact in contacts:
            email_methods = [
                cm.value for cm in contact.contact_methods if cm.method_type == "email"
            ]
            email_addresses.extend(email_methods)

        if not email_addresses:
            raise BadRequestError("No email addresses found for the specified contacts")

        query = " OR ".join(f"from:{email}" for email in email_addresses)

        emails = email_service.fetch_emails(query)
        email_service.save_emails_to_db(emails, contacts)

        return APIResponse.success(
            message="Emails synced successfully",
            meta={"email_count": len(emails), "contact_count": len(contacts)},
        )
    except RuntimeError as e:
        raise BadRequestError(f"Failed to sync emails: {str(e)}")
    except Exception as e:
        raise
