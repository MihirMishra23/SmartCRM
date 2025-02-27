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
    SEARCH_EMAILS_DOCS,
    EMAIL_STATS_DOCS,
)
import logging
from os.path import expanduser

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

    # Pagination
    page: Optional[int]
    per_page: Optional[int]
    total: Optional[int]
    limit: Optional[int]
    offset: Optional[int]
    has_more: Optional[bool]

    # Email counts
    email_count: Optional[int]
    contact_count: Optional[int]
    sent_count: Optional[int]
    received_count: Optional[int]
    sent_emails_count: Optional[int]
    total_emails: Optional[int]

    # IDs
    contact_id: Optional[int]


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

    required_fields = ["name", "contact_methods"]
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise BadRequestError(f"Missing required fields: {', '.join(missing_fields)}")

    if not data.get("contact_methods"):
        raise BadRequestError("Contact methods cannot be empty")

    for method in data["contact_methods"]:
        if "type" not in method or "value" not in method:
            raise BadRequestError("Contact methods must include type and value")
        if method["type"] not in ["email", "phone", "linkedin"]:
            raise BadRequestError("Invalid contact method type")


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


@api.route("/test", methods=["GET", "OPTIONS"])
def test():
    return APIResponse.success(message="Hello, world!")


@api.route("/contacts", methods=["POST"])
@swag_from(CREATE_CONTACT_DOCS)
def create_contact():
    """Create a new contact with the provided information.

    The request must include at least a name. Contact methods (email, phone, etc.)
    can be provided optionally.

    Returns:
        APIResponse: JSON response containing the created contact

    Raises:
        BadRequestError: If the request data is invalid or Content-Type is not application/json
        ConflictError: If a contact with the same email already exists
    """
    # Validate Content-Type header
    if not request.is_json:
        raise BadRequestError("Content-Type must be application/json")

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
        SQLAlchemyError: If database operation fails
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

        # Get both sent and received emails
        emails = EmailService.get_all_emails_for_contact(contact.id)
        formatted_emails = [EmailService.format_email_response(e) for e in emails]

        # Split into sent and received for metadata
        sent_count = len([e for e in emails if e.sender_id == contact.id])
        received_count = len([e for e in emails if e.sender_id != contact.id])

        return APIResponse.success(
            data=formatted_emails,
            meta={
                "total": len(emails),
                "sent_count": sent_count,
                "received_count": received_count,
            },
        )
    except Exception as e:
        if isinstance(e, NotFoundError):
            raise
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
        BadRequestError: If sync operation fails or Content-Type is not application/json
    """
    # Validate Content-Type header
    if not request.is_json:
        raise BadRequestError("Content-Type must be application/json")

    try:
        contact = ContactService.get_contact_by_email(email)
        if not contact:
            raise NotFoundError(f"Contact with email {email} not found")

        email_service = EmailService(
            token_path="gmail_token.json", credentials_path="gmail_credentials.json"
        )

        email_addresses = contact.email_addresses
        if not email_addresses:
            raise BadRequestError("No email addresses found for the contact")

        # Fetch emails sent by this contact
        query = " OR ".join(f"from:{email}" for email in email_addresses)
        sent_emails = email_service.fetch_emails(query)

        # Save sent emails
        email_service.save_emails_to_db(sent_emails, sender=contact)

        return APIResponse.success(
            message="Emails synced successfully",
            meta={"sent_emails_count": len(sent_emails)},
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
        BadRequestError: If sync operation fails or Content-Type is not application/json
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting sync_all_emails endpoint")

    # Validate Content-Type header
    if not request.is_json:
        logger.error("Request Content-Type is not application/json")
        raise BadRequestError("Content-Type must be application/json")

    try:
        data = request.json or {}
        if not isinstance(data, dict):
            logger.error(f"Invalid request data type: {type(data)}")
            raise BadRequestError("Invalid request data")

        logger.debug(f"Searching contacts with filters: {data}")
        contacts = ContactService.get_contacts(
            name=data.get("name"), email=data.get("email"), company=data.get("company")
        )

        if not contacts:
            logger.warning("No contacts found matching the criteria")
            raise NotFoundError("No contacts found matching the criteria")

        logger.info(f"Found {len(contacts)} contacts to sync")

        email_service = EmailService(
            token_path=expanduser("~/CodingStuff/Projects/SmartCRM/gmail_token.json"),
            credentials_path=expanduser(
                "~/CodingStuff/Projects/SmartCRM/gmail_credentials.json"
            ),
        )

        total_emails = 0
        for idx, contact in enumerate(contacts):
            logger.debug(
                f"Processing contact {idx + 1}/{len(contacts)}: {contact.name}"
            )
            email_addresses = contact.email_addresses
            if not email_addresses:
                logger.warning(f"No email addresses found for contact {contact.name}")
                continue

            # Fetch emails sent by this contact
            query = " OR ".join(f"from:{email}" for email in email_addresses)
            logger.debug(f"Gmail query for contact {contact.name}: {query}")

            sent_emails = email_service.fetch_emails(query)
            logger.info(f"Found {len(sent_emails)} emails for contact {contact.name}")

            # Save emails
            logger.debug(f"Saving {len(sent_emails)} emails for contact {contact.name}")
            email_service.save_emails_to_db(sent_emails, sender=contact)
            total_emails += len(sent_emails)

        logger.info(
            f"Sync completed. Total emails: {total_emails}, Contacts: {len(contacts)}"
        )
        return APIResponse.success(
            message="Emails synced successfully",
            meta={"email_count": total_emails, "contact_count": len(contacts)},
        )
    except RuntimeError as e:
        logger.error(f"Failed to sync emails: {str(e)}", exc_info=True)
        raise BadRequestError(f"Failed to sync emails: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during sync: {str(e)}", exc_info=True)
        raise


@api.route("/emails/search", methods=["GET"])
@swag_from(SEARCH_EMAILS_DOCS)
def search_emails():
    """Search emails with various filters.

    Query Parameters:
        q (str): Search term to match in subject or content
        contact_id (int): Filter by contact ID
        start_date (str): Filter emails after this date (YYYY-MM-DD)
        end_date (str): Filter emails before this date (YYYY-MM-DD)
        is_sender (bool): If true, only get emails sent by contact_id
        limit (int): Maximum number of results to return
        offset (int): Number of results to skip

    Returns:
        APIResponse: JSON response containing:
            - data: List of Email objects
            - meta: Search metadata
    """
    try:
        # Parse query parameters
        query = request.args.get("q")
        contact_id = request.args.get("contact_id", type=int)
        start_date_str = request.args.get("start_date")
        end_date_str = request.args.get("end_date")
        is_sender = request.args.get(
            "is_sender", type=lambda v: v.lower() == "true" if v else None
        )
        limit = min(int(request.args.get("limit", 50)), 100)  # Cap at 100
        offset = int(request.args.get("offset", 0))

        # Parse dates if provided
        start_date = None
        end_date = None
        if start_date_str:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        if end_date_str:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

        # Perform search
        result = EmailService.search_emails(
            query=query,
            contact_id=contact_id,
            start_date=start_date,
            end_date=end_date,
            is_sender=is_sender,
            limit=limit,
            offset=offset,
        )

        return APIResponse.success(
            data=[
                EmailService.format_email_response(email) for email in result["emails"]
            ],
            meta={
                "total": result["total"],
                "has_more": result["has_more"],
                "limit": limit,
                "offset": offset,
            },
        )
    except ValueError as e:
        raise BadRequestError(f"Invalid parameter format: {str(e)}")
    except Exception as e:
        raise BadRequestError(f"Search failed: {str(e)}")


@api.route("/contacts/<int:contact_id>/email-stats", methods=["GET"])
def get_contact_email_stats(contact_id: int):
    """Get email statistics for a contact.

    Args:
        contact_id: ID of the contact

    Returns:
        APIResponse: JSON response containing email statistics:
            - total_sent: Number of emails sent
            - total_received: Number of emails received
            - most_frequent_senders: Top contacts who send emails
            - most_frequent_receivers: Top contacts who receive emails
            - email_volume_by_month: Email count by month
    """
    try:
        contact = Contact.query.get(contact_id)
        if not contact:
            raise NotFoundError(f"Contact with ID {contact_id} not found")

        stats = EmailService.get_email_statistics(contact_id)

        # Format the response
        formatted_stats = {
            "total_sent": stats["total_sent"],
            "total_received": stats["total_received"],
            "most_frequent_senders": [
                {
                    "contact": ContactService.format_contact_response(item["contact"]),
                    "email_count": item["email_count"],
                }
                for item in stats["most_frequent_senders"]
            ],
            "most_frequent_receivers": [
                {
                    "contact": ContactService.format_contact_response(item["contact"]),
                    "email_count": item["email_count"],
                }
                for item in stats["most_frequent_receivers"]
            ],
            "email_volume_by_month": stats["email_volume_by_month"],
        }

        return APIResponse.success(
            data=formatted_stats,
            meta={
                "contact_id": contact_id,
                "total_emails": stats["total_sent"] + stats["total_received"],
            },
        )
    except Exception as e:
        if isinstance(e, NotFoundError):
            raise
        raise BadRequestError(f"Failed to get email statistics: {str(e)}")
