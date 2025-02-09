import psycopg2
from typing import Iterator, Union, List
import pandas as pd
from tqdm import tqdm

class DataBase:
    def __init__(self, db_name):
        # conn = psycopg2.connect("dbname=" + p_db_name + " user=" + p_user + " password=" + p_pass)
        self.conn = psycopg2.connect(f"dbname={db_name}")
        self.cur = self.conn.cursor()

    def close(self):
        self.cur.close()
        self.conn.close()

    def execute_query(self, query: str):
        self.cur.execute(query)

    def fetch_next(self) -> Union[tuple, None]:
        return self.cur.fetchone()

    def fetch_all(self) -> list[tuple]:
        return self.cur.fetchall()

    def add_email(
        self, contacts: List[str], date: str, content: str, summary: str = ""
    ) -> None:
        """
        Add email to the database
        Params: contacts: list of contacts (names only),
                date: date of email (date only),
                content: content of email,
                summary: summary of email
        """
        # this is to avoid issue with sql queries where text has a single quote
        content = content.replace("'", "''")
        summary = summary.replace("'", "''")

        # put email into emails database
        self.cur.execute(
            f"INSERT INTO emails (date, summary, content) VALUES ('{date}', '{summary}', '{content}') RETURNING id"
        )
        email_id = self.cur.fetchone()[0]  # type: ignore

        # put contacts and emails into contact_emails database
        contacts_string = ", ".join([f"'{contact}'" for contact in contacts])
        self.cur.execute(
            f"SELECT id FROM contacts WHERE name IN ({contacts_string}) OR contact_info IN ({contacts_string});"
        )
        contact_ids = [contact[0] for contact in self.cur.fetchall()]
        query_list = ", ".join(
            [f"{contact_id, email_id}" for contact_id in contact_ids]
        )
        print("query_list:", query_list)
        self.cur.execute(
            f"INSERT INTO contact_emails (contact_id, email_id) VALUES {query_list};"
        )
        self.cur.execute(
            f"UPDATE contacts SET last_contacted = '{date}' WHERE name IN ({contacts_string}) AND last_contacted < '{date}';"
        )
        self.conn.commit()

    def fetch_emails(self, contacts: List = []) -> Iterator[tuple]:
        if contacts == []:
            self.cur.execute("SELECT * FROM emails")
            return iter(self.cur)
        self.cur.execute(
            f"""SELECT e.*
FROM emails e
JOIN contact_emails ce ON e.id = ce.email_id
JOIN contacts c ON ce.contact_id = c.id
WHERE c.name IN {contacts};"""
        )
        return iter(self.cur)

    def fetch_contacts(self) -> Iterator[tuple]:
        self.cur.execute("SELECT * FROM contacts")
        return iter(self.cur)

    def reset_database(self):
        command = "TRUNCATE TABLE contacts, contact_emails, emails RESTART IDENTITY CASCADE"
        self.cur.execute(command)
        self.conn.commit()
        
    def add_contact(self, name: str, company: str, contact_info: str, last_contacted: str, follow_up_date: str, warm: bool, reminder: bool, notes: str):
        self.cur.execute(
            f"INSERT INTO contacts (name, company, contact_info, last_contacted, follow_up_date, warm, notes) VALUES ('{name}', '{company}', '{contact_info}', '{last_contacted}', '{follow_up_date}', {warm}, '{notes}')"
        )
        self.conn.commit()
        
    def load_contacts_from_csv(self, csv_file: str):
        df = pd.read_csv(csv_file, header=0)
        for _, row in tqdm(df.iterrows(), desc="Loading contacts", total=len(df)):
            name = str(row["name"])
            company = str(row["company"])
            contact_info = str(row["contact_info"])
            last_contacted = str(row["last_contacted"])
            follow_up_date = str(row["follow_up_date"])
            warm = bool(row["warm"])
            reminder = bool(row["reminder"])
            notes = str(row["notes"])
            self.add_contact(name, company, contact_info, last_contacted, follow_up_date, warm, reminder, notes)
