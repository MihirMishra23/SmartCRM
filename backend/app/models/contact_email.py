from .base import db


class ContactEmail(db.Model):
    __tablename__ = "contact_emails"

    contact_id = db.Column(
        db.Integer, db.ForeignKey("contacts.id", ondelete="CASCADE"), primary_key=True
    )
    email_id = db.Column(db.Integer, db.ForeignKey("emails.id"), primary_key=True)
