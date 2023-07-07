from __future__ import print_function
from typing import Iterable, Any, List, Optional, Literal

import os
from datetime import datetime

from dataclasses import dataclass
from base64 import urlsafe_b64decode


@dataclass(init=False, repr=False)
class Email:
    To: str
    From: str
    Subject: str
    Contents: str
    Date: datetime

    def __str__(self) -> str:
        return f"Date: {self.Date}\nTo: {self.To}\nFrom: {self.From}\nSubject: {self.Subject}\n\n{self.Contents}"


@dataclass(init=False)
class Contact:
    name: str
    email: str
    phone: str
    contact: List[Email]


def search_threads(service, query: str) -> Iterable[dict[str, Any]]:
    """
    Returns an iterable of the message objects based on the given query.
    Searches entire thread instead of just the first email.

    :param service: The Resource item from googleapiclient.discovery.build()
    :param query: The query term. Ex: label:Networking
    """
    results = (
        service.users()
        .threads()
        .list(userId="me", q=query)
        .execute()
        .get("threads", [])
    )
    for result in results:
        thread: List[dict[str, Any]] = (
            service.users()
            .threads()
            .get(userId="me", id=result["id"])
            .execute()["messages"]
        )
        for msg in thread:
            yield msg


def search_messages(service, query: str) -> List[dict[str, str]]:
    """
    Returns a list of the message objects based on the given query. Only
    retrieves the first message object in each thread.

    :param service: The Resource item from googleapiclient.discovery.build()
    :param query: The query term. Ex: from:email@address.com
    """
    result = service.users().messages().list(userId="me", q=query).execute()
    messages = []
    if "messages" in result:
        messages.extend(result["messages"])
    while "nextPageToken" in result:
        page_token = result["nextPageToken"]
        result = (
            service.users()
            .messages()
            .list(userId="me", q=query, pageToken=page_token)
            .execute()
        )
        if "messages" in result:
            messages.extend(result["messages"])
    return messages


def parse_parts(
    service, parts, folder_name: str, message: dict[str, str]
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
                yield from parse_parts(service, part.get("parts"), folder_name, message)
            if mimeType == "text/plain" and data:
                # if the email part is text plain
                text = urlsafe_b64decode(data).decode()
                # print(text)
                yield text


def read_message(
    service, message: dict[str, str], *, echo=False, show_trimmed_content=False
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
        service.users()
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
    contents = parse_parts(service, parts, folder_name, message)
    mail.Contents = "\n\n".join([c for c in contents])
    if not show_trimmed_content:
        lines = mail.Contents.split("\n")
        filtered_lines = [line for line in lines if not line.startswith(">")]
        if len(filtered_lines) < len(lines):
            filtered_lines = filtered_lines[:-3]
        mail.Contents = "\n".join(filtered_lines).rstrip()
    if echo:
        print("=" * 20)
        print(
            f"From: {mail.From}\nTo: {mail.To}\nSubject: {mail.Subject}\n\n{mail.Contents}"
        )
        print("=" * 20)
    return mail


def search_drive(
    service,
    *,
    name: Optional[str] = None,
    parent: Optional[str] = None,
    file_type: Literal["sheet", "folder", None] = None,
) -> str:
    """
    Returns the file id of the first query

    :param name: The name of the requested file.
    :param parent: The name of the parent folder.
    :param file_type:
    """
    lst = []
    if name:
        lst.append(f"name = '{name}'")
    if parent:
        lst.append(f"parents in {search_drive(service, name=parent)}")
    if file_type:
        if file_type == "folder":
            lst.append(f"mimeType = 'application/vnd.google-apps.folder'")
        if file_type == "sheet":
            lst.append(f"mimeType = 'application/vnd.google-apps.spreadsheet'")
    query = " and ".join(lst)
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get("files", [])
    if not items:
        return ""
    return items[0]["id"]


def add_row(service, *, row_data: list, sheet_id: str, tab_name: str):
    """
    Adds a row to the given spreadsheet.

    :param row_data: The row data to append to the sheet
    :param sheet_id: The id of the spreadsheet to add to.
    :param tab_name: The name of the specific tab to add to.
    """
    value_input_option = "USER_ENTERED"
    insert_data_option = "INSERT_ROWS"
    value_range_body = {
        "values": [row_data],
        "majorDimension": "ROWS",
    }
    (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=sheet_id,
            range=f"{tab_name}!A1",
            valueInputOption=value_input_option,
            insertDataOption=insert_data_option,
            body=value_range_body,
        )
    ).execute()


def read_sheet(
    service,
    sheet_id: str,
    *,
    range: str,
    axis: Literal["rows", "columns"] = "rows",
):
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=range, majorDimension=axis.upper())
        .execute()
    )
    values = result.get("values", [])
    return values
