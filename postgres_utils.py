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
        Add email to the database, avoiding duplicates while maintaining contact relationships
        Params: contacts: list of contacts (names only),
                date: date of email (date only),
                content: content of email,
                summary: summary of email
        """
        # Escape single quotes
        content = content.replace("'", "''")
        summary = summary.replace("'", "''")

        # First check if this email content already exists
        self.cur.execute(f"SELECT id FROM emails WHERE content = '{content}'")
        existing_email = self.cur.fetchone()

        if existing_email:
            email_id = existing_email[0]
        else:
            # Add new email if it doesn't exist
            self.cur.execute(
                f"INSERT INTO emails (date, summary, content) VALUES ('{date}', '{summary}', '{content}') RETURNING id"
            )
            item = self.cur.fetchone()
            if item is None:
                raise ValueError("Failed to insert email")
            email_id = item[0]

        # Get contact IDs for all involved contacts
        contacts_string = ", ".join([f"'{contact}'" for contact in contacts])
        self.cur.execute(
            f"""
            SELECT DISTINCT c.id 
            FROM contacts c
            JOIN contact_methods cm ON c.id = cm.contact_id
            WHERE cm.value IN ({contacts_string})
            """
        )
        contact_ids = [contact[0] for contact in self.cur.fetchall()]

        # Add contact-email relationships if they don't exist
        for contact_id in contact_ids:
            self.cur.execute(
                f"""
                INSERT INTO contact_emails (contact_id, email_id)
                VALUES ({contact_id}, {email_id})
                ON CONFLICT (contact_id, email_id) DO NOTHING
                """
            )

            # Update last_contacted date if this is more recent
            self.cur.execute(
                f"""
                UPDATE contacts 
                SET last_contacted = '{date}' 
                WHERE id = {contact_id}
                AND (last_contacted IS NULL OR last_contacted < '{date}')
                """
            )

        self.conn.commit()

    def fetch_emails(self, contacts: List = []) -> Iterator[tuple]:
        if contacts == []:
            self.cur.execute("SELECT * FROM emails")
            return iter(self.cur)
        contacts_string = ", ".join([f"'{contact}'" for contact in contacts])
        self.cur.execute(
            f"""SELECT e.*
FROM emails e
JOIN contact_emails ce ON e.id = ce.email_id
JOIN contacts c ON ce.contact_id = c.id
WHERE c.name IN ({contacts_string});"""
        )
        return iter(self.cur)

    def fetch_contacts(self) -> Iterator[tuple]:
        self.cur.execute("SELECT * FROM contacts")
        return iter(self.cur)

    def fetch_contacts_as_dicts(self):
        """
        Fetch contacts with their contact methods from the database
        """
        query = f"""
            SELECT 
                c.*,
                json_agg(
                    json_build_object(
                        'type', cm.method_type,
                        'value', cm.value,
                        'is_primary', cm.is_primary
                    )
                ) as contact_methods
            FROM contacts c
            LEFT JOIN contact_methods cm ON c.id = cm.contact_id
            GROUP BY c.id
        """
        self.cur.execute(query)
        desc = self.cur.description
        assert desc is not None
        columns = [col.name for col in desc]
        contacts = [dict(zip(columns, row)) for row in self.cur.fetchall()]
        return contacts

    def reset_database(self):
        command = (
            "TRUNCATE TABLE contacts, contact_emails, emails RESTART IDENTITY CASCADE"
        )
        self.cur.execute(command)
        self.conn.commit()

    def add_contact(
        self,
        name: str,
        contact_methods: List[
            dict
        ],  # List of {type: str, value: str, is_primary: bool}
        company: Union[str, None] = None,
        last_contacted: Union[str, None] = None,
        follow_up_date: Union[str, None] = None,
        warm: bool = False,
        reminder: bool = True,
        notes: Union[str, None] = None,
        position: Union[str, None] = None,
    ):
        """Add a contact with multiple contact methods"""
        # check for nans
        if company == "nan":
            company = None
        if last_contacted == "nan":
            last_contacted = None
        if follow_up_date == "nan":
            follow_up_date = None
        if notes == "nan":
            notes = None
        if position == "nan":
            position = None

        # Insert the contact first
        self.cur.execute(
            """
            INSERT INTO contacts 
            (name, company, last_contacted, follow_up_date, warm, notes, reminder, position) 
            VALUES 
            (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                name,
                company,
                last_contacted,
                follow_up_date,
                warm,
                notes,
                reminder,
                position,
            ),
        )
        item = self.cur.fetchone()
        if item is None:
            raise ValueError("Failed to insert contact")
        contact_id = item[0]

        # Add each contact method
        for method in contact_methods:
            self.cur.execute(
                f"""
                INSERT INTO contact_methods 
                (contact_id, method_type, value, is_primary)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    contact_id,
                    method["type"],
                    method["value"],
                    method.get("is_primary", False),
                ),
            )

        self.conn.commit()

    def load_contacts_from_csv(self, csv_file: str):
        df = pd.read_csv(csv_file, header=0)
        for _, row in tqdm(df.iterrows(), desc="Loading contacts", total=len(df)):
            contact_methods = []
            if not pd.isna(row["email"]):
                contact_methods.append(
                    {"type": "email", "value": str(row["email"]), "is_primary": True}
                )
            if not pd.isna(row["linkedin"]):
                contact_methods.append(
                    {
                        "type": "linkedin",
                        "value": str(row["linkedin"]),
                        "is_primary": False if len(contact_methods) > 0 else True,
                    }
                )
            if not pd.isna(row["phone"]):
                contact_methods.append(
                    {"type": "phone", "value": str(row["phone"]), "is_primary": False}
                )

            self.add_contact(
                name=str(row["name"]),
                contact_methods=contact_methods,
                company=str(row["company"]),
                last_contacted=str(row["last_contacted"]),
                follow_up_date=str(row["follow_up_date"]),
                warm=bool(row["warm"]),
                reminder=bool(row["reminder"]),
                notes=str(row["notes"]),
                position=str(row["position"]),
            )

    def update_emails_for_contact(
        self,
        contact_id: int,
        date: str,
        content: str,
        summary: str = "",
    ) -> None:
        """
        Add email to the database for a specific contact, avoiding duplicates
        """
        # Escape single quotes
        content = content.replace("'", "''")
        summary = summary.replace("'", "''")

        # First check if this email content already exists
        self.cur.execute(f"SELECT id FROM emails WHERE content = '{content}'")
        existing_email = self.cur.fetchone()

        if existing_email:
            email_id = existing_email[0]
        else:
            # Add new email if it doesn't exist
            self.cur.execute(
                f"INSERT INTO emails (date, summary, content) VALUES ('{date}', '{summary}', '{content}') RETURNING id"
            )
            item = self.cur.fetchone()
            if item is None:
                raise ValueError("Failed to insert email")
            email_id = item[0]

        # Add contact-email relationship if it doesn't exist
        self.cur.execute(
            f"""
            INSERT INTO contact_emails (contact_id, email_id)
            VALUES ({contact_id}, {email_id})
            ON CONFLICT (contact_id, email_id) DO NOTHING
            """
        )

        # Update last_contacted date if this is more recent
        self.cur.execute(
            f"""
            UPDATE contacts 
            SET last_contacted = '{date}' 
            WHERE id = {contact_id}
            AND (last_contacted IS NULL OR last_contacted < '{date}')
            """
        )

        self.conn.commit()

    def fetch_emails_with_contacts(
        self, contacts: List[str] = []
    ) -> Iterator[tuple[tuple, List[tuple]]]:
        """
        Fetch emails with their associated contacts from the database

        Args:
            contacts: Optional list of contact names to filter by

        Returns:
            Iterator of tuples containing (email_record, list_of_contacts)
            where email_record is (id, date, summary, content)
            and list_of_contacts is a list of (name, email) tuples
        """
        if contacts:
            contacts_string = ", ".join([f"'{contact}'" for contact in contacts])
            query = f"""
                WITH email_ids AS (
                    SELECT DISTINCT e.id
                    FROM emails e
                    JOIN contact_emails ce ON e.id = ce.email_id
                    JOIN contacts c ON ce.contact_id = c.id
                    WHERE c.name IN ({contacts_string})
                )
                SELECT 
                    e.id, e.date, e.summary, e.content,
                    array_agg(json_build_object('name', c.name, 'email', cm.value)) as contacts
                FROM email_ids ei
                JOIN emails e ON e.id = ei.id
                JOIN contact_emails ce ON e.id = ce.email_id
                JOIN contacts c ON ce.contact_id = c.id
                JOIN contact_methods cm ON c.id = cm.contact_id
                WHERE cm.method_type = 'email'
                GROUP BY e.id, e.date, e.summary, e.content
                ORDER BY e.date DESC;
            """
        else:
            query = """
                SELECT 
                    e.id, e.date, e.summary, e.content,
                    array_agg(json_build_object('name', c.name, 'email', cm.value)) as contacts
                FROM emails e
                JOIN contact_emails ce ON e.id = ce.email_id
                JOIN contacts c ON ce.contact_id = c.id
                JOIN contact_methods cm ON c.id = cm.contact_id
                WHERE cm.method_type = 'email'
                GROUP BY e.id, e.date, e.summary, e.content
                ORDER BY e.date DESC;
            """

        self.cur.execute(query)
        for row in self.cur:
            email_record = row[:-1]  # Everything except contacts array
            contacts_data = row[-1]  # Contacts array
            contacts_list = [(c["name"], c["email"]) for c in contacts_data]
            yield (email_record, contacts_list)
