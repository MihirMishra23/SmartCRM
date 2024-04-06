import psycopg2
from typing import Iterator, Union, List


class DataBase:
    def __init__(self, db_name):
        # conn = psycopg2.connect("dbname=" + p_db_name + " user=" + p_user + " password=" + p_pass)
        self.conn = psycopg2.connect(f"dbname={db_name}")
        self.cur = self.conn.cursor()

    def close_db(self):
        self.cur.close()

    def execute_query(self, query: str):
        self.cur.execute(query)

    def fetch_next(self) -> Union[tuple, None]:
        return self.cur.fetchone()

    def fetch_all(self) -> list[tuple]:
        return self.cur.fetchall()

    def add_email(
        self, contacts: List[str], date: str, content: str, summary: str = ""
    ) -> None:
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
        self.cur.execute(f"SELECT id FROM contacts WHERE name IN ({contacts_string});")
        contact_ids = [contact[0] for contact in self.cur.fetchall()]
        query_list = ", ".join(
            [f"{contact_id, email_id}" for contact_id in contact_ids]
        )
        self.cur.execute(
            f"INSERT INTO contact_emails (contact_id, email_id) VALUES {query_list};"
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
