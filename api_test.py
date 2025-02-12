import unittest
import requests
import json
from datetime import datetime, date
from typing import Dict, Any, List
import psycopg2
import uuid


class TestFlaskAPI(unittest.TestCase):
    BASE_URL = "http://localhost:5001"
    DB_NAME = "postgres"

    @classmethod
    def setUpClass(cls):
        """Set up test environment and verify API is running"""
        try:
            # Check if API is running
            response = requests.get(f"{cls.BASE_URL}/health")
            if response.status_code != 200:
                raise Exception("API is not healthy")
        except requests.exceptions.ConnectionError:
            raise Exception("API is not running. Please start it with 'python api.py'")

        # Create database connection for test setup
        cls.conn = psycopg2.connect(f"dbname={cls.DB_NAME}")
        cls.conn.autocommit = True  # Needed for creating/dropping tables
        cls.cur = cls.conn.cursor()

        # Generate unique suffix for test tables
        cls.test_suffix = f"_test_{uuid.uuid4().hex[:8]}"

        # Clone the tables with test suffix
        cls._clone_tables()

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        cls._drop_test_tables()
        cls.cur.close()
        cls.conn.close()

    @classmethod
    def _clone_tables(cls):
        """Clone the necessary tables for testing by copying schema from existing tables"""
        # Get tables in correct order based on dependencies
        tables = ["contacts", "contact_methods", "emails", "contact_emails"]
        
        for table in tables:
            test_table = f"{table}{cls.test_suffix}"
            
            # Drop test table if it exists
            cls.cur.execute(f"DROP TABLE IF EXISTS {test_table} CASCADE")
            
            # Create new table with same schema, constraints, indexes, and triggers
            # But don't copy the data
            cls.cur.execute(f"""
                CREATE TABLE {test_table} 
                (LIKE {table} INCLUDING ALL)
            """)
            
            # Get and recreate foreign key constraints
            cls.cur.execute("""
                SELECT
                    tc.constraint_name,
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM
                    information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = %s
            """, (table,))
            
            for fk in cls.cur.fetchall():
                # Recreate each foreign key with the test suffix
                cls.cur.execute(f"""
                    ALTER TABLE {test_table}
                    ADD CONSTRAINT {fk[0]}{cls.test_suffix}
                    FOREIGN KEY ({fk[2]})
                    REFERENCES {fk[3]}{cls.test_suffix}({fk[4]})
                """)
            
            # Get and recreate sequences if they exist
            cls.cur.execute("""
                SELECT column_name, column_default
                FROM information_schema.columns
                WHERE table_name = %s
                AND column_default LIKE 'nextval%%'
            """, (table,))
            
            for col in cls.cur.fetchall():
                # Extract sequence name from default value
                sequence_name = col[1].split("'")[1].split("'")[0]
                # Create new sequence for test table
                test_sequence = f"{sequence_name}{cls.test_suffix}"
                cls.cur.execute(f"CREATE SEQUENCE IF NOT EXISTS {test_sequence}")
                # Update column default
                cls.cur.execute(f"""
                    ALTER TABLE {test_table}
                    ALTER COLUMN {col[0]} SET DEFAULT nextval('{test_sequence}'::regclass)
                """)

    @classmethod
    def _drop_test_tables(cls):
        """Drop all test tables and their sequences"""
        # Drop tables in reverse order due to dependencies
        tables = ["contact_emails", "contact_methods", "emails", "contacts"]
        for table in tables:
            test_table = f"{table}{cls.test_suffix}"
            cls.cur.execute(f"DROP TABLE IF EXISTS {test_table} CASCADE")
            
            # Drop associated sequences
            cls.cur.execute("""
                SELECT column_default
                FROM information_schema.columns
                WHERE table_name = %s
                AND column_default LIKE 'nextval%%'
            """, (table,))
            
            for col in cls.cur.fetchall():
                sequence_name = col[0].split("'")[1].split("'")[0]
                test_sequence = f"{sequence_name}{cls.test_suffix}"
                cls.cur.execute(f"DROP SEQUENCE IF EXISTS {test_sequence}")

    def setUp(self):
        """Store initial database state"""
        self.initial_state = self._get_db_state()

    def tearDown(self):
        """Verify database state matches initial state"""
        final_state = self._get_db_state()
        self.assertEqual(
            self.initial_state, final_state, "Database state changed during test"
        )

    def _get_db_state(self) -> Dict[str, List[tuple]]:
        """Get current state of all test tables"""
        tables = ["contacts", "contact_methods", "contact_emails", "emails"]
        state = {}
        
        # Define ordering for each table based on its structure
        order_by = {
            "contacts": "id",
            "contact_methods": "id",
            "emails": "id",
            "contact_emails": "contact_id, email_id"  # Composite primary key
        }
        
        for table in tables:
            test_table = f"{table}{self.test_suffix}"
            self.cur.execute(f"SELECT * FROM {test_table} ORDER BY {order_by[table]}")
            state[table] = self.cur.fetchall()
        return state

    def test_health_endpoint(self):
        """Test the health check endpoint"""
        response = requests.get(f"{self.BASE_URL}/health")
        self.assertEqual(
            response.status_code, 
            200, 
            f"Health check failed with status {response.status_code}"
        )
        self.assertEqual(
            response.json(), 
            {"status": "healthy"}, 
            f"Unexpected health check response: {response.json()}"
        )

    def test_contacts_crud(self):
        """Test contact creation, retrieval, and validation"""
        # Test creating a valid contact with all fields
        new_contact = {
            "name": "Test Contact",  # Required
            "contact_methods": [  # At least one method required
                {
                    "type": "email",
                    "value": "test@example.com",
                    "is_primary": True
                },
                {
                    "type": "phone",
                    "value": "123-456-7890",
                    "is_primary": False
                }
            ],
            "company": "Test Corp",
            "position": "Test Engineer",
            "notes": "Test notes",
            "warm": True,
            "reminder": True,
            "last_contacted": date.today().isoformat(),
            "follow_up_date": date.today().isoformat()
        }
        response = requests.post(
            f"{self.BASE_URL}/contacts",
            json=new_contact,
            params={"test_suffix": self.test_suffix}
        )
        self.assertEqual(
            response.status_code, 
            201, 
            f"Failed to create contact with all fields. Status: {response.status_code}, Response: {response.json()}"
        )

        # Test creating contact with minimum required fields
        min_contact = {
            "name": "Min Contact",
            "contact_methods": [
                {
                    "type": "email",
                    "value": "min@example.com",
                    "is_primary": True
                }
            ]
        }
        response = requests.post(
            f"{self.BASE_URL}/contacts",
            json=min_contact,
            params={"test_suffix": self.test_suffix}
        )
        self.assertEqual(
            response.status_code, 
            201, 
            f"Failed to create contact with minimum fields. Status: {response.status_code}, Response: {response.json()}"
        )

        # Verify contacts were added
        response = requests.get(
            f"{self.BASE_URL}/contacts",
            params={"test_suffix": self.test_suffix}
        )
        contacts = response.json()
        self.assertEqual(
            len(contacts), 
            2, 
            f"Expected 2 contacts, but found {len(contacts)}. Contacts: {contacts}"
        )
        self.assertTrue(
            any(c["name"] == "Test Contact" for c in contacts),
            f"Could not find 'Test Contact' in contacts: {contacts}"
        )
        self.assertTrue(
            any(c["name"] == "Min Contact" for c in contacts),
            f"Could not find 'Min Contact' in contacts: {contacts}"
        )

        # Test duplicate contact method value (should fail)
        duplicate_contact = {
            "name": "Duplicate Contact",
            "contact_methods": [
                {
                    "type": "email",
                    "value": "test@example.com",  # Already used
                    "is_primary": True
                }
            ]
        }
        response = requests.post(
            f"{self.BASE_URL}/contacts",
            json=duplicate_contact,
            params={"test_suffix": self.test_suffix}
        )
        self.assertNotEqual(
            response.status_code, 
            201, 
            f"Duplicate contact creation should have failed but succeeded with status 201"
        )

    def test_emails_crud(self):
        """Test email creation, retrieval, and filtering"""
        # First create a test contact
        test_contact = {
            "name": "Email Test Contact",
            "contact_methods": [
                {
                    "type": "email",
                    "value": "email_test@example.com",
                    "is_primary": True
                }
            ]
        }
        response = requests.post(
            f"{self.BASE_URL}/contacts",
            json=test_contact,
            params={"test_suffix": self.test_suffix}
        )
        self.assertEqual(
            response.status_code, 
            201, 
            f"Failed to create test contact. Status: {response.status_code}, Response: {response.json()}"
        )

        # Test creating an email with all fields
        new_email = {
            "contacts": ["Email Test Contact"],
            "date": date.today().isoformat(),
            "content": "Test email content",
            "summary": "Test summary"
        }
        response = requests.post(
            f"{self.BASE_URL}/emails",
            json=new_email,
            params={"test_suffix": self.test_suffix}
        )
        self.assertEqual(
            response.status_code, 
            201, 
            f"Failed to create email with all fields. Status: {response.status_code}, Response: {response.json()}"
        )

        # Test creating an email with minimum fields
        min_email = {
            "contacts": ["Email Test Contact"],
            "date": date.today().isoformat(),
            "content": "Minimal email content"
        }
        response = requests.post(
            f"{self.BASE_URL}/emails",
            json=min_email,
            params={"test_suffix": self.test_suffix}
        )
        self.assertEqual(
            response.status_code, 
            201, 
            f"Failed to create email with minimum fields. Status: {response.status_code}, Response: {response.json()}"
        )

        # Test retrieving emails for specific contact
        response = requests.get(
            f"{self.BASE_URL}/emails",
            params={
                "contacts": ["Email Test Contact"],
                "test_suffix": self.test_suffix
            }
        )
        self.assertEqual(
            response.status_code, 
            200, 
            f"Failed to retrieve emails. Status: {response.status_code}, Response: {response.json()}"
        )
        emails = response.json()
        self.assertEqual(
            len(emails), 
            2, 
            f"Expected 2 emails, but found {len(emails)}. Emails: {emails}"
        )
        self.assertTrue(
            any("Test email content" in email["content"] for email in emails),
            f"Could not find 'Test email content' in emails: {emails}"
        )
        self.assertTrue(
            any("Minimal email content" in email["content"] for email in emails),
            f"Could not find 'Minimal email content' in emails: {emails}"
        )

    def test_edge_cases(self):
        """Test edge cases and error handling"""
        # Test missing required fields
        invalid_cases = [
            # Missing name
            {
                "contact_methods": [
                    {"type": "email", "value": "test@example.com", "is_primary": True}
                ]
            },
            # Missing contact_methods
            {
                "name": "Invalid Contact"
            },
            # Empty contact_methods
            {
                "name": "Invalid Contact",
                "contact_methods": []
            }
        ]
        for i, invalid_contact in enumerate(invalid_cases):
            response = requests.post(
                f"{self.BASE_URL}/contacts",
                json=invalid_contact,
                params={"test_suffix": self.test_suffix}
            )
            self.assertEqual(
                response.status_code, 
                400, 
                f"Case {i}: Invalid contact creation should have failed with 400 but got {response.status_code}. "
                f"Contact: {invalid_contact}, Response: {response.json()}"
            )

        # Test malformed JSON
        response = requests.post(
            f"{self.BASE_URL}/contacts",
            data="invalid json",
            headers={"Content-Type": "application/json"},
            params={"test_suffix": self.test_suffix}
        )
        self.assertEqual(
            response.status_code, 
            400, 
            f"Malformed JSON should have failed with 400 but got {response.status_code}"
        )

        # Test email with non-existent contact
        email = {
            "contacts": ["Non Existent Contact"],
            "date": date.today().isoformat(),
            "content": "Test content"
        }
        response = requests.post(
            f"{self.BASE_URL}/emails",
            json=email,
            params={"test_suffix": self.test_suffix}
        )
        self.assertNotEqual(
            response.status_code, 
            201, 
            f"Email creation with non-existent contact should have failed but succeeded with status 201"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
