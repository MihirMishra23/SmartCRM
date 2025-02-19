from datetime import datetime
from .base import db
from sqlalchemy.orm import relationship
from .contact_email import ContactEmail


class Contact(db.Model):
    __tablename__ = "contacts"

    # Match exact column order from PostgreSQL
    name = db.Column(db.Text, nullable=False)
    company = db.Column(db.Text)
    last_contacted = db.Column(db.Date)
    follow_up_date = db.Column(db.Date)
    warm = db.Column(db.Boolean)
    notes = db.Column(db.Text)
    id = db.Column(db.Integer, primary_key=True)
    reminder = db.Column(db.Boolean, server_default="true")
    position = db.Column(db.Text)

    # Relationships
    contact_methods = relationship(
        "ContactMethod", back_populates="contact", cascade="all, delete-orphan"
    )
    emails = relationship(
        "Email", secondary="contact_emails", back_populates="contacts"
    )
    sent_emails = relationship(
        "Email", back_populates="sender", foreign_keys="Email.sender_id"
    )

    @property
    def email_addresses(self):
        """Get all email addresses associated with this contact."""
        return [cm.value for cm in self.contact_methods if cm.method_type == "email"]

    @property
    def primary_email(self):
        """Get the primary email address for this contact."""
        primary = next(
            (
                cm.value
                for cm in self.contact_methods
                if cm.method_type == "email" and cm.is_primary
            ),
            None,
        )
        if primary is None and self.email_addresses:
            return self.email_addresses[0]
        return primary

    @property
    def received_emails(self):
        """Get all emails received by this contact."""
        return [email for email in self.emails if email.sender_id != self.id]

    def __repr__(self):
        return f"<Contact {self.name}>"
