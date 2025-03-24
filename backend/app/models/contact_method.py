from .base import db
from sqlalchemy.orm import relationship
from sqlalchemy import Index, UniqueConstraint


class ContactMethod(db.Model):
    __tablename__ = "contact_methods"

    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey("contacts.id"), nullable=False)
    method_type = db.Column(db.Text, nullable=False)
    value = db.Column(db.Text, nullable=False, unique=True)
    is_primary = db.Column(db.Boolean, server_default="false")

    # Relationship
    contact = relationship("Contact", back_populates="contact_methods")

    # Constraints and Indexes
    __table_args__ = (Index("idx_contact_methods_value", "value"),)

    def __repr__(self):
        return f"<ContactMethod {self.method_type}: {self.value}>"
