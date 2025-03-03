from .base import db
from sqlalchemy.orm import relationship
from .contact_email import ContactEmail


class Email(db.Model):
    __tablename__ = "emails"

    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.Text, nullable=True)
    date = db.Column(db.Date, nullable=False)
    summary = db.Column(db.Text)
    content = db.Column(db.Text, nullable=False)
    sender_id = db.Column(
        db.Integer, db.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    sender = relationship(
        "Contact", foreign_keys=[sender_id], back_populates="sent_emails"
    )
    contacts = relationship(
        "Contact", secondary="contact_emails", back_populates="emails"
    )

    @property
    def receivers(self):
        """Get all contacts who received this email (excluding the sender)."""
        return [contact for contact in self.contacts if contact.id != self.sender_id]

    def __repr__(self):
        return f"<Email {self.id} from {self.date}>"
