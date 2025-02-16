from .base import db
from sqlalchemy.orm import relationship


class Email(db.Model):
    __tablename__ = "emails"

    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.Text, nullable=False)
    date = db.Column(db.Date, nullable=False)
    summary = db.Column(db.Text)
    content = db.Column(db.Text, nullable=False)

    # Relationship
    contacts = relationship(
        "Contact", secondary="contact_emails", back_populates="emails"
    )

    def __repr__(self):
        return f"<Email {self.id} from {self.date}>"
