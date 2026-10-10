from sqlalchemy.orm import Session
from reachai.repositories.company_repo import CompanyRepository, ContactRepository


class CompanyService:
    def __init__(self, session: Session):
        self.company_repo = CompanyRepository(session)


class ContactService:
    def __init__(self, session: Session):
        self.contact_repo = ContactRepository(session)
