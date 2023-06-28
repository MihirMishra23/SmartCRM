from __future__ import print_function

import os
import os.path
import pickle

import google
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
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

from sqlalchemy import create_engine, Engine
from models import Base, Contact, Email
from sqlalchemy.orm import Session

from utils import search_messages, read_message, search_threads

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def clear_table(session: Session):
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
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials_cornell.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    
    engine: Engine = create_engine("sqlite:///networking_data.db")
    engine.connect()
    
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)

    clear_table(session)

    try:
        # Call the Gmail API
        service: Resource = build('gmail', 'v1', credentials=creds)
        messages = []
        results = search_threads(service, 'han@mintlify.com')
        for msg in results:
            messages.append(read_message(service, msg, echo=True))
        session.add_all(messages)

        session.commit()
        
        
    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f'An error occurred: {error}')


if __name__ == '__main__':
    main()