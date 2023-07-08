from __future__ import print_function

import os
import os.path
import pickle

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import openai
import pandas as pd
import re

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


def extract_substring(text):
    match = re.search(r"<(.*?)>", text)
    if match:
        return match.group(1)
    else:
        return text


def main():
    creds = connect(token_json_path="token.json", cred_json_path="credentials.json")
    cornell_creds = connect(
        token_json_path="token_cornell.json", cred_json_path="credentials_cornell.json"
    )

    try:
        gmail_service = build("gmail", "v1", credentials=cornell_creds)
        drive_service = build("drive", "v3", credentials=creds)
        sheets_service = build("sheets", "v4", credentials=creds)

        sheet_id = search_drive(
            drive_service, name="Mihir Professional Network", file_type="sheet"
        )

        contact_vals = read_sheet(sheets_service, sheet_id, range="Contacts!A:D")

        contact_df = pd.DataFrame(contact_vals[1:], columns=contact_vals[0])
        contact_df = contact_df.set_index("ID")

        results = search_threads(gmail_service, "han@mintlify.com")
        # for each email matched, read it (output plain/text to console & save HTML and attachments)
        for msg in results:
            message = read_message(gmail_service, msg)
            message.To = extract_substring(message.To)
            message.From = extract_substring(message.From)
            ids: list = contact_df.index[
                contact_df["contact info"].str.contains(message.To)
            ].to_list()
            ids.extend(
                contact_df.index[
                    contact_df["contact info"].str.contains(message.From)
                ].to_list()
            )
            # print(ids, message.To, message.From)
            if len(ids) > 0:
                emails = read_sheet(sheets_service, sheet_id, range="Emails!A:E")
                email_df = pd.DataFrame(emails[1:], columns=emails[0])
                email_df = email_df.set_index("ID")

                if message.__str__(hide_date=True) not in email_df["content"].to_list():
                    print("Reached")
                    row_data = [
                        ",".join(ids),
                        message.Date,
                        ",".join(contact_df.loc[ids, "name"].to_list()),
                        None,
                        message.__str__(hide_date=True),
                    ]
                    add_row(
                        sheets_service,
                        sheet_id=sheet_id,
                        row_data=row_data,
                        tab_name="Emails",
                    )

            # summary = (
            #     openai.ChatCompletion.create(
            #         model="gpt-3.5-turbo",
            #         messages=[
            #             {
            #                 "role": "system",
            #                 "content": """I am Mihir Mishra. Refer to Mihir as "you". Summarize the emails I
            #             give you in 2 or fewer sentences. Never give me my own
            #             contact information. Use the email handle or email content to fill out all information.
            #             Your output should be in the following format:

            #             Name
            #             Company (and possition if applicable)
            #             Contact Info
            #             Summary """,
            #             },
            #             {
            #                 "role": "user",
            #                 "content": f"{message}",
            #             },
            #         ],
            #         temperature=0.1,
            #     )
            #     .choices[0]  # type: ignore
            #     .message.content
            # )

            # print(summary)
            # print()

            # info = summary.split("\n")

            # # TODO: make this a more robust method of checking if contact already in sheet
            # if info[0] not in id_names_dict.values():
            #     row_data = [len(id_names_dict), info[0], info[1], info[2]]

            #     add_row(
            #         sheets_service,
            #         row_data=row_data,
            #         sheet_id=sheet_id,
            #         tab_name="Contacts",
            #     )
            #     sheet_vals = read_sheet(
            #         sheets_service, sheet_id, range="Contacts!A:B", axis="columns"
            #     )
            #     id_names_dict = {
            #         sheet_vals[0][i]: sheet_vals[1][i]
            #         for i in range(len(sheet_vals[0]))
            #     }

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
