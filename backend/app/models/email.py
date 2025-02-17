from .base import db
from sqlalchemy.orm import relationship


class Email(db.Model):
    __tablename__ = "emails"

    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.Text, nullable=False)
    date = db.Column(db.Date, nullable=False)
    summary = db.Column(db.Text)
    content = db.Column(db.Text, nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("contacts.id"), nullable=False)

    # Relationships
    sender = relationship(
        "Contact", foreign_keys=[sender_id], back_populates="sent_emails"
    )
    receivers = relationship(
        "Contact", secondary="email_receivers", back_populates="received_emails"
    )

    def __repr__(self):
        return f"<Email {self.id} from {self.date}>"
