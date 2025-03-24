import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from ..models.email import Email
from ..models.contact import Contact
from ..models.contact_method import ContactMethod
from ..models.base import db
import base64
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_, and_, desc, func
import logging
import time
import json
from ..config import Config

logger = logging.getLogger(__name__)


class EmailService:
    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    def __init__(self, token_path: str, credentials_path: str):
        self.token_path = token_path
        self.credentials_path = credentials_path
        self.creds = None
        self.service = None
        self.user_emails = Config.USER_EMAILS
        logger.info(
            f"EmailService initialized with token_path={token_path}, credentials_path={credentials_path}, user_emails={self.user_emails}"
        )

    def authenticate(self):
        """Authenticate with Gmail API.

        Raises:
            RuntimeError: If authentication fails
        """
        logger.info("Starting Gmail API authentication")
        logger.debug(f"Checking for token at {self.token_path}")

        if os.path.exists(self.token_path):
            logger.debug(f"Found existing token file at {self.token_path}")
            with open(self.token_path, "r") as token_file:
                token_data = json.loads(token_file.read())
                self.creds = Credentials.from_authorized_user_info(token_data)
                logger.debug(
                    f"Loaded credentials, valid={self.creds.valid if self.creds else False}"
                )
        else:
            logger.debug("No existing token file found")

        if not self.creds or not self.creds.valid:
            logger.info(
                "Credentials invalid or missing, starting refresh/new token flow"
            )
            if self.creds and self.creds.expired and self.creds.refresh_token:
                logger.debug("Attempting to refresh expired token")
                self.creds.refresh(Request())
                logger.info("Token refreshed successfully")
            else:
                logger.debug(
                    f"Starting new token flow with credentials from {self.credentials_path}"
                )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES
                )
                self.creds = flow.run_local_server(port=0)
                logger.info("New token obtained successfully")

            logger.debug("Saving token to file")
            with open(self.token_path, "w") as token_file:
                token_data = {
                    "token": self.creds.token,
                    "refresh_token": self.creds.refresh_token,
                    "token_uri": self.creds.token_uri,
                    "client_id": self.creds.client_id,
                    "client_secret": self.creds.client_secret,
                    "scopes": self.creds.scopes,
                }
                json.dump(token_data, token_file)

        try:
            logger.debug("Building Gmail service")
            self.service = build("gmail", "v1", credentials=self.creds)
            logger.info("Gmail service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to build Gmail service: {str(e)}")
            raise RuntimeError(f"Failed to initialize Gmail service: {str(e)}")

    def fetch_emails(self, query: str = "") -> List[dict]:
        """Fetch emails from Gmail based on query.

        Args:
            query: Gmail search query string

        Returns:
            List of dictionaries containing email data

        Raises:
            RuntimeError: If Gmail service fails or query fails
        """
        logger.info(f"Fetching emails with query: {query}")
        start_time = time.time()

        if not self.service:
            logger.debug("Gmail service not initialized, authenticating...")
            self.authenticate()

        if not self.service:
            logger.error(
                "Failed to initialize Gmail service after authentication attempt"
            )
            raise RuntimeError("Failed to initialize Gmail service")

        try:
            logger.debug("Executing Gmail API list request")
            results = (
                self.service.users().messages().list(userId="me", q=query).execute()
            )
            messages = results.get("messages", [])
            logger.info(f"Found {len(messages)} messages matching query")

            emails = []
            for idx, message in enumerate(messages):
                logger.debug(f"Processing message {idx + 1}/{len(messages)}")
                msg = (
                    self.service.users()
                    .messages()
                    .get(userId="me", id=message["id"])
                    .execute()
                )

                headers = msg.get("payload", {}).get("headers", [])
                subject = next(
                    (
                        header["value"]
                        for header in headers
                        if header["name"] == "Subject"
                    ),
                    "No Subject",
                )
                from_header = next(
                    (header["value"] for header in headers if header["name"] == "From"),
                    "Unknown",
                )
                to_header = next(
                    (header["value"] for header in headers if header["name"] == "To"),
                    "",
                )
                cc_header = next(
                    (header["value"] for header in headers if header["name"] == "Cc"),
                    "",
                )
                date_header = next(
                    (header["value"] for header in headers if header["name"] == "Date"),
                    None,
                )

                logger.debug(
                    f"Extracted headers - Subject: {subject}, From: {from_header}"
                )

                # Extract email addresses
                from_email = self._extract_email_address(from_header)
                to_emails = self._extract_multiple_email_addresses(to_header)
                cc_emails = self._extract_multiple_email_addresses(cc_header)

                # Extract email content
                payload = msg.get("payload", {})
                content = ""

                if "parts" in payload:
                    logger.debug("Processing multipart message")
                    for part in payload["parts"]:
                        if part.get("mimeType") == "text/plain":
                            data = part.get("body", {}).get("data", "")
                            if data:
                                content = base64.urlsafe_b64decode(data).decode()
                else:
                    logger.debug("Processing single part message")
                    data = payload.get("body", {}).get("data", "")
                    if data:
                        content = base64.urlsafe_b64decode(data).decode()

                emails.append(
                    {
                        "subject": subject,
                        "from": from_header,
                        "from_email": from_email,
                        "to": to_header,
                        "to_emails": to_emails,
                        "cc": cc_header,
                        "cc_emails": cc_emails,
                        "date": date_header,
                        "content": content,
                        "message_id": message["id"],
                    }
                )

            elapsed_time = time.time() - start_time
            logger.info(f"Email fetch completed in {elapsed_time:.2f} seconds")
            return emails

        except Exception as e:
            logger.error(f"Error fetching emails: {str(e)}", exc_info=True)
            raise RuntimeError(f"Error fetching emails: {str(e)}")

    def _extract_email_address(self, header_value: str) -> str:
        """Extract email address from a header value.

        Args:
            header_value: Header value (e.g., "John Doe <john@example.com>")

        Returns:
            Email address (e.g., "john@example.com")
        """
        if "<" in header_value and ">" in header_value:
            return header_value.split("<")[1].split(">")[0].strip().lower()
        return header_value.strip().lower()

    def _extract_multiple_email_addresses(self, header_value: str) -> List[str]:
        """Extract multiple email addresses from a header value.

        Args:
            header_value: Header value (e.g., "John Doe <john@example.com>, Jane Doe <jane@example.com>")

        Returns:
            List of email addresses (e.g., ["john@example.com", "jane@example.com"])
        """
        if not header_value:
            return []

        # Split by commas, but handle commas inside quotes
        parts = []
        current_part = ""
        in_quotes = False

        for char in header_value:
            if char == '"':
                in_quotes = not in_quotes
            elif char == "," and not in_quotes:
                parts.append(current_part.strip())
                current_part = ""
                continue
            current_part += char

        if current_part:
            parts.append(current_part.strip())

        # Extract email from each part
        emails = [self._extract_email_address(part) for part in parts]
        return [email for email in emails if email]  # Filter out empty strings

    def save_emails_to_db(self, emails: List[dict]):
        """Save fetched emails to the database.

        Args:
            emails: List of email dictionaries from fetch_emails

        Returns:
            Dict with counts of saved, skipped, and failed emails

        Raises:
            RuntimeError: If database operation fails
        """
        logger.info(f"Saving {len(emails)} emails to database")

        successful_saves = 0
        skipped_saves = 0
        failed_saves = 0

        for idx, email_data in enumerate(emails):
            if not email_data.get("date"):
                logger.warning(f"Skipping email {idx} due to missing date")
                continue

            try:
                logger.debug(f"Processing email {idx + 1}/{len(emails)}")

                # Check if email already exists by message ID
                message_id = email_data.get("message_id")
                if message_id:
                    existing_email = Email.query.filter_by(
                        message_id=message_id
                    ).first()
                    if existing_email:
                        logger.info(
                            f"Email with message ID {message_id} already exists, skipping"
                        )
                        skipped_saves += 1
                        continue

                # Extract sender and recipient information
                from_email = (
                    email_data.get("from_email", "").lower()
                    if email_data.get("from_email")
                    else ""
                )
                to_emails = (
                    [email.lower() for email in email_data.get("to_emails", [])]
                    if email_data.get("to_emails")
                    else []
                )
                cc_emails = (
                    [email.lower() for email in email_data.get("cc_emails", [])]
                    if email_data.get("cc_emails")
                    else []
                )
                all_recipient_emails = to_emails + cc_emails

                # Check if this email involves at least one contact
                contact_involved = False
                sender_contact = None
                recipient_contacts = []

                # Check if sender is a contact (not a user email)
                if from_email and from_email not in [
                    email.lower() for email in self.user_emails if email
                ]:
                    # Sender is not a user email, look up the contact
                    sender_contact = (
                        db.session.query(Contact)
                        .join(ContactMethod, Contact.id == ContactMethod.contact_id)
                        .filter(
                            ContactMethod.method_type == "email",
                            func.lower(ContactMethod.value) == from_email,
                        )
                        .first()
                    )

                    if sender_contact:
                        contact_involved = True

                # Check if any recipient is a contact
                for recipient_email in all_recipient_emails:
                    recipient_contact = (
                        db.session.query(Contact)
                        .join(ContactMethod, Contact.id == ContactMethod.contact_id)
                        .filter(
                            ContactMethod.method_type == "email",
                            func.lower(ContactMethod.value) == recipient_email,
                        )
                        .first()
                    )

                    if recipient_contact:
                        contact_involved = True
                        recipient_contacts.append(recipient_contact)

                # Skip this email if no contacts are involved
                if not contact_involved:
                    logger.info(
                        f"Email {idx} does not involve any contacts, filtering out"
                    )
                    filtered_out += 1
                    continue

                # Create new email record
                email = Email()
                email.message_id = message_id
                email.date = datetime.strptime(
                    email_data["date"], "%a, %d %b %Y %H:%M:%S %z"
                ).date()
                email.content = email_data["content"]
                email.summary = ""
                email.subject = email_data.get("subject", "No Subject")

                # Set the actual sender
                if sender_contact:
                    email.sender = sender_contact
                    # Add sender to contacts list
                    email.contacts.append(sender_contact)
                else:
                    # Sender is a user email, find or create a special contact for the user
                    user_email = from_email
                    # Check if we already have a special user contact for this email
                    user_contact = (
                        db.session.query(Contact)
                        .join(ContactMethod, Contact.id == ContactMethod.contact_id)
                        .filter(
                            ContactMethod.method_type == "email",
                            func.lower(ContactMethod.value) == user_email,
                        )
                        .first()
                    )

                    # If we don't have a contact for this user email, create a special one
                    if not user_contact:
                        # Create a basic contact for the user email
                        from_name = (
                            email_data.get("from", "").split("<")[0].strip()
                            if "<" in email_data.get("from", "")
                            else "User"
                        )
                        user_contact = Contact()
                        user_contact.name = from_name if from_name else "User"
                        user_contact.notes = "Automatically created for user email"
                        db.session.add(user_contact)
                        db.session.flush()  # Get an ID for the contact

                        # Add the email as a contact method
                        user_contact_method = ContactMethod()
                        user_contact_method.contact_id = user_contact.id
                        user_contact_method.method_type = "email"
                        user_contact_method.value = user_email
                        user_contact_method.is_primary = True
                        db.session.add(user_contact_method)
                        logger.info(
                            f"Created special user contact for email {user_email}"
                        )

                    # Set the user contact as the sender
                    email.sender = user_contact
                    # Add sender to contacts list
                    email.contacts.append(user_contact)

                # Add all recipient contacts
                for contact in recipient_contacts:
                    if contact not in email.contacts:
                        email.contacts.append(contact)

                db.session.add(email)
                successful_saves += 1

            except (ValueError, KeyError) as e:
                logger.error(f"Error processing email {idx}: {str(e)}")
                failed_saves += 1
                continue

        try:
            logger.debug("Committing changes to database")
            db.session.commit()
            logger.info(
                f"Successfully saved {successful_saves} emails, skipped {skipped_saves} duplicates, failed to save {failed_saves}"
            )
            return {
                "saved": successful_saves,
                "skipped": skipped_saves,
                "failed": failed_saves,
            }
        except Exception as e:
            logger.error(f"Error committing changes to database: {str(e)}")
            db.session.rollback()
            raise RuntimeError(f"Failed to save emails: {str(e)}")

    @staticmethod
    def get_emails_for_sender(sender_id: int) -> List[Email]:
        """Get emails sent by a specific contact.

        Args:
            sender_id: ID of the contact who sent the emails

        Returns:
            List of Email objects ordered by date descending
        """
        logger.info(f"Fetching emails for sender_id={sender_id}")
        try:
            emails = (
                Email.query.filter_by(sender_id=sender_id)
                .order_by(Email.date.desc())
                .all()
            )
            logger.info(f"Found {len(emails)} emails for sender {sender_id}")
            return emails
        except SQLAlchemyError as e:
            logger.error(
                f"Database error fetching sender emails: {str(e)}", exc_info=True
            )
            raise

    @staticmethod
    def get_emails_for_receiver(receiver_id: int) -> List[Email]:
        """Get emails received by a specific contact.

        Args:
            receiver_id: ID of the contact who received the emails

        Returns:
            List of Email objects ordered by date descending
        """
        logger.info(f"Fetching emails for receiver_id={receiver_id}")
        try:
            emails = (
                Email.query.join(Email.receivers)
                .filter(Contact.id == receiver_id)
                .order_by(Email.date.desc())
                .all()
            )
            logger.info(f"Found {len(emails)} emails for receiver {receiver_id}")
            return emails
        except SQLAlchemyError as e:
            logger.error(
                f"Database error fetching receiver emails: {str(e)}", exc_info=True
            )
            raise

    @staticmethod
    def get_all_emails_for_contact(contact_id: int) -> List[Email]:
        """Get all emails a contact was involved in (sent or received).

        Args:
            contact_id: ID of the contact

        Returns:
            List of Email objects ordered by date descending
        """
        logger.info(f"Fetching all emails for contact_id={contact_id}")
        try:
            emails = (
                Email.query.join(Email.contacts)
                .filter(or_(Email.sender_id == contact_id, Contact.id == contact_id))
                .order_by(Email.date.desc())
                .distinct()
                .all()
            )
            logger.info(f"Found {len(emails)} total emails for contact {contact_id}")
            return emails
        except SQLAlchemyError as e:
            logger.error(
                f"Database error fetching contact emails: {str(e)}", exc_info=True
            )
            raise

    @staticmethod
    def format_email_response(email: Email) -> dict:
        """Format an email object into API response format.

        Args:
            email: Email object to format

        Returns:
            Dictionary containing formatted email data

        Raises:
            Exception: If object is detached from session
        """
        logger.debug(f"Formatting email response for email_id={email.id}")
        try:
            # Format sender
            sender_data = (
                {
                    "id": email.sender.id,
                    "name": email.sender.name,
                    "email": email.sender.primary_email,
                }
                if email.sender
                else None
            )

            # Format receivers
            receiver_data = (
                [
                    {
                        "id": receiver.id,
                        "name": receiver.name,
                        "email": receiver.primary_email,
                    }
                    for receiver in email.receivers
                ]
                if email.receivers
                else []
            )

            return {
                "id": email.id,
                "subject": email.subject,
                "content": email.content,
                "summary": email.summary,
                "date": email.date.isoformat() if email.date else None,
                "sender": sender_data,
                "receivers": receiver_data,
            }
        except Exception as e:
            logger.warning(
                f"Error formatting email {email.id}, attempting refresh: {str(e)}"
            )
            db.session.add(email)
            db.session.refresh(email)
            return EmailService.format_email_response(email)

    @staticmethod
    def search_emails(
        query: Optional[str] = None,
        contact_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        is_sender: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Search emails with various filters.

        Args:
            query: Search term to match in subject or content
            contact_id: Filter by contact ID
            start_date: Filter emails after this date
            end_date: Filter emails before this date
            is_sender: If True, only get emails sent by contact_id
                      If False, only get emails received by contact_id
                      If None, get both
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            Dictionary containing:
                - emails: List of Email objects
                - total: Total number of matching emails
                - has_more: Whether there are more results
        """
        logger.info(
            f"Searching emails with params: query='{query}', contact_id={contact_id}, "
            f"start_date={start_date}, end_date={end_date}, is_sender={is_sender}, "
            f"limit={limit}, offset={offset}"
        )

        try:
            base_query = Email.query

            if query:
                search_term = f"%{query}%"
                logger.debug(f"Applying text search with term: {search_term}")
                base_query = base_query.filter(
                    or_(
                        Email.subject.ilike(search_term),
                        Email.content.ilike(search_term),
                        Email.summary.ilike(search_term),
                    )
                )

            if start_date:
                logger.debug(f"Applying start_date filter: {start_date}")
                base_query = base_query.filter(Email.date >= start_date)
            if end_date:
                logger.debug(f"Applying end_date filter: {end_date}")
                base_query = base_query.filter(Email.date <= end_date)

            if contact_id:
                logger.debug(
                    f"Applying contact filters: contact_id={contact_id}, is_sender={is_sender}"
                )
                if is_sender is True:
                    base_query = base_query.filter(Email.sender_id == contact_id)
                elif is_sender is False:
                    base_query = base_query.join(Email.receivers).filter(
                        Contact.id == contact_id
                    )
                else:
                    base_query = base_query.join(Email.receivers, isouter=True).filter(
                        or_(Email.sender_id == contact_id, Contact.id == contact_id)
                    )

            total = base_query.count()
            logger.debug(f"Total matching results: {total}")

            emails = (
                base_query.order_by(desc(Email.date))
                .offset(offset)
                .limit(limit + 1)
                .all()
            )

            has_more = len(emails) > limit
            if has_more:
                emails = emails[:limit]

            logger.info(f"Returning {len(emails)} results, has_more={has_more}")
            return {"emails": emails, "total": total, "has_more": has_more}

        except SQLAlchemyError as e:
            logger.error(f"Database error during email search: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def get_email_statistics(contact_id: int) -> Dict[str, Any]:
        """Get email statistics for a contact.

        Args:
            contact_id: ID of the contact

        Returns:
            Dictionary containing:
                - total_sent: Number of emails sent
                - total_received: Number of emails received
                - most_frequent_senders: List of contacts who send the most emails
                - most_frequent_receivers: List of contacts who receive the most emails
                - email_volume_by_month: Email count by month
        """
        logger.info(f"Generating email statistics for contact_id={contact_id}")
        try:
            sent_count = Email.query.filter(Email.sender_id == contact_id).count()
            received_count = (
                Email.query.join(Email.receivers)
                .filter(Contact.id == contact_id)
                .count()
            )

            logger.debug(
                f"Basic counts - sent: {sent_count}, received: {received_count}"
            )

            frequent_senders = (
                db.session.query(Contact, func.count(Email.id).label("email_count"))
                .join(Email, Email.sender_id == Contact.id)
                .join(Email.receivers)
                .filter(Contact.id != contact_id)
                .group_by(Contact.id)
                .order_by(desc("email_count"))
                .limit(5)
                .all()
            )

            frequent_receivers = (
                db.session.query(Contact, func.count(Email.id).label("email_count"))
                .join(Email.receivers)
                .filter(Email.sender_id == contact_id)
                .group_by(Contact.id)
                .order_by(desc("email_count"))
                .limit(5)
                .all()
            )

            volume_by_month = (
                db.session.query(
                    func.date_trunc("month", Email.date).label("month"),
                    func.count(Email.id).label("count"),
                )
                .join(Email.receivers, isouter=True)
                .filter(or_(Email.sender_id == contact_id, Contact.id == contact_id))
                .group_by("month")
                .order_by("month")
                .all()
            )

            logger.info(f"Statistics generated successfully for contact {contact_id}")

            return {
                "total_sent": sent_count,
                "total_received": received_count,
                "most_frequent_senders": [
                    {"contact": contact, "email_count": count}
                    for contact, count in frequent_senders
                ],
                "most_frequent_receivers": [
                    {"contact": contact, "email_count": count}
                    for contact, count in frequent_receivers
                ],
                "email_volume_by_month": [
                    {"month": month, "count": count} for month, count in volume_by_month
                ],
            }

        except SQLAlchemyError as e:
            logger.error(
                f"Database error generating statistics: {str(e)}", exc_info=True
            )
            raise
