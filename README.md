# Inbox-Manager

## Initialization

Follow the tutorial at this website to set up the google APIs: https://developers.google.com/workspace/guides/get-started

The general steps are listed below

1. Run the following line in terminal ```pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib```
2. Go to https://console.developers.google.com/apis/dashboard and enable the gmail, drive, and sheets APIs (you may want to create a new project when prompted if you haven't already)
3. Create your credentials and download json. Save the file to this folder.

Note that if you want to scan gmail on one email and save it to drive in another, you will need to repeat the above steps and save the resulting json in a differently named file.


Now, fill the variables in command.py with the relevant information (open the file to see what goes where).


### Sheet structure
The spreadsheet should have 2 tabs: Contacts and Emails. Contacts will be something the user fills out (with the exception of the "last contacted on" column) and the Emails tab will be handled automatically.

The Contacts tab should have the headers in the following order: ID, name, company, contact info, last contacted on, days since last contact, days until next follow-up, notes, type, active/inactive, keywords
The Emails tab should have the headers in the following order: ID, date, contact name(s), summary, content

Note that the summary column is not supported yet.

### Important Initialization Notes
- For cells in the contact info column, the email must be the first entry (ex. email\nphone number).
- Emails in the contact info column MUST be lowercase
- You may want to set up a formula for the days since last contact column of the Contacts tab. I use =IF(ISDATE(cell), TODAY()-cell, )

## Use
When ```command.INITIALIZED=False``` the system will search for emails to/from every contact in the database, which may result in a system overload. Once the system is initialized and ```command.INITIALIZED``` is automatically changed, the only file that should be run is main.py, which will update the "last contacted on" column of the Contacts tab and the Emails tab based on any new emails since the last time it was run.

## Filesystem Explanation
The only files users need to edit for system initialization are command.py (fill the variables) and the credential json files. Users can look at log.txt to see the last date that main.py was run.
