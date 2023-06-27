from sqlalchemy import create_engine, text
from models import Base, Contact, Email
from sqlalchemy.orm import Session

engine = create_engine("sqlite:///sample.db", echo=True)

engine.connect()
  
Base.metadata.create_all(bind=engine)

session = Session(bind=engine)

contact1 = Contact(
    name="Mihir",
    email_address="Mihir@address.com",
    emails = [
      Email(text="Testing123"),
    ]
  )

session.add_all([contact1])

session.commit()