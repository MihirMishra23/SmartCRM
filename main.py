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
import csv

from utils import *
from email_utils import *
from drive_utils import *
from gpt_utils import *
from command import *

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
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


def search_emails_and_update_sheet(
    gmail_service: EmailService,
    drive_service: DriveService,
    sheet_id: str,
    contact_df: pd.DataFrame,
    query: str,
):
    """
    Populates the Emails tab based on all listed contacts in the Contacts tab.
    Updates the last contacted on column in the Contacts tab.
    """
    results = gmail_service.search_threads(query=query)

    # for each email to/from a contact, read it (output plain/text to sheet)
    for msg in results:
        # read message
        message = gmail_service.read_message(msg)
        message.To = extract_substring(message.To)
        message.From = extract_substring(message.From)
        if message.Cc:
            message.Cc = extract_substring(message.Cc)

        # collect contact ids
        tos = message.To.split(", ")
        ids: list = []
        for To in tos:
            ids.extend(
                contact_df.index[contact_df["contact info"].str.contains(To)].to_list()
            )
        ids.extend(
            contact_df.index[
                contact_df["contact info"].str.contains(message.From)
            ].to_list()
        )
        if message.Cc:
            ccs = message.Cc.split(", ")
            for cc in ccs:
                ids.extend(
                    contact_df.index[
                        contact_df["contact info"].str.contains(cc)
                    ].to_list()
                )

        # write to Emails tab if the email isn't already in it
        if len(ids) > 0:
            email_df = drive_service.read_sheet(sheet_id, range="Emails!A:M")

            if message.__str__(hide_date=True) not in email_df["content"].to_list():
                parsed_date = datetime.strptime(
                    message.Date, "%a, %d %b %Y %H:%M:%S %z"
                )
                formatted_date = parsed_date.strftime("%m/%d/%Y %I:%M %p")

                try:
                    summary = summarize_email(NAME, message)  # type: ignore
                except openai.BadRequestError:
                    summary = "Summarization failed"

                row_data = {col: "" for col in email_df.columns}
                row_data.update(
                    {
                        "ID": ", ".join(ids),
                        "date": formatted_date,
                        "contact name(s)": ", ".join(
                            contact_df.loc[ids, "name"].to_list()
                        ),
                        "summary": summary,
                        "content": message.__str__(hide_date=True),
                    }
                )
                email_df = email_df.append(row_data, ignore_index=True)
                time.sleep(1)
                drive_service.add_row(
                    sheet_id=sheet_id,
                    row_data=email_df.iloc[-1].to_list(),
                    tab_name="Emails",
                )

                # update last contacted on date in Contacts tab
                for id in ids:
                    d = None
                    if (
                        contact_df.at[id, "last contacted on"] != ""
                        and contact_df.at[id, "last contacted on"] is not None
                    ):
                        try:
                            d = datetime.strptime(
                                contact_df.at[id, "last contacted on"], "%m/%d/%y"
                            ).date()
                        except ValueError:
                            d = datetime.strptime(
                                contact_df.at[id, "last contacted on"], "%m/%d/%Y"
                            ).date()
                    if d is None or d < parsed_date.date():
                        drive_service.update_cell(
                            cell_value=parsed_date.strftime("%m/%d/%y"),
                            cell_loc=f"E{int(id)+1}",
                            sheet_id=sheet_id,
                            tab_name="Contacts",
                        )
                        contact_df.loc[id, "last contacted on"] = parsed_date.strftime(
                            "%m/%d/%y"
                        )


def main():
    gmail_creds = connect(
        token_json_path="gmail_token.json", cred_json_path=GMAIL_CREDENTIALS_PATH
    )
    drive_creds = connect(
        token_json_path="drive_token.json", cred_json_path=DRIVE_CREDENTIALS_PATH
    )

    try:
        gmail_service = EmailService(build("gmail", "v1", credentials=gmail_creds))
        drive_service = DriveService(
            drive_service=build("drive", "v3", credentials=drive_creds),
            sheets_service=build("sheets", "v4", credentials=drive_creds),
        )

        sheet_id = drive_service.search_drive(name=SHEET_NAME, file_type="sheet")

        contact_df = drive_service.read_sheet(sheet_id, range="Contacts!A:M")
        contact_df = contact_df.set_index("ID")

        new_contacts = None
        if os.path.exists("contacts.csv"):
            og_contact_df = pd.read_csv("contacts.csv")
            og_contact_df = og_contact_df.set_index("ID")  # type: ignore
            new_contacts = contact_df.loc[
                [row for row in contact_df.index if row not in og_contact_df.index]
            ]

        with open("log.txt", "r+") as file:
            initialized = file.read() != ""

        if not initialized:
            for _, row in contact_df.iterrows():
                if row["active"].strip().lower() in {"n", "no"}:
                    continue
                contact_address = row["contact info"]
                address = contact_address.split("\n")[0]
                search_emails_and_update_sheet(
                    gmail_service=gmail_service,
                    drive_service=drive_service,
                    sheet_id=sheet_id,
                    contact_df=contact_df,
                    query=f"to:{address} OR from:{address}",
                )
                contact_df = drive_service.read_sheet(sheet_id, range="Contacts!A:M")

                contact_df = contact_df.set_index("ID")
                time.sleep(5)
        elif new_contacts is not None:
            for _, row in new_contacts.iterrows():
                if row["active"].strip().lower() in {"n", "no"}:
                    continue
                address = row["contact info"].split("\n")[0]
                search_emails_and_update_sheet(
                    gmail_service=gmail_service,
                    drive_service=drive_service,
                    sheet_id=sheet_id,
                    contact_df=contact_df,
                    query=f"to:{address} OR from:{address}",
                )
                contact_df = drive_service.read_sheet(sheet_id, range="Contacts!A:M")

                contact_df = contact_df.set_index("ID")
                time.sleep(5)
        with open("log.txt", "r+") as file:
            log = file.read()
            last_run_date = log.split("\n")[-1]
            if initialized:
                search_emails_and_update_sheet(
                    gmail_service=gmail_service,
                    drive_service=drive_service,
                    sheet_id=sheet_id,
                    contact_df=contact_df,
                    query=f"after: {get_previous_day(last_run_date)} AND -to:('')",
                )
            # gmail search query for emails sent after last run date that don't have an empty to field
            query = f"after: {last_run_date} AND in:inbox AND to:*"
            today = datetime.now().strftime("%Y/%m/%d")
            if today != last_run_date:
                if initialized:
                    file.write("\n")
                file.write(datetime.now().strftime("%Y/%m/%d"))
        contact_df.to_csv("contacts.csv")

        # _____________________________________________________________________
        # Reminders. Sends one reminder email if the contact has not been reached
        # out to after a period of time specified by the sheet
        contact_df = drive_service.read_sheet(sheet_id, range="Contacts!A:M")
        contact_df = contact_df.set_index("ID")
        for _, row in contact_df.iterrows():
            if row["reminder"] == "" or row["reminder"] is None:
                continue
            last = row["days since last contact"]
            followup = row["days until next follow up"]
            if not last:
                continue
            if followup.strip() == "" or followup is None:
                followup = 90
            if int(last) >= followup:
                date = datetime.strptime(row["last contacted on"], "%m/%d/%Y")
                date = datetime.strftime(date, "%Y/%m/%d")

                msg = [
                    m
                    for m in gmail_service.search_threads(
                        f"after: {date} SmartCRM Reminder: Follow up with {row['name']}",
                    )
                ]
                if len(msg) == 0:
                    string = ""
                    url = googlesearch.search(
                        f"techcrunch new products at {row['company']}",
                        num_results=3,
                        lang="en",
                    )
                    for _ in range(3):
                        link = next(url)
                        string += summarize_webpage(link)  # type: ignore
                    url = googlesearch.search(
                        f"the verge new products at {row['company']}",
                        num_results=3,
                        lang="en",
                    )
                    for _ in range(3):
                        link = next(url)
                        string += summarize_webpage(link)  # type: ignore
                    company_innovations = summarize_company_innovations(string)

                    threads = gmail_service.search_threads(
                        f"to: {row['contact info']} OR from: {row['contact info']}",
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
                        subject=f"SmartCRM Reminder: Follow up with {row['name']}",
                        body=f"""The last time you reached out to {row['name']} was on \
{row['last contacted on']} ({row['days since last contact']} days ago). Please refer to \
https://docs.google.com/spreadsheets/d/{sheet_id} for additional information.

Potential Response:
{potential_response}

Recent Company Innovations (note that this may not work for small startups):
{company_innovations}
""",
                    )

    except HttpError as error:
        print(type(error))
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
