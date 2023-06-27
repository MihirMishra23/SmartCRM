from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship, Session #type:ignore
from sqlalchemy import ForeignKey, Text
from typing import List

Base = declarative_base()

class Contact(Base):
  __tablename__ = 'contacts'
  id:Mapped[int] = mapped_column(primary_key=True)
  # name:Mapped[str] = mapped_column(nullable=False)
  email_address:Mapped[str]
  emails: Mapped[List["Email"]] = relationship(back_populates='From')
  
  def __repr__(self):
    return f"<Name = {self.name}>"

class Email(Base):
  __tablename__ = 'emails'
  id: Mapped[int] = mapped_column(primary_key=True)
  to_contact_id: Mapped[int] = mapped_column(ForeignKey('contacts.id'), nullable=False)
  To: Mapped[str] = mapped_column(Text, nullable=False)
  From: Mapped["Contact"] = relationship(back_populates='emails')
  Date: Mapped[str] = mapped_column(Text, nullable=False)
  Subject: Mapped[str] = mapped_column(Text, nullable=False)
  Contents: Mapped[str] = mapped_column(Text, nullable=False)
  
  def __repr__(self):
    return f"<Email info = {self.Contents}>"