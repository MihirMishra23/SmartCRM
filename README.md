# Inbox Manager and CRM

## Initialization

Follow the tutorial at this website to set up the google APIs: https://developers.google.com/workspace/guides/get-started

The general steps are listed below
1. In terminal run ```git clone https://github.com/MihirMishra23/Inbox-Manager.git``` in the directory location you want to store this file (The install location will not affect the system).
2. Run the following line in terminal ```pip install -r requirements.txt```

The below steps are very long and confusing. I'm working on seeing if I can avoid all of these but this is what I have for now.

3. Create a new cloud project, following the instructions here https://developers.google.com/workspace/guides/create-project. The name of the project has no effect on the system.
4. Enable the APIs. Go to https://console.cloud.google.com/apis/library? and make sure the project is selected as the one you just created (the project name should be on the top left of the page, directly to the right of "Google Cloud"). Enable the "Gmail API", "Google Sheets API", and "Google Drive API"
5. Configure OAuth Consent. Go to https://console.cloud.google.com/apis/credentials/consent? and make sure the selected project is the one you created. Set "User Type" to "External" and press "Create". Fill out the "App information" and "Developer contact information" and then skip through the rest of the pages.
6. Get the credentials json. Go to https://console.cloud.google.com/apis/credentials? and find the OAuth Client ID you just created. Go to actions on the far right and press the download button and download the json. Put the json in the folder this repo is in and put the name of the json file in command.py. Ex. "credentials.json"
7. If you have separate accounts for your gmail and sheets access, repeat steps 3-6 with the second account. You should have 2 json files, with the names of both json files stored in command.py
8. Fill the variables in command.py with the relevant information. Read the comments in the file to understand what to put where.
9. Ensure your Google Sheet is set up as defined in the Sheet Structure section
10. Run main.py

The first time you run main.py, it will initialize the system. It will open tabs in google prompting you to enable access to certain APIs. Please do so. If you have multiple google accounts, enable API access for the accounts in order of the gmail account, then the drive account.

### Sheet Structure
The spreadsheet should have 2 tabs: Contacts and Emails. Contacts will be something the user fills out (with the exception of the "last contacted on" column) and the Emails tab will be handled automatically.

The Contacts tab should have the headers in the following order: ID, name, company, contact info, last contacted on, days since last contact, days until next follow-up, notes, type, active/inactive, keywords
The Emails tab should have the headers in the following order: ID, date, contact name(s), summary, content

Note that the summary column is not supported yet.

### Important Initialization Notes
- For cells in the contact info column, the email must be the first entry (ex. email\nphone number).
- Emails in the contact info column MUST be lowercase
- You may want to set up a formula for the days since last contact column of the Contacts tab. I use =IF(ISDATE(cell), TODAY()-cell, )

## Use
The only file that should be run is main.py, which will update the "last contacted on" column of the Contacts tab and the Emails tab based on any new emails since the last time it was run. See the log.txt file to see the last date it was run.

## Filesystem Explanation
The only files users need to edit for system initialization are command.py (fill the variables) and the credential json files. Users can look at log.txt to see the last date that main.py was run.
