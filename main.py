from __future__ import print_function

import os
import os.path
import pickle

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import openai
from dotenv import load_dotenv

from utils import *

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


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
    Removes all the entries in the database while retaining the columns
    
    :param session: The sqlalchemy session within which to clear the table
    """
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()

def main():
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
        gmail_service = build("gmail", "v1", credentials=cornell_creds)
        drive_service = build("drive", "v3", credentials=creds)
        sheets_service = build("sheets", "v4", credentials=creds)

        results = search_threads(gmail_service, "han@mintlify.com")
        # for each email matched, read it (output plain/text to console & save HTML and attachments)
        for msg in results:
            message = read_message(gmail_service, msg)
            chat_completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": """I want you to act as a summarizer. Give 2-3 
                            concise sentence summaries of the emails I give you or 
                            give the contact information you can gleam. I am 
                            Mihir Mishra, so you can refer to me in the first 
                            person. Your responses should be to the point and 
                            succinct.""",
                    },
                    {
                        "role": "user",
                        "content": f"{message}",
                    },
                ],
                temperature=0.1,
            )

            print(chat_completion.choices[0].message.content)  # type: ignore
            print()

        # sheet_id = search_drive(
        #     drive_service, name="Mihir Professional Network", file_type="sheet"
        # )

        # # drive appends row to spreadsheet
        # row_data = ["Test 1", "Test 2", "Test 3"]

        # add_row(
        #     sheets_service, row_data=row_data, sheet_id=sheet_id, tab_name="Contacts"
        # )

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
