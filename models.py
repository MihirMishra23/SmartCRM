from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship, Session #type:ignore
from sqlalchemy import ForeignKey, Text
from typing import List

Base = declarative_base()

class Contact(Base):
  __tablename__ = 'contacts'
  id:Mapped[int] = mapped_column(primary_key=True)
  name:Mapped[str] = mapped_column(nullable=False)
  email_address:Mapped[str]
  emails: Mapped[List["Email"]] = relationship(back_populates='contact')
  
  def __repr__(self):
    return f"<Name = {self.name}>"

class Email(Base):
  __tablename__ = 'emails'
  id:Mapped[int] = mapped_column(primary_key=True)
  contact_id:Mapped[int] = mapped_column(ForeignKey('contacts.id'), nullable=False)
  text: Mapped[str] = mapped_column(Text, nullable=False)
  contact: Mapped["Contact"] = relationship(back_populates='emails')
  
  def __repr__(self):
    return f"<Email info = {self.text}>"