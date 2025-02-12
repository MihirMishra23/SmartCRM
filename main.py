from __future__ import print_function

import os
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import openai
import pandas as pd
from datetime import datetime
import time
import googlesearch
import psycopg2
from tqdm import tqdm

from utils import *
from email_utils import (
    EmailService,
    EmailFactory,
    display_contact_emails,
    extract_substring,
)
from gpt_utils import *
import postgres_utils
from command import *

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


def connect_google(
    token_json_path: str = "token.json", cred_json_path: str = "credentials.json"
):
    """
    Returns credential to connect to API. This cred object can be used to build
    API resources.

    :param token_json_path: The path to the token json. If already filled,
        doesn't change
    :param cred_json_path: The path to the credential file. This is exported from google.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_json_path):
        creds = Credentials.from_authorized_user_file(token_json_path, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing credentials")
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(cred_json_path, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_json_path, "w") as token:
            token.write(creds.to_json())
    return creds


def search_emails_and_update_db(
    gmail_service: EmailService,
    db: postgres_utils.DataBase,
    query: str,
):
    """
    Stores emails in postgres database based on contact queries
    """
    # Get all email addresses for the contact
    db.cur.execute(
        """
        SELECT value 
        FROM contact_methods 
        WHERE method_type = 'email'
        """
    )
    email_addresses = [row[0] for row in db.cur.fetchall()]

    # Build query for all email addresses
    query_parts = []
    for email in email_addresses:
        query_parts.append(f"to:{email} OR from:{email}")

    full_query = " OR ".join(query_parts)
    if query:
        full_query = f"({full_query}) AND {query}"

    results = gmail_service.search_threads(query=full_query)

    # for each email to/from a contact, read it and store in database
    for msg in results:
        message = gmail_service.read_message(msg)
        message.To = extract_substring(message.To)
        message.From = extract_substring(message.From)
        if message.Cc:
            message.Cc = extract_substring(message.Cc)

        # Get all contacts involved in this email
        contacts = []
        contacts.extend(message.To.split(", "))
        contacts.append(message.From)
        if message.Cc:
            contacts.extend(message.Cc.split(", "))

        # Parse date to ISO format for postgres
        parsed_date = datetime.strptime(message.Date, "%a, %d %b %Y %H:%M:%S %z")
        formatted_date = parsed_date.date().isoformat()

        try:
            summary = summarize_email(NAME, str(message))
        except openai.BadRequestError:
            summary = "Summarization failed"

        # Add email to database
        db.add_email(
            contacts=contacts,
            date=formatted_date,
            content=message.__str__(hide_date=True),
            summary=summary,
        )


def populate_emails(
    gmail_service: EmailService,
    db: postgres_utils.DataBase,
):
    """
    Populates the Emails tab based on all listed contacts in the Contacts tab.
    """
    for contact in db.fetch_contacts_as_dicts():
        contact_info = contact["contact_info"]
        query = f"to:{contact_info} OR from:{contact_info}"
        results = gmail_service.search_threads(query=query)
        for msg in results:
            # read message
            email = gmail_service.read_message(msg)
            email_contacts = email.get_contact_names()
            # change format of date to match postgres db
            datetime_obj = datetime.strptime(email.Date, "%a, %d %b %Y %H:%M:%S %z")
            email_date = datetime_obj.date().isoformat()
            db.add_email(email_contacts, email_date, email.Contents)


def process_emails(
    gmail_service: EmailService,
    db: postgres_utils.DataBase,
    contact: dict,
) -> None:
    """
    Updates emails in postgres database for a specific contact
    """
    # Get contact's email addresses
    email_addresses = [
        method["value"]
        for method in contact["contact_methods"]
        if method["type"] == "email"
    ]

    if not email_addresses:
        return

    # Build query for all email addresses
    query_parts = [f"to:{email} OR from:{email}" for email in email_addresses]
    query = " OR ".join(query_parts)

    results = gmail_service.search_threads(query=query)

    # Process each email
    for msg in results:
        message = gmail_service.read_message(msg)

        # Parse date to ISO format for postgres, handling UTC notation
        try:
            date_str = message.Date.replace(" (UTC)", "")
            parsed_date = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
        except ValueError:
            # If timezone parsing fails, assume UTC
            date_str = message.Date.replace(" (UTC)", " +0000")
            parsed_date = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")

        formatted_date = parsed_date.date().isoformat()

        try:
            summary = summarize_email(NAME, str(message))
        except openai.BadRequestError:
            summary = "Summarization failed"

        # Convert to database format and store
        contacts, date, content, _ = EmailFactory.to_db_format(message)
        db.update_emails_for_contact(
            contact_id=contact["id"],
            date=formatted_date,
            content=content,
            summary=summary,
        )


def main():
    gmail_creds = connect_google(
        token_json_path="gmail_token.json", cred_json_path=GMAIL_CREDENTIALS_PATH
    )

    try:
        # Connect to postgres
        db = postgres_utils.DataBase("postgres")

        # Connect to Gmail API
        gmail_service = EmailService(build("gmail", "v1", credentials=gmail_creds))

        # Get all contacts from database
        contacts = db.fetch_contacts_as_dicts()

        # Check if this is first run
        with open("log.txt", "r+") as file:
            initialized = file.read() != ""

        if not initialized:
            # Initial population of emails for each contact
            for contact in tqdm(contacts, desc="Processing emails"):
                process_emails(
                    gmail_service=gmail_service,
                    db=db,
                    contact=contact,
                )

            # Display all processed emails using email_utils function
            # display_contact_emails(db)

            db.close()
            return

        # Handle new emails since last run
        with open("log.txt", "r+") as file:
            log = file.read()
            last_run_date = log.split("\n")[-1] if log else None

            if last_run_date:
                for contact in contacts:
                    process_emails(
                        gmail_service=gmail_service,
                        db=db,
                        contact=contact,
                    )

                # Display newly processed emails
                today = datetime.now().date().isoformat()
                print(f"\nNew emails since {last_run_date}:")
                # display_contact_emails(db)

            today = datetime.now().strftime("%Y/%m/%d")
            if not last_run_date or today != last_run_date:
                if initialized:
                    file.write("\n")
                file.write(today)

            # Handle reminders
            for contact in contacts:
                if not contact.get("reminder"):
                    continue

                last_contact_date = contact.get("last_contacted")
                if not last_contact_date:
                    continue

                followup_days = contact.get("follow_up_date", 90)

                # Calculate days since last contact
                last_date = datetime.strptime(last_contact_date, "%Y-%m-%d").date()
                days_since = (datetime.now().date() - last_date).days

                if days_since >= followup_days:
                    # Check if reminder already sent
                    reminder_subject = (
                        f"SmartCRM Reminder: Follow up with {contact['name']}"
                    )
                    existing_reminders = gmail_service.search_threads(
                        f"after: {last_contact_date} {reminder_subject}"
                    )

                    if not list(existing_reminders):
                        # Generate reminder content
                        string = ""
                        url = googlesearch.search(
                            f"techcrunch new products at {contact['company']}",
                            num_results=3,
                            lang="en",
                        )
                        for _ in range(3):
                            link = next(url)
                            string += summarize_webpage(link)  # type: ignore
                        url = googlesearch.search(
                            f"the verge new products at {contact['company']}",
                            num_results=3,
                            lang="en",
                        )
                        for _ in range(3):
                            link = next(url)
                            string += summarize_webpage(link)  # type: ignore
                        company_innovations = summarize_company_innovations(string)

                        threads = gmail_service.search_threads(
                            f"to: {contact['contact_info']} OR from: {contact['contact_info']}",
                            newest_first=True,
                        )
                        msgs = []
                        num_msgs = 0
                        for msg in threads:
                            msgs.append(gmail_service.read_message(msg).__str__())
                            num_msgs += 1
                            if num_msgs >= 3:
                                break

                        potential_response = generate_response_email_from_messages(
                            "\n".join(msgs), NAME
                        )

                        gmail_service.send_email(
                            to="mrm367@cornell.edu",
                            subject=reminder_subject,
                            body=f"""The last time you reached out to {contact['name']} was on \
{last_contact_date} ({days_since} days ago).

Potential Response:
{potential_response}

Recent Company Innovations (note that this may not work for small startups):
{company_innovations}
""",
                        )

    except HttpError as error:
        print(f"An error occurred: {error}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
