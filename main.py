from __future__ import print_function

import os
import os.path
import pickle

from google.auth.transport.requests import Request #type: ignore
from google.oauth2.credentials import Credentials #type: ignore
from google_auth_oauthlib.flow import InstalledAppFlow #type: ignore
from googleapiclient.discovery import build #type: ignore
from googleapiclient.errors import HttpError #type: ignore
# for encoding/decoding messages in base64
import base64
# for dealing with attachement MIME types
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from mimetypes import guess_type as guess_mime_type

from sqlalchemy import create_engine
from models import Base, Contact, Email
from sqlalchemy.orm import Session

from utils import search_messages, read_message

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def clear_table(session: Session):
    for table in reversed(Base.metadata.sorted_tables):
        # Delete each row in the table
        session.execute(table.delete())

    # Commit the transaction to make the changes persistent
    session.commit()

def main():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
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
    
    
    engine = create_engine("sqlite:///networking_data.db", echo=True)
    engine.connect()
    
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)

    clear_table(session)

    try:
        # Call the Gmail API
        service = build('gmail', 'v1', credentials=creds)
        results = service.users().threads().list(userId='me', q='mmishrapike').execute().get('threads', [])
        messages = []
        for result in results:
            thread = service.users().threads().get(userId='me', id=result['id']).execute()['messages']
            for msg in thread:
                messages.append(read_message(service, msg))
        session.add_all(messages)

        session.commit()
        
        
    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f'An error occurred: {error}')


if __name__ == '__main__':
    main()