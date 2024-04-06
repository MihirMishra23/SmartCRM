import psycopg2
from typing import Iterator, Union, List


class DataBase:
    def __init__(self, db_name):
        # conn = psycopg2.connect("dbname=" + p_db_name + " user=" + p_user + " password=" + p_pass)
        conn = psycopg2.connect(f"dbname={db_name}")
        self.cur = conn.cursor()

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
        self.cur.execute(
            f"INSERT INTO emails (date, summary, content) VALUES ({date}, {summary}, {content}) RETURNING id"
        )
        email_id = self.cur.fetchone()
        self.cur.execute(
            """INSERT INTO emails (date, summary, content)
VALUES ('2023-03-20', 'Meeting Summary', 'for contact Han Wang and Hahnbee Lee')
RETURNING id;"""
        )
        email_id = cur.fetchone()[0]  # type: ignore

        # contacts into string of contacts

        self.cur.execute(
            "SELECT id FROM contacts WHERE name IN ('Han Wang', 'Hahnbee Lee');"
        )
        contact_ids = [contact[0] for contact in self.cur.fetchall()]
        query_list = ", ".join(
            [f"{contact_id, email_id}" for contact_id in contact_ids]
        )
        self.cur.execute(
            f"INSERT INTO contact_emails (contact_id, email_id) VALUES {query_list};"
        )

    def fetch_emails(self, contacts: tuple = ()) -> Iterator[tuple]:
        if contacts == ():
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
