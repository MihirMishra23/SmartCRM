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
        def verify_contact_count(expected_count, message=""):
            """Helper method to verify the number of contacts and return them"""
            response = requests.get(
                f"{self.BASE_URL}/contacts",
                params={"test_suffix": self.test_suffix}
            )
            contacts = response.json()
            self.assertEqual(
                len(contacts),
                expected_count,
                f"{message} Expected {expected_count} contacts, but found {len(contacts)}. Contacts: {contacts}"
            )
            return contacts

        # 1. Test Contact Creation
        contacts_to_create = [
            # Full contact with all fields
            {
                "name": "Test Contact",
                "contact_methods": [
                    {"type": "email", "value": "test@example.com", "is_primary": True},
                    {"type": "phone", "value": "123-456-7890", "is_primary": False}
                ],
                "company": "Test Corp",
                "position": "Test Engineer",
                "notes": "Test notes",
                "warm": True,
                "reminder": True,
                "last_contacted": date.today().isoformat(),
                "follow_up_date": date.today().isoformat()
            },
            # Second contact with same name but different details
            {
                "name": "Test Contact",
                "contact_methods": [
                    {"type": "email", "value": "another@example.com", "is_primary": True},
                    {"type": "phone", "value": "987-654-3210", "is_primary": False}
                ],
                "company": "Another Corp"
            },
            # Third contact with same name but minimal details
            {
                "name": "Test Contact",
                "contact_methods": [
                    {"type": "email", "value": "third@example.com", "is_primary": True}
                ]
            },
            # Minimal contact
            {
                "name": "Min Contact",
                "contact_methods": [
                    {"type": "email", "value": "min@example.com", "is_primary": True}
                ]
            }
        ]

        # Create all contacts and verify each creation
        for i, contact in enumerate(contacts_to_create):
            response = requests.post(
                f"{self.BASE_URL}/contacts",
                json=contact,
                params={"test_suffix": self.test_suffix}
            )
            self.assertEqual(
                response.status_code,
                201,
                f"Failed to create contact {i + 1}. Status: {response.status_code}, Response: {response.json()}"
            )

        # Verify all contacts were added correctly
        contacts = verify_contact_count(4, "After creating all contacts:")
        test_contacts = [c for c in contacts if c["name"] == "Test Contact"]
        self.assertEqual(
            len(test_contacts),
            3,
            f"Expected 3 'Test Contact' contacts, but found {len(test_contacts)}. Contacts: {contacts}"
        )
        self.assertTrue(
            any(c["name"] == "Min Contact" for c in contacts),
            f"Could not find 'Min Contact' in contacts: {contacts}"
        )

        # 2. Test Duplicate Prevention
        duplicate_method_contact = {
            "name": "Different Contact",
            "contact_methods": [
                {
                    "type": "email",
                    "value": "test@example.com",  # Already used by first contact
                    "is_primary": True
                }
            ]
        }
        response = requests.post(
            f"{self.BASE_URL}/contacts",
            json=duplicate_method_contact,
            params={"test_suffix": self.test_suffix}
        )
        self.assertNotEqual(
            response.status_code,
            201,
            f"Contact creation with duplicate method should have failed but succeeded with status 201"
        )

        # 3. Test Deletion Scenarios
        # Test invalid deletions first
        deletion_tests = [
            # (name, company, contact_info, expected_status)
            ("NonExistentContact", None, None, 404),  # Non-existent contact
            ("Test Contact", None, None, 409)  # Ambiguous name without specifics
        ]

        for name, company, contact_info, expected_status in deletion_tests:
            params = {"test_suffix": self.test_suffix}
            if company:
                params["company"] = company
            if contact_info:
                params["contact_info"] = contact_info

            response = requests.delete(
                f"{self.BASE_URL}/contacts/{name}",
                params=params
            )
            self.assertEqual(
                response.status_code,
                expected_status,
                f"Deletion test for {name} (company: {company}, contact_info: {contact_info}) "
                f"expected status {expected_status} but got {response.status_code}. "
                f"Response: {response.json()}"
            )

        # Delete all contacts systematically
        deletion_order = [
            # (name, company, contact_info)
            ("Test Contact", "Test Corp", None),  # First by company
            ("Test Contact", None, "another@example.com"),  # Second by email
            ("Min Contact", None, "min@example.com"),  # Min contact by email
            ("Test Contact", None, "third@example.com")  # Last by email
        ]

        for name, company, contact_info in deletion_order:
            params = {"test_suffix": self.test_suffix}
            if company:
                params["company"] = company
            if contact_info:
                params["contact_info"] = contact_info

            response = requests.delete(
                f"{self.BASE_URL}/contacts/{name}",
                params=params
            )
            self.assertEqual(
                response.status_code,
                200,
                f"Failed to delete contact {name} with params {params}. "
                f"Status: {response.status_code}, Response: {response.json()}"
            )
            
        # Verify all contacts were deleted
        verify_contact_count(0, "After all deletions:")

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

        # Test error case 1: Creating email for non-existent contact
        nonexistent_email = {
            "contacts": ["Non Existent Contact"],
            "date": date.today().isoformat(),
            "content": "This should fail"
        }
        response = requests.post(
            f"{self.BASE_URL}/emails",
            json=nonexistent_email,
            params={"test_suffix": self.test_suffix}
        )
        self.assertEqual(
            response.status_code,
            404,
            f"Email creation with non-existent contact should have failed with 404 but got {response.status_code}. Response: {response.json()}"
        )

        # Test error case 2: Invalid date format
        invalid_date_email = {
            "contacts": ["Email Test Contact"],
            "date": "2024/03/15",  # Wrong format, should be ISO format
            "content": "This should fail"
        }
        response = requests.post(
            f"{self.BASE_URL}/emails",
            json=invalid_date_email,
            params={"test_suffix": self.test_suffix}
        )
        self.assertEqual(
            response.status_code,
            400,
            f"Email creation with invalid date format should have failed with 400 but got {response.status_code}. Response: {response.json()}"
        )

        # Test error case 3: Missing required fields
        missing_fields_cases = [
            {"date": date.today().isoformat(), "content": "Missing contacts"},  # Missing contacts
            {"contacts": ["Email Test Contact"], "content": "Missing date"},    # Missing date
            {"contacts": ["Email Test Contact"], "date": date.today().isoformat()}  # Missing content
        ]
        for i, invalid_email in enumerate(missing_fields_cases):
            response = requests.post(
                f"{self.BASE_URL}/emails",
                json=invalid_email,
                params={"test_suffix": self.test_suffix}
            )
            self.assertEqual(
                response.status_code,
                400,
                f"Case {i}: Email creation with missing fields should have failed with 400 but got {response.status_code}. "
                f"Email: {invalid_email}, Response: {response.json()}"
            )

        # Cleanup: Delete all created emails and contacts
        # 1. Get all emails for the test contact
        response = requests.get(
            f"{self.BASE_URL}/emails",
            params={
                "contacts": ["Email Test Contact"],
                "test_suffix": self.test_suffix
            }
        )
        self.assertEqual(response.status_code, 200, "Failed to get emails for cleanup")
        emails = response.json()
        
        # 2. Delete the test contact (this should cascade delete the contact_emails relationships)
        response = requests.delete(
            f"{self.BASE_URL}/contacts/Email Test Contact",
            params={
                "contact_info": "email_test@example.com",
                "test_suffix": self.test_suffix
            }
        )
        self.assertEqual(
            response.status_code,
            200,
            f"Failed to delete test contact during cleanup. Status: {response.status_code}, Response: {response.json()}"
        )

        # 3. Verify cleanup was successful
        response = requests.get(
            f"{self.BASE_URL}/emails",
            params={
                "contacts": ["Email Test Contact"],
                "test_suffix": self.test_suffix
            }
        )
        self.assertEqual(response.status_code, 200, "Failed to verify email cleanup")
        remaining_emails = response.json()
        self.assertEqual(
            len(remaining_emails),
            0,
            f"Expected 0 emails after cleanup, but found {len(remaining_emails)}"
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
