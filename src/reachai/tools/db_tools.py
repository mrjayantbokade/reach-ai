from langchain.tools import tool
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from reachai.core.config import settings
from reachai.services.ingestion_service import IngestionService

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


class SearchCompanyInput(BaseModel):
    name: str = Field(description="Company name to search for")


class GetCompanyInput(BaseModel):
    company_id: int = Field(description="Company database ID")


class SearchContactInput(BaseModel):
    name: str = Field(description="Contact full name to search for")


class GetContactInput(BaseModel):
    contact_id: int = Field(description="Contact database ID")


class GetCompanyContactsInput(BaseModel):
    company_id: int = Field(description="Company database ID")


class GetReferralsInput(BaseModel):
    company_id: int = Field(description="Company database ID")


class GetOutreachHistoryInput(BaseModel):
    contact_id: int = Field(description="Contact database ID")


class SearchOpportunityInput(BaseModel):
    title: str = Field(description="Opportunity title to search for")


@tool(args_schema=SearchCompanyInput)
def search_company(name: str) -> str:
    """Search for a company by name. Returns company info or 'not found'."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        company = service.company_repo.get_by_name(name)
        if company:
            return f"Found company: {company.name} (id={company.id}, normalized={company.normalized_name})"
        else:
            return f"No company found for: {name}"
    finally:
        session.close()


@tool(args_schema=GetCompanyInput)
def get_company(company_id: int) -> str:
    """Get company details by ID."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        company = service.company_repo.get_by_id(company_id)
        if company:
            return f"Company: {company.name} (id={company.id}, domain={company.domain}, linkedin={company.linkedin_url})"
        return f"No company with id={company_id}"
    finally:
        session.close()


@tool(args_schema=SearchContactInput)
def search_contact(name: str) -> str:
    """Search for a contact by full name."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        contacts = service.contact_repo.search_by_full_name(name)
        if contacts:
            result = f"Found {len(contacts)} contact(s):"
            for c in contacts:
                result += f"\n  - {c.full_name} (id={c.id}, company_id={c.company_id}, title={c.job_title})"
            return result
        return f"No contact found for: {name}"
    finally:
        session.close()


@tool(args_schema=GetContactInput)
def get_contact(contact_id: int) -> str:
    """Get contact details by ID."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        contact = service.contact_repo.get_by_id(contact_id)
        if contact:
            emails = [e.email for e in contact.emails]
            return f"Contact: {contact.full_name} (id={contact.id}, company_id={contact.company_id}, title={contact.job_title}, emails={emails})"
        return f"No contact with id={contact_id}"
    finally:
        session.close()


@tool(args_schema=GetCompanyContactsInput)
def get_company_contacts(company_id: int) -> str:
    """Get all contacts for a company."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        company = service.company_repo.get_by_id(company_id)
        if not company:
            return f"No company with id={company_id}"
        contacts = service.contact_repo.get_by_company(company_id)
        if not contacts:
            return f"No contacts found for company: {company.name} (id={company_id})"
        result = f"Contacts for {company.name} (id={company_id}): {len(contacts)}"
        for c in contacts:
            emails = [e.email for e in c.emails if e.email]
            result += f"\n  - {c.full_name} (id={c.id}, title={c.job_title or 'N/A'}, email={emails[0] if emails else 'N/A'})"
        return result
    finally:
        session.close()


@tool(args_schema=GetReferralsInput)
def get_referrals(company_id: int) -> str:
    """Get referrals for a company."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        company = service.company_repo.get_by_id(company_id)
        if not company:
            return f"No company with id={company_id}"
        referrals = service.referral_repo.get_by_company(company_id)
        if not referrals:
            return f"No referrals recorded for company: {company.name} (id={company_id})"
        result = f"Referrals for {company.name} (id={company_id}): {len(referrals)}"
        for r in referrals:
            result += f"\n  - Contact ID {r.contact_id}, status={r.status}, referred_at={r.referred_at}, notes={r.notes or 'None'}"
        return result
    finally:
        session.close()


@tool(args_schema=GetOutreachHistoryInput)
def get_outreach_history(contact_id: int) -> str:
    """Get outreach history for a contact."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        events = service.outreach_repo.get_by_contact_and_opportunity(contact_id)
        if not events:
            return f"No outreach events recorded for contact id={contact_id}"
        result = f"Outreach history for contact id={contact_id}: {len(events)} event(s)"
        for e in events:
            result += f"\n  - Channel: {e.channel}, Direction: {e.direction}, Status: {e.status}, Sent: {e.sent_at}"
        return result
    finally:
        session.close()


@tool(args_schema=SearchOpportunityInput)
def search_opportunity(title: str) -> str:
    """Search for an opportunity by title."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        opportunities = service.opportunity_repo.search_by_title(title)
        if opportunities:
            result = f"Found {len(opportunities)} opportunity(ies) matching '{title}':"
            for o in opportunities:
                result += f"\n  - Title: {o.title}, Company ID: {o.company_id}, Status: {o.status}, URL: {o.url or 'None'}"
            return result
        return f"No opportunity found matching '{title}'"
    finally:
        session.close()
