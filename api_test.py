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

    def setUp(self):
        """Set up test database for each test"""
        # Create database connection
        self.conn = psycopg2.connect(f"dbname={self.DB_NAME}")
        self.conn.autocommit = True  # Needed for creating/dropping tables
        self.cur = self.conn.cursor()

        # Generate unique suffix for test tables
        self.test_suffix = f"_test_{uuid.uuid4().hex[:8]}"

        # Clone the tables with test suffix
        self._clone_tables()

    def tearDown(self):
        """Clean up test database after each test"""
        self._drop_test_tables()
        self.cur.close()
        self.conn.close()

    def _clone_tables(self):
        """Clone the necessary tables for testing by copying schema from existing tables"""
        # Get tables in correct order based on dependencies
        tables = ["contacts", "contact_methods", "emails", "contact_emails"]
        
        for table in tables:
            test_table = f"{table}{self.test_suffix}"
            
            # Drop test table if it exists
            self.cur.execute(f"DROP TABLE IF EXISTS {test_table} CASCADE")
            
            # Create new table with same schema, constraints, indexes, and triggers
            # But don't copy the data
            self.cur.execute(f"""
                CREATE TABLE {test_table} 
                (LIKE {table} INCLUDING ALL)
            """)
            
            # Get and recreate foreign key constraints
            self.cur.execute("""
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
            
            for fk in self.cur.fetchall():
                # Recreate each foreign key with the test suffix
                self.cur.execute(f"""
                    ALTER TABLE {test_table}
                    ADD CONSTRAINT {fk[0]}{self.test_suffix}
                    FOREIGN KEY ({fk[2]})
                    REFERENCES {fk[3]}{self.test_suffix}({fk[4]})
                """)
            
            # Get and recreate sequences if they exist
            self.cur.execute("""
                SELECT column_name, column_default
                FROM information_schema.columns
                WHERE table_name = %s
                AND column_default LIKE 'nextval%%'
            """, (table,))
            
            for col in self.cur.fetchall():
                # Extract sequence name from default value
                sequence_name = col[1].split("'")[1].split("'")[0]
                # Create new sequence for test table
                test_sequence = f"{sequence_name}{self.test_suffix}"
                self.cur.execute(f"CREATE SEQUENCE IF NOT EXISTS {test_sequence}")
                # Update column default
                self.cur.execute(f"""
                    ALTER TABLE {test_table}
                    ALTER COLUMN {col[0]} SET DEFAULT nextval('{test_sequence}'::regclass)
                """)

    def _drop_test_tables(self):
        """Drop all test tables and their sequences"""
        # Drop tables in reverse order due to dependencies
        tables = ["contact_emails", "contact_methods", "emails", "contacts"]
        for table in tables:
            test_table = f"{table}{self.test_suffix}"
            self.cur.execute(f"DROP TABLE IF EXISTS {test_table} CASCADE")
            
            # Drop associated sequences
            self.cur.execute("""
                SELECT column_default
                FROM information_schema.columns
                WHERE table_name = %s
                AND column_default LIKE 'nextval%%'
            """, (table,))
            
            for col in self.cur.fetchall():
                sequence_name = col[0].split("'")[1].split("'")[0]
                test_sequence = f"{sequence_name}{self.test_suffix}"
                self.cur.execute(f"DROP SEQUENCE IF EXISTS {test_sequence}")

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
            "contacts": ["email_test@example.com"],
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
            "contacts": ["email_test@example.com"],
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
                "contacts": ["email_test@example.com"],
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
            "contacts": ["nonexistent@example.com"],
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
            "contacts": ["email_test@example.com"],
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
            {"contacts": ["email_test@example.com"], "content": "Missing date"},    # Missing date
            {"contacts": ["email_test@example.com"], "date": date.today().isoformat()}  # Missing content
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
                "contacts": ["email_test@example.com"],
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
                "contacts": ["email_test@example.com"],
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
        """Test edge cases and error handling for contacts and emails API"""
        
        # Track created test data for cleanup
        test_contacts = []  # List of (name, email, company) tuples
        
        # 1. Contact Creation Edge Cases
        invalid_contact_cases = [
            # Missing required fields
            (
                {"contact_methods": [{"type": "email", "value": "test@example.com", "is_primary": True}]},
                "Missing required field: name"
            ),
            (
                {"name": "Test Contact"},
                "Missing required field: contact_methods"
            ),
            # Invalid field types
            (
                {
                    "name": 123,  # Invalid name type
                    "contact_methods": [{"type": "email", "value": "test@example.com", "is_primary": True}]
                },
                "Name must be a non-empty string"
            ),
            (
                {
                    "name": "Test Contact",
                    "contact_methods": "not a list"  # Invalid contact_methods type
                },
                "contact_methods must be an array"
            ),
            # Empty or invalid values
            (
                {
                    "name": "",  # Empty name
                    "contact_methods": [{"type": "email", "value": "test@example.com", "is_primary": True}]
                },
                "Name must be a non-empty string"
            ),
            (
                {
                    "name": "Test Contact",
                    "contact_methods": []  # Empty contact_methods
                },
                "At least one contact method is required"
            ),
            # Invalid contact method structure
            (
                {
                    "name": "Test Contact",
                    "contact_methods": [{"type": "email"}]  # Missing value
                },
                "Contact method at index 0 missing required field: value"
            ),
            (
                {
                    "name": "Test Contact",
                    "contact_methods": [{"value": "test@example.com"}]  # Missing type
                },
                "Contact method at index 0 missing required field: type"
            ),
            (
                {
                    "name": "Test Contact",
                    "contact_methods": [
                        {"type": "email", "value": "test@example.com", "is_primary": "not a boolean"}
                    ]
                },
                "Contact method at index 0 field 'is_primary' must be a boolean"
            ),
            # Invalid date formats
            (
                {
                    "name": "Test Contact",
                    "contact_methods": [{"type": "email", "value": "test@example.com", "is_primary": True}],
                    "last_contacted": "2024/03/15"  # Wrong date format
                },
                "invalid input syntax for type date"
            ),
            # Special characters and extremely long values
            (
                {
                    "name": "Test Contact" + "a" * 1000,  # Extremely long name
                    "contact_methods": [{"type": "email", "value": "test@example.com", "is_primary": True}]
                },
                "value too long"
            ),
        ]

        for i, (invalid_contact, expected_error) in enumerate(invalid_contact_cases):
            response = requests.post(
                f"{self.BASE_URL}/contacts",
                json=invalid_contact,
                params={"test_suffix": self.test_suffix}
            )
            self.assertNotEqual(
                response.status_code,
                201,
                f"Case {i}: Invalid contact creation should have failed but succeeded: {invalid_contact}"
            )
            self.assertIn(
                expected_error,
                response.json().get("error", ""),
                f"Case {i}: Expected error '{expected_error}' not found in response: {response.json()}"
            )

        # 2. Contact Method Validation
        # Create valid contact for duplicate testing
        valid_contact = {
            "name": "Test Contact",
            "contact_methods": [
                {"type": "email", "value": "test@example.com", "is_primary": True},
                {"type": "phone", "value": "123-456-7890", "is_primary": False}
            ],
            "company": "Test Corp"
        }
        response = requests.post(
            f"{self.BASE_URL}/contacts",
            json=valid_contact,
            params={"test_suffix": self.test_suffix}
        )
        self.assertEqual(response.status_code, 201)
        test_contacts.append(("Test Contact", "test@example.com", "Test Corp"))

        # Create another contact with same name for ambiguous deletion test
        another_contact = {
            "name": "Test Contact",
            "contact_methods": [
                {"type": "email", "value": "another@example.com", "is_primary": True}
            ],
            "company": "Another Corp"
        }
        response = requests.post(
            f"{self.BASE_URL}/contacts",
            json=another_contact,
            params={"test_suffix": self.test_suffix}
        )
        self.assertEqual(response.status_code, 201)
        test_contacts.append(("Test Contact", "another@example.com", "Another Corp"))

        # Test duplicate contact methods
        duplicate_cases = [
            # Same email, different contact
            {
                "name": "Another Contact",
                "contact_methods": [
                    {"type": "email", "value": "test@example.com", "is_primary": True}
                ]
            },
            # Same phone, different contact
            {
                "name": "Another Contact",
                "contact_methods": [
                    {"type": "phone", "value": "123-456-7890", "is_primary": True}
                ]
            }
        ]

        for duplicate_contact in duplicate_cases:
            response = requests.post(
                f"{self.BASE_URL}/contacts",
                json=duplicate_contact,
                params={"test_suffix": self.test_suffix}
            )
            self.assertEqual(
                response.status_code,
                400,
                f"Duplicate contact method should have failed: {duplicate_contact}"
            )
            self.assertIn(
                "already used by contact",
                response.json().get("error", ""),
                f"Expected duplicate error not found in response: {response.json()}"
            )

        # 3. Contact Deletion Edge Cases
        deletion_test_cases = [
            # Non-existent contact
            (
                "NonExistent",
                None,
                None,
                404,
                "Contact not found"
            ),
            # Ambiguous deletion (multiple contacts with same name)
            (
                "Test Contact",
                None,
                None,
                409,
                "Multiple contacts found"
            ),
            # Non-existent company
            (
                "Test Contact",
                None,
                "NonExistentCompany",
                404,
                "Contact not found"
            ),
            # Non-existent contact info
            (
                "Test Contact",
                "nonexistent@example.com",
                None,
                404,
                "Contact not found"
            )
        ]

        for name, contact_info, company, expected_status, expected_error in deletion_test_cases:
            params = {"test_suffix": self.test_suffix}
            if contact_info:
                params["contact_info"] = contact_info
            if company:
                params["company"] = company

            response = requests.delete(
                f"{self.BASE_URL}/contacts/{name}",
                params=params
            )
            self.assertEqual(
                response.status_code,
                expected_status,
                f"Deletion of {name} (contact_info: {contact_info}, company: {company}) "
                f"returned {response.status_code} instead of {expected_status}"
            )
            self.assertIn(
                expected_error,
                response.json().get("error", ""),
                f"Expected error '{expected_error}' not found in response: {response.json()}"
            )

        # 4. Email Creation Edge Cases
        email_test_cases = [
            # Missing required fields
            (
                {"date": date.today().isoformat(), "content": "Test content"},
                "contacts field is required"
            ),
            (
                {"contacts": ["Test Contact"], "content": "Test content"},
                "date field is required"
            ),
            (
                {"contacts": ["Test Contact"], "date": date.today().isoformat()},
                "content field is required"
            ),
            # Invalid contact
            (
                {
                    "contacts": ["NonExistentContact"],
                    "date": date.today().isoformat(),
                    "content": "Test content"
                },
                "Contact not found"
            ),
            # Invalid date format
            (
                {
                    "contacts": ["Test Contact"],
                    "date": "2024/03/15",
                    "content": "Test content"
                },
                "invalid input syntax for type date"
            ),
            # Empty content
            (
                {
                    "contacts": ["Test Contact"],
                    "date": date.today().isoformat(),
                    "content": ""
                },
                "content cannot be empty"
            )
        ]

        for i, (invalid_email, expected_error) in enumerate(email_test_cases):
            response = requests.post(
                f"{self.BASE_URL}/emails",
                json=invalid_email,
                params={"test_suffix": self.test_suffix}
            )
            self.assertNotEqual(
                response.status_code,
                201,
                f"Case {i}: Invalid email creation should have failed but succeeded: {invalid_email}"
            )
            self.assertIn(
                expected_error,
                response.json().get("error", "").lower(),
                f"Case {i}: Expected error '{expected_error}' not found in response: {response.json()}"
            )

        # Cleanup phase
        try:
            # 1. Delete test contacts in reverse order (to handle dependencies)
            for name, email, company in reversed(test_contacts):
                response = requests.delete(
                    f"{self.BASE_URL}/contacts/{name}",
                    params={
                        "contact_info": email,
                        "company": company,
                        "test_suffix": self.test_suffix
                    }
                )
                # Accept both 200 (successful delete) and 404 (already deleted)
                self.assertIn(
                    response.status_code,
                    [200, 404],
                    f"Failed to delete contact {name} during cleanup. "
                    f"Status: {response.status_code}, Response: {response.json()}"
                )

            # 2. Verify all test contacts were deleted
            for name, email, company in test_contacts:
                response = requests.get(
                    f"{self.BASE_URL}/contacts",
                    params={
                        "test_suffix": self.test_suffix,
                        "contact_info": email
                    }
                )
                self.assertEqual(
                    response.status_code,
                    200,
                    f"Failed to verify contact {name} cleanup"
                )
                contacts = response.json()
                matching_contacts = [
                    c for c in contacts 
                    if c["name"] == name 
                    and any(m["value"] == email for m in c["contact_methods"])
                ]
                self.assertEqual(
                    len(matching_contacts),
                    0,
                    f"Contact {name} with email {email} still exists after cleanup"
                )

        except Exception as e:
            # Log cleanup failure but don't fail the test
            print(f"Warning: Cleanup failed: {str(e)}")
            # Re-raise if this is a test assertion
            if isinstance(e, AssertionError):
                raise


if __name__ == "__main__":
    unittest.main(verbosity=2)
