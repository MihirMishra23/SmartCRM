from typing import Iterable, Any, List, Optional, Literal

import io
import re

from dataclasses import dataclass
from base64 import urlsafe_b64decode, urlsafe_b64encode
from email.mime.text import MIMEText


@dataclass(init=False, repr=False)
class Email:
    To: str
    Cc: Optional[str] = None
    From: str
    Subject: str
    Contents: str
    Date: str

    def __str__(self, hide_date: bool = False) -> str:
        sb = io.StringIO()
        if not hide_date:
            sb.write(f"Date: {self.Date}\n")
        sb.write(f"To: {self.To}\n")
        if self.Cc:
            sb.write(f"Cc: {self.Cc}\n")
        sb.write(f"From: {self.From}\nSubject: {self.Subject}\n\n{self.Contents}")
        return sb.getvalue()

    def get_contact_names(self) -> List[str]:
        """Returns a list of contact names from the email"""
        contacts = self.To.split(", ") + self.From.split(",")
        if self.Cc:
            contacts += self.Cc.split(",")
        return [name.split("<")[0].strip() for name in contacts]

    def get_contact_emails(self) -> List[str]:
        """Returns a list of contact emails from the email"""
        contacts = self.To.split(", ") + self.From.split(",")
        if self.Cc:
            contacts += self.Cc.split(",")
        return [re.search(r"<(.*?)>", name).group(1) for name in contacts]  # type: ignore


def extract_substring(text: str) -> str:
    """Returns the substrings inside of <> or the string itself if <> does not exist"""
    lst: list[str] = text.split(", ")
    for i in range(len(lst)):
        match = re.search(r"<(.*?)>", lst[i])
        if match:
            lst[i] = match.group(1)
    text = ", ".join(lst)
    return text


class EmailService:
    def __init__(self, service):
        self.service = service

    def search_threads(
        self, query: str, newest_first: bool = False
    ) -> Iterable[dict[str, Any]]:
        """
        Returns an iterable of the message objects based on the given query.
        Searches entire thread instead of just the first email.

        :param service: The Resource item from googleapiclient.discovery.build()
        :param query: The query term. Ex: label:Networking
        """
        results = self.service.users().threads().list(userId="me", q=query).execute()
        threads = results.get("threads", [])

        while "nextPageToken" in results:
            page_token = results["nextPageToken"]

            results = (
                self.service.users()
                .threads()
                .list(userId="me", q=query, pageToken=page_token)
                .execute()
            )

            threads.extend(results.get("threads", []))

        for result in threads:
            thread: List[dict[str, Any]] = (
                self.service.users()
                .threads()
                .get(userId="me", id=result["id"])
                .execute()["messages"]
            )
            if newest_first:
                x = [msg for msg in thread]
                thread = x[::-1]
            for msg in thread:
                yield msg

    def search_messages(self, query: str) -> List[dict[str, str]]:
        """
        Returns a list of the message objects based on the given query. Only
        retrieves the first message object in each thread.

        :param service: The Resource item from googleapiclient.discovery.build()
        :param query: The query term. Ex: from:email@address.com
        """
        result = self.service.users().messages().list(userId="me", q=query).execute()
        messages = []
        if "messages" in result:
            messages.extend(result["messages"])
        while "nextPageToken" in result:
            page_token = result["nextPageToken"]
            result = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, pageToken=page_token)
                .execute()
            )
            if "messages" in result:
                messages.extend(result["messages"])
        return messages

    def parse_parts(
        self, parts, folder_name: str, message: dict[str, str]
    ) -> Iterable[str]:
        """
        Utility function that parses the content of an email partition
        """

        if parts:
            for part in parts:
                mimeType = part.get("mimeType")
                body = part.get("body")
                data = body.get("data")
                if part.get("parts"):
                    # recursively call this function when we see that a part
                    # has parts inside
                    yield from self.parse_parts(part.get("parts"), folder_name, message)
                if mimeType == "text/plain" and data:
                    # if the email part is text plain
                    text = urlsafe_b64decode(data).decode()
                    # print(text)
                    yield text

    def read_message(
        self, message: dict[str, str], *, echo=False, show_trimmed_content=False
    ) -> Email:
        """
        This function takes Gmail API `service` and the given `message_id` and does the following:
            - Parses the contents of the message to Email and returns
            - Downloads any file that is attached to the email and saves it in the folder created

        :param service: the api passed in
        :param message: the message id

        returns: Email containing all information about the message
        """
        msg = (
            self.service.users()
            .messages()
            .get(userId="me", id=message["id"], format="full")
            .execute()
        )

        mail = Email()

        # parts can be the message body, or attachments
        payload = msg["payload"]
        headers = payload.get("headers")
        parts = payload.get("parts")
        folder_name = "email"
        if headers:
            # this section prints email basic info & creates a folder for the email
            for header in headers:
                name = header.get("name")
                value = header.get("value")
                if name.lower() == "from":
                    # we print the From address
                    mail.From = value
                if name.lower() == "to":
                    # we print the To address
                    mail.To = value
                if name.lower() == "subject":
                    # make a directory with the name of the subject
                    mail.Subject = value
                if name.lower() == "date":
                    # we print the date when the message was sent
                    mail.Date = value
                if name.lower() == "cc":
                    mail.Cc = value
            if "To" not in mail.__dict__.keys():
                mail.To = ""
            if mail.Cc and (
                extract_substring(mail.Cc) in extract_substring(mail.To)
                or extract_substring(mail.Cc) in extract_substring(mail.From)
            ):
                mail.Cc = None
        contents = self.parse_parts(parts, folder_name, message)
        mail.Contents = "\n\n".join([c for c in contents])
        if not show_trimmed_content:
            lines = mail.Contents.split("\n")
            filtered_lines = [line for line in lines if not line.startswith(">")]
            if len(filtered_lines) < len(lines):
                filtered_lines = filtered_lines[:-3]
            mail.Contents = "\n".join(filtered_lines).rstrip()
        if echo:
            print("=" * 20)
            print(mail)
            print("=" * 20)
        return mail

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
    ):
        """
        Sends an email based on the given parameters. Returns a None object if send fails.

        :param to: The email address of the recipient.
        :param subject: The subject of the email.
        :param body: The body (main content) of the email.
        """
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject

        # Encode the message and convert it to base64
        message_bytes = message.as_bytes()
        message_b64 = urlsafe_b64encode(message_bytes).decode("utf-8")

        return (
            self.service.users()
            .messages()
            .send(userId="me", body={"raw": message_b64})
            .execute()
        )


class EmailFactory:
    """Factory class for creating Email objects from different data sources"""

    @staticmethod
    def from_db_record(email_record: tuple, contacts: List[tuple]) -> Email:
        """
        Creates an Email object from a database record and associated contacts

        Args:
            email_record: Tuple containing (id, date, summary, content) from emails table
            contacts: List of tuples containing contact information (name, email) for this email

        Returns:
            Email object populated with the database data
        """
        email = Email()
        _, date, _, content = email_record

        # Process contacts into To/From/Cc fields
        contact_strings = [f"{contact[0]} <{contact[1]}>" for contact in contacts]

        # For simplicity, use first contact as From and rest as To
        # This can be enhanced based on actual email direction data if available
        email.From = contact_strings[0]
        email.To = ", ".join(contact_strings[1:])
        email.Cc = None  # Set if CC information is available in your database
        email.Subject = ""  # Set if subject is stored in your database
        email.Contents = content
        email.Date = date

        return email

    @staticmethod
    def to_db_format(email: Email) -> tuple[List[str], str, str, str]:
        """
        Converts an Email object to the format expected by DataBase.add_email()

        Args:
            email: Email object to convert

        Returns:
            Tuple of (contacts, date, content, summary) ready for database insertion
        """
        contacts = email.get_contact_names()
        return (contacts, email.Date, email.Contents, "")  # Add summary if needed


def display_contact_emails(db, contact_name: str = "") -> None:
    """
    Display emails for a specific contact or all contacts using EmailFactory

    Args:
        db: Database instance that implements fetch_emails_with_contacts
        contact_name: Optional name of contact to filter emails by
    """
    contacts = [contact_name] if contact_name else []

    print(f"\nDisplaying emails for {contact_name or 'all contacts'}:")
    print("-" * 50)

    try:
        for email_record, contacts in db.fetch_emails_with_contacts(contacts):
            try:
                email = EmailFactory.from_db_record(email_record, contacts)
                # Filter out any lines that look like they contain base64 or technical data
                content_lines = email.Contents.split("\n")
                filtered_lines = [
                    line
                    for line in content_lines
                    if not any(
                        x in line.lower() for x in ["base64", "token", "boundary="]
                    )
                    and not line.strip().startswith("--")
                ]
                email.Contents = "\n".join(filtered_lines).strip()

                if email.Contents:  # Only print if there's actual content
                    print(email)
                    print("-" * 50)
            except Exception as e:
                print(f"Error displaying email: {str(e)}")
                continue
    except Exception as e:
        print(f"Error fetching emails: {str(e)}")
        return None
