from datetime import datetime
from .base import db
from sqlalchemy.orm import relationship


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

    def __repr__(self):
        return f"<Contact {self.name}>"
