import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
from typing import List, Optional
from datetime import datetime
from ..models.email import Email
from ..models.contact import Contact
from ..models.base import db
import base64
from sqlalchemy.exc import SQLAlchemyError


class EmailService:
    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    def __init__(self, token_path: str, credentials_path: str):
        self.token_path = token_path
        self.credentials_path = credentials_path
        self.creds = None
        self.service = None

    def authenticate(self):
        """Authenticate with Gmail API.

        Raises:
            RuntimeError: If authentication fails
        """
        if os.path.exists(self.token_path):
            with open(self.token_path, "rb") as token:
                self.creds = pickle.load(token)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            with open(self.token_path, "wb") as token:
                pickle.dump(self.creds, token)

        self.service = build("gmail", "v1", credentials=self.creds)

    def fetch_emails(self, query: str = "") -> List[dict]:
        """Fetch emails from Gmail based on query.

        Args:
            query: Gmail search query string

        Returns:
            List of dictionaries containing email data

        Raises:
            RuntimeError: If Gmail service fails or query fails
        """
        if not self.service:
            self.authenticate()

        if not self.service:  # If still None after authentication
            raise RuntimeError("Failed to initialize Gmail service")

        try:
            results = (
                self.service.users().messages().list(userId="me", q=query).execute()
            )
            messages = results.get("messages", [])

            emails = []
            for message in messages:
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
                date_header = next(
                    (header["value"] for header in headers if header["name"] == "Date"),
                    None,
                )

                # Extract email content
                payload = msg.get("payload", {})
                content = ""

                if "parts" in payload:
                    for part in payload["parts"]:
                        if part.get("mimeType") == "text/plain":
                            data = part.get("body", {}).get("data", "")
                            if data:
                                content = base64.urlsafe_b64decode(data).decode()
                else:
                    data = payload.get("body", {}).get("data", "")
                    if data:
                        content = base64.urlsafe_b64decode(data).decode()

                emails.append(
                    {
                        "subject": subject,
                        "from": from_header,
                        "date": date_header,
                        "content": content,
                    }
                )

            return emails
        except Exception as e:
            raise RuntimeError(f"Error fetching emails: {str(e)}")

    def save_emails_to_db(self, emails: List[dict], contacts: List[Contact]):
        """Save fetched emails to database.

        Args:
            emails: List of email data dictionaries
            contacts: List of Contact objects to associate with emails

        Raises:
            RuntimeError: If database operation fails
        """
        for email_data in emails:
            if not email_data.get("date"):
                continue

            try:
                email = Email()
                email.date = datetime.strptime(
                    email_data["date"], "%a, %d %b %Y %H:%M:%S %z"
                ).date()
                email.content = email_data["content"]
                email.summary = ""  # You might want to generate this using GPT

                db.session.add(email)

                # Link email to contacts
                email.contacts.extend(contacts)

            except (ValueError, KeyError) as e:
                print(f"Error processing email: {str(e)}")
                continue

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise RuntimeError(f"Error saving emails to database: {str(e)}")

    @staticmethod
    def get_emails_for_contacts(contact_ids: Optional[List[int]] = None) -> List[Email]:
        """Get emails for specified contacts or all emails if no contacts specified.

        Args:
            contact_ids: Optional list of contact IDs to filter by

        Returns:
            List of Email objects ordered by date descending
        """
        query = Email.query
        if contact_ids:
            query = query.join(Email.contacts).filter(Contact.id.in_(contact_ids))
        return query.order_by(Email.date.desc()).all()

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
        try:
            return {
                "id": email.id,
                "subject": email.subject,
                "content": email.content,
                "summary": email.summary,
                "date": email.date.isoformat() if email.date else None,
                "contacts": (
                    [
                        {
                            "id": contact.id,
                            "name": contact.name,
                            "email": next(
                                (
                                    cm.value
                                    for cm in contact.contact_methods
                                    if cm.method_type == "email"
                                ),
                                None,
                            ),
                        }
                        for contact in email.contacts
                    ]
                    if email.contacts
                    else []
                ),
            }
        except Exception as e:
            # If the object is detached, try to refresh it
            from ..models.base import db

            db.session.add(email)
            db.session.refresh(email)
            return EmailService.format_email_response(email)
