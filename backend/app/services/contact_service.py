from datetime import datetime
from typing import List, Optional
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_

from ..models.base import db
from ..models.contact import Contact
from ..models.contact_method import ContactMethod


class ContactService:
    @staticmethod
    def get_contacts(
        name: Optional[str] = None,
        email: Optional[str] = None,
        company: Optional[str] = None,
    ) -> List[Contact]:
        """Get contacts with optional filtering"""
        query = Contact.query

        if name:
            query = query.filter(Contact.name.ilike(f"%{name}%"))
        if company:
            query = query.filter(Contact.company.ilike(f"%{company}%"))
        if email:
            query = query.join(Contact.contact_methods).filter(
                ContactMethod.method_type == "email",
                ContactMethod.value.ilike(f"%{email}%"),
            )

        return query.all()

    @staticmethod
    def get_contact_by_email(email: str) -> Optional[Contact]:
        """Get a contact by their email address"""
        return (
            Contact.query.join(Contact.contact_methods)
            .filter(ContactMethod.method_type == "email", ContactMethod.value == email)
            .first()
        )

    @staticmethod
    def delete_contact_by_email(email: str) -> bool:
        """Delete a contact by their email address"""
        contact = ContactService.get_contact_by_email(email)
        if not contact:
            return False

        try:
            ContactMethod.query.filter_by(contact_id=contact.id).delete()
            db.session.delete(contact)
            db.session.commit()
            return True
        except SQLAlchemyError:
            db.session.rollback()
            raise

    @staticmethod
    def create_contact(contact_data: dict) -> Contact:
        """Create a new contact"""
        # First check if any of the contact methods already exist
        if "contact_methods" in contact_data:
            for method in contact_data["contact_methods"]:
                existing_method = ContactMethod.query.filter_by(
                    method_type=method["type"], value=method["value"]
                ).first()
                if existing_method:
                    raise ValueError(
                        f"Contact method {method['type']}:{method['value']} is already associated with another contact"
                    )

        contact = Contact()
        contact.name = contact_data["name"]
        contact.company = contact_data.get("company")
        contact.position = contact_data.get("position")
        contact.last_contacted = (
            datetime.fromisoformat(contact_data["last_contacted"]).date()
            if contact_data.get("last_contacted")
            else None
        )
        contact.follow_up_date = (
            datetime.fromisoformat(contact_data["follow_up_date"]).date()
            if contact_data.get("follow_up_date")
            else None
        )
        contact.warm = contact_data.get("warm", False)
        contact.reminder = contact_data.get("reminder", True)
        contact.notes = contact_data.get("notes")

        # Add contact methods
        for method in contact_data.get("contact_methods", []):
            contact_method = ContactMethod()
            contact_method.method_type = method["type"]
            contact_method.value = method["value"]
            contact_method.is_primary = method.get("is_primary", False)
            contact.contact_methods.append(contact_method)

        try:
            db.session.add(contact)
            db.session.commit()
            return contact
        except SQLAlchemyError:
            db.session.rollback()
            raise

    @staticmethod
    def format_contact_response(contact: Contact) -> dict:
        """Format a contact object into API response format"""
        email_methods = [
            cm for cm in contact.contact_methods if cm.method_type == "email"
        ]
        primary_email = next((cm.value for cm in email_methods if cm.is_primary), None)
        if not primary_email and email_methods:
            primary_email = email_methods[0].value

        return {
            "name": contact.name,
            "email": primary_email,  # Use primary email as identifier
            "company": contact.company,
            "position": contact.position,
            "last_contacted": (
                contact.last_contacted.isoformat() if contact.last_contacted else None
            ),
            "follow_up_date": (
                contact.follow_up_date.isoformat() if contact.follow_up_date else None
            ),
            "warm": contact.warm,
            "reminder": contact.reminder,
            "notes": contact.notes,
            "contact_methods": [
                {
                    "type": cm.method_type,
                    "value": cm.value,
                    "is_primary": cm.is_primary,
                }
                for cm in contact.contact_methods
            ],
        }
