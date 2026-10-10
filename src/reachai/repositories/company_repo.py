from sqlalchemy.orm import Session
from sqlalchemy import func
from reachai.models.database import (
    Company, Contact, ContactEmail, ContactPhone, ContactSource,
    Opportunity, OutreachEvent, Referral
)
from typing import Optional, List
import unicodedata


def normalize_name(name: str) -> str:
    return unicodedata.normalize("NFKD", name).lower().strip().replace(" ", "_")


class CompanyRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_normalized_name(self, normalized_name: str) -> Optional[Company]:
        return self.session.query(Company).filter_by(normalized_name=normalized_name).first()

    def get_by_id(self, company_id: int) -> Optional[Company]:
        return self.session.query(Company).filter_by(id=company_id).first()

    def get_by_name(self, name: str) -> Optional[Company]:
        norm = normalize_name(name)
        return self.get_by_normalized_name(norm)

    def get_by_domain(self, domain: str) -> Optional[Company]:
        return self.session.query(Company).filter(func.lower(Company.domain) == domain.lower()).first()

    def create(self, company: Company) -> Company:
        self.session.add(company)
        return company

    def list_all(self) -> List[Company]:
        return self.session.query(Company).all()

    def search_by_name(self, name: str) -> List[Company]:
        norm = normalize_name(name)
        return self.session.query(Company).filter(
            Company.normalized_name.contains(norm) | Company.name.contains(name)
        ).all()


class ContactRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_email(self, email: str) -> Optional[Contact]:
        return (
            self.session.query(Contact)
            .join(ContactEmail)
            .filter(ContactEmail.email == email)
            .first()
        )

    def get_by_id(self, contact_id: int) -> Optional[Contact]:
        return self.session.query(Contact).filter_by(id=contact_id).first()

    def get_by_company(self, company_id: int) -> List[Contact]:
        return self.session.query(Contact).filter_by(company_id=company_id).all()

    def list_all(self) -> List[Contact]:
        return self.session.query(Contact).all()

    def search_by_full_name(self, full_name: str) -> List[Contact]:
        return self.session.query(Contact).filter(
            Contact.full_name.ilike(f"%{full_name}%")
        ).all()

    def create(self, contact: Contact) -> Contact:
        self.session.add(contact)
        return contact

    def get_by_company_id(self, company_id: int) -> List[Contact]:
        return self.session.query(Contact).filter_by(company_id=company_id).all()


class ContactEmailRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_email(self, email: str) -> Optional[ContactEmail]:
        return self.session.query(ContactEmail).filter_by(email=email).first()

    def create(self, email_obj: ContactEmail) -> ContactEmail:
        self.session.add(email_obj)
        return email_obj


class ContactPhoneRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_phone(self, phone: str) -> Optional[ContactPhone]:
        return self.session.query(ContactPhone).filter_by(phone=phone).first()

    def create(self, phone_obj: ContactPhone) -> ContactPhone:
        self.session.add(phone_obj)
        return phone_obj


class ContactSourceRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, source_obj: ContactSource) -> ContactSource:
        self.session.add(source_obj)
        return source_obj

    def get_by_contact_id(self, contact_id: int) -> List[ContactSource]:
        return self.session.query(ContactSource).filter_by(contact_id=contact_id).all()


class OpportunityRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_company_and_title(self, company_id: int, title: str) -> Optional[Opportunity]:
        return (
            self.session.query(Opportunity)
            .filter_by(company_id=company_id, title=title)
            .first()
        )

    def get_by_company_id(self, company_id: int) -> List[Opportunity]:
        return self.session.query(Opportunity).filter_by(company_id=company_id).all()

    def list_all(self) -> List[Opportunity]:
        return self.session.query(Opportunity).all()

    def create(self, opportunity: Opportunity) -> Opportunity:
        self.session.add(opportunity)
        return opportunity

    def search_by_title(self, title: str) -> List[Opportunity]:
        return self.session.query(Opportunity).filter(
            Opportunity.title.ilike(f"%{title}%")
        ).all()


class OutreachEventRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_contact_and_opportunity(self, contact_id: int, opportunity_id: Optional[int] = None) -> List[OutreachEvent]:
        query = self.session.query(OutreachEvent).filter_by(contact_id=contact_id)
        if opportunity_id is not None:
            query = query.filter_by(opportunity_id=opportunity_id)
        return query.all()

    def get_by_company(self, company_id: int) -> List[OutreachEvent]:
        return self.session.query(OutreachEvent).filter_by(company_id=company_id).all()

    def list_all(self) -> List[OutreachEvent]:
        return self.session.query(OutreachEvent).all()

    def create(self, event: OutreachEvent) -> OutreachEvent:
        self.session.add(event)
        return event


class ReferralRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_company(self, company_id: int) -> List[Referral]:
        return self.session.query(Referral).filter_by(company_id=company_id).all()

    def get_by_contact(self, contact_id: int) -> List[Referral]:
        return self.session.query(Referral).filter_by(contact_id=contact_id).all()

    def list_all(self) -> List[Referral]:
        return self.session.query(Referral).all()

    def create(self, referral: Referral) -> Referral:
        self.session.add(referral)
        return referral
