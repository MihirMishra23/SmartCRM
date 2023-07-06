from __future__ import print_function

import os
import os.path
import pickle
import pandas as pd
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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

SPREADSHEET_ID = "1WArI3tICbjsE3VegiU3wJqHK4BWkdgjDSunitGVeXUs"
RANGE_NAME = "Sheet1!A1:H"


def connect(
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
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(cred_json_path, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_json_path, "w") as token:
            token.write(creds.to_json())
    return creds


def main():
    creds = connect(token_json_path="token.json", cred_json_path="credentials.json")
    cornell_creds = connect(
        token_json_path="token_cornell.json", cred_json_path="credentials_cornell.json"
    )

    try:
        # Call the Gmail API
        gmail_service = build("gmail", "v1", credentials=cornell_creds)
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
