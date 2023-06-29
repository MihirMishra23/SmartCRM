from __future__ import print_function

import os
import os.path
import pickle
import pandas as pd

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

from utils import *

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

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

    tracker = pd.read_csv("tracker.csv", )
    tracker = tracker.iloc[0:0]


    try:
        # Call the Gmail API
        service = build('gmail', 'v1', credentials=creds)
                    
        results = search_threads(service, "han@mintlify.com")
        # print(f"Found {len(results)} results.")
        # for each email matched, read it (output plain/text to console & save HTML and attachments)
        for msg in results:
            message = read_message(service, msg, echo=True)
            if message.To not in tracker['Email'].values:
                tracker.loc[len(tracker.index)] = [message.To, [message.__repr__()]]
            else:
                tracker[tracker['Email'] == message.To].iloc[0]['Communication'].append(message.__repr__())
            if message.From not in tracker['Email'].values:
                tracker.loc[len(tracker.index)] = [message.From, [message.__repr__()]]
            else:
                tracker[tracker['Email'] == message.From].iloc[0]['Communication'].append(message.__repr__())
        tracker.to_csv("tracker.csv", index=False)
        
        
    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f'An error occurred: {error}')


if __name__ == '__main__':
    main()