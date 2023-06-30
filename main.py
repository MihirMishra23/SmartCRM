from __future__ import print_function

import os
import os.path
import pickle
import pandas as pd

from google.auth.transport.requests import Request  # type: ignore
from google.oauth2.credentials import Credentials  # type: ignore
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
from googleapiclient.discovery import build  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore

# for encoding/decoding messages in base64
import base64

# for dealing with attachement MIME types
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from mimetypes import guess_type as guess_mime_type

from utils import *

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]

SPREADSHEET_ID = "1eZhFLlhakNtRC8QYyrNW1b__FxlXeRdZ3R-9U5F4ETg"
RANGE_NAME = "Sheet1!A1:H"


def main():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials_cornell.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        # Call the Gmail API
        gmail_service = build("gmail", "v1", credentials=creds)
        drive_service = build("sheets", "v4", credentials=creds)

        results = search_threads(gmail_service, "han@mintlify.com")
        # for each email matched, read it (output plain/text to console & save HTML and attachments)
        for msg in results:
            message = read_message(gmail_service, msg, echo=True)

        # drive appends row to spreadsheet
        row_data = ["Test 1", "Test 2", "Test 3"]

        # Add the row to the sheet
        value_input_option = "USER_ENTERED"
        insert_data_option = "INSERT_ROWS"
        value_range_body = {
            "values": [row_data],
            "majorDimension": "ROWS",
        }
        add = (
            drive_service.spreadsheets()
            .values()
            .append(
                spreadsheetId=SPREADSHEET_ID,
                range="Sheet1!A4",
                valueInputOption=value_input_option,
                insertDataOption=insert_data_option,
                body=value_range_body,
            )
        ).execute()

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
