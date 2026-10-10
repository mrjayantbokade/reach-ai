from pydantic import BaseModel, Field
from langchain_core.tools import tool
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from typing import List, Optional
from datetime import datetime
from difflib import SequenceMatcher
from reachai.core.config import settings
from reachai.models.database import OutreachEvent, Referral
from reachai.repositories.company_repo import normalize_name
from reachai.services.ranking_service import CandidateRankingService
from reachai.services.ingestion_service import IngestionService

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


class SearchCompanySchema(BaseModel):
    name: str = Field(description="The company name to search for.")


class ListCompaniesSchema(BaseModel):
    pass


class ListContactsSchema(BaseModel):
    pass


class ListOpportunitiesSchema(BaseModel):
    pass


class ListReferralsSchema(BaseModel):
    pass


class ListOutreachEventsSchema(BaseModel):
    pass


class GetCompanySchema(BaseModel):
    company_id: int = Field(description="The database ID of the company.")


class SearchContactSchema(BaseModel):
    name: str = Field(description="The full or partial name of the contact to search for.")


class GetContactSchema(BaseModel):
    contact_id: int = Field(description="The database ID of the contact.")


class GetCompanyContactsSchema(BaseModel):
    company_id: int = Field(description="The database ID of the company.")


class CreateContactSchema(BaseModel):
    company_name: Optional[str] = Field(
        default=None,
        description="Company name. Omit only when a business email domain can identify the company; a stated company applies to every contact in a pasted group."
    )
    full_name: Optional[str] = Field(
        default=None,
        description=(
            "Optional full name. If the user did not state a name but an email local-part "
            "clearly represents one, derive it before calling this tool: "
            "person@company.com -> Person; person.name@company.com -> Person Name. "
            "Omit only when no readable name can be derived; it will be saved as N/A."
        ),
    )
    job_title: str = Field(description="Job title.", default="")
    emails: List[str] = Field(
        default_factory=list,
        description="All email addresses supplied for this same contact.",
    )
    phones: List[str] = Field(
        default_factory=list,
        description="All mobile or phone numbers supplied for this same contact.",
    )


class CreateOpportunitySchema(BaseModel):
    company_name: str = Field(description="Company name for the opportunity.")
    title: str = Field(description="Title of the opportunity.")
    url: str = Field(description="URL of the opportunity.", default="")


class GetReferralsSchema(BaseModel):
    company_id: int = Field(description="The database ID of the company.")


class GetOutreachHistorySchema(BaseModel):
    contact_id: int = Field(description="The database ID of the contact.")


class GetCompanyEmailsSchema(BaseModel):
    company_id: int = Field(description="The database ID of the company whose saved email addresses are needed.")


class GetCompanyPhonesSchema(BaseModel):
    company_id: int = Field(description="The database ID of the company whose saved phone numbers are needed.")


class GetContactSourcesSchema(BaseModel):
    contact_id: int = Field(description="The database ID of the contact whose saved source records are needed.")


class SearchOpportunitySchema(BaseModel):
    title: str = Field(description="Full or partial job/opportunity title to search for.")


class GetCompanyOpportunitiesSchema(BaseModel):
    company_id: int = Field(description="The database ID of the company whose opportunities are needed.")


class CreateReferralSchema(BaseModel):
    contact_id: int = Field(description="The contact making or associated with the referral.")
    company_id: int = Field(description="The company database ID.")
    opportunity_id: Optional[int] = Field(default=None, description="Optional opportunity database ID.")
    status: str = Field(default="pending", description="Referral status.")
    notes: str = Field(default="", description="Optional referral notes.")


class CreateOutreachEventSchema(BaseModel):
    contact_id: Optional[int] = Field(default=None, description="Optional contact database ID.")
    company_id: Optional[int] = Field(default=None, description="Optional company database ID.")
    opportunity_id: Optional[int] = Field(default=None, description="Optional opportunity database ID.")
    channel: str = Field(description="Communication channel, such as email, LinkedIn, or phone.")
    direction: str = Field(description="Direction: inbound or outbound.")
    subject: str = Field(default="", description="Optional message subject.")
    message: str = Field(default="", description="Optional message text or notes.")
    status: str = Field(default="", description="Optional outreach status.")


class GetUncontactedCompanyContactsSchema(BaseModel):
    company_id: int = Field(description="The company database ID.")


class RankCandidatesSchema(BaseModel):
    company_name: str = Field(description="Company name for outreach candidate ranking.")
    opportunity_title: Optional[str] = Field(default=None, description="Optional opportunity title context.")


@tool(args_schema=SearchCompanySchema)
def search_company(name: str) -> str:
    """Search saved companies by exact, partial, or typo-tolerant name match."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        company = service.company_repo.get_by_name(name)
        if company:
            return f"Found company: {company.name} (id={company.id}, normalized_name={company.normalized_name}, domain={company.domain or 'None'})"

        query = normalize_name(name)
        companies = service.company_repo.list_all()
        scored_matches = sorted(
            (
                (
                    1.0 if query in candidate.normalized_name or candidate.normalized_name in query
                    else SequenceMatcher(None, query, candidate.normalized_name).ratio(),
                    candidate,
                )
                for candidate in companies
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        matches = [(score, candidate) for score, candidate in scored_matches[:3] if score >= 0.55]
        if not matches:
            return f"No company found matching '{name}'."

        best_score, best_match = matches[0]
        lines = [
            f"No exact company match for '{name}'. Closest match: "
            f"{best_match.name} (id={best_match.id}, domain={best_match.domain or 'N/A'})."
        ]
        if len(matches) > 1:
            lines.append("Other similar saved companies:")
        lines.extend(
            f"  - {candidate.name} (id={candidate.id}, domain={candidate.domain or 'N/A'})"
            for _, candidate in matches[1:]
        )
        return "\n".join(lines)
    finally:
        session.close()


@tool(args_schema=ListCompaniesSchema)
def list_companies() -> str:
    """List every company currently saved in the database."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        companies = sorted(service.company_repo.list_all(), key=lambda company: company.name.casefold())
        if not companies:
            return "No companies are saved."
        lines = [f"Saved companies: {len(companies)}"]
        lines.extend(f"  - {company.name} (id={company.id})" for company in companies)
        return "\n".join(lines)
    finally:
        session.close()


@tool(args_schema=ListContactsSchema)
def list_contacts() -> str:
    """List every saved contact across all companies."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        contacts = sorted(service.contact_repo.list_all(), key=lambda contact: (contact.company_id, contact.full_name.casefold()))
        if not contacts:
            return "No contacts are saved."
        lines = [f"Saved contacts: {len(contacts)}"]
        lines.extend(
            f"  - {contact.full_name} (id={contact.id}, company_id={contact.company_id}, title={contact.job_title or 'N/A'})"
            for contact in contacts
        )
        return "\n".join(lines)
    finally:
        session.close()


@tool(args_schema=ListOpportunitiesSchema)
def list_opportunities() -> str:
    """List every saved job opportunity across all companies."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        opportunities = service.opportunity_repo.list_all()
        if not opportunities:
            return "No opportunities are saved."
        lines = [f"Saved opportunities: {len(opportunities)}"]
        lines.extend(
            f"  - {opportunity.title} (id={opportunity.id}, company_id={opportunity.company_id}, status={opportunity.status})"
            for opportunity in opportunities
        )
        return "\n".join(lines)
    finally:
        session.close()


@tool(args_schema=ListReferralsSchema)
def list_referrals() -> str:
    """List every referral saved in the database."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        referrals = service.referral_repo.list_all()
        if not referrals:
            return "No referrals are saved."
        lines = [f"Saved referrals: {len(referrals)}"]
        lines.extend(
            f"  - referral_id={referral.id}, contact_id={referral.contact_id}, company_id={referral.company_id}, status={referral.status}"
            for referral in referrals
        )
        return "\n".join(lines)
    finally:
        session.close()


@tool(args_schema=ListOutreachEventsSchema)
def list_outreach_events() -> str:
    """List every saved outreach event in the database."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        events = service.outreach_repo.list_all()
        if not events:
            return "No outreach events are saved."
        lines = [f"Saved outreach events: {len(events)}"]
        lines.extend(
            f"  - event_id={event.id}, contact_id={event.contact_id}, company_id={event.company_id}, channel={event.channel}, direction={event.direction}, status={event.status or 'N/A'}"
            for event in events
        )
        return "\n".join(lines)
    finally:
        session.close()


@tool(args_schema=GetCompanySchema)
def get_company(company_id: int) -> str:
    """Get full company details by ID."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        company = service.company_repo.get_by_id(company_id)
        if company:
            return f"Company: {company.name} (id={company.id}, domain={company.domain}, linkedin={company.linkedin_url}, industry={company.industry or 'N/A'})"
        return f"No company found with id={company_id}"
    finally:
        session.close()


@tool(args_schema=SearchContactSchema)
def search_contact(name: str) -> str:
    """Search for a contact by full or partial name."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        contacts = service.contact_repo.search_by_full_name(name)
        if contacts:
            lines = [f"Found {len(contacts)} contact(s) matching '{name}':"]
            for c in contacts:
                emails = [e.email for e in c.emails if e.email]
                lines.append(f"  - {c.full_name} (id={c.id}, company_id={c.company_id}, title={c.job_title or 'N/A'}, email={emails[0] if emails else 'N/A'})")
            return "\n".join(lines)
        return f"No contact found for: {name}"
    finally:
        session.close()


@tool(args_schema=GetContactSchema)
def get_contact(contact_id: int) -> str:
    """Get full contact details by database ID."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        contact = service.contact_repo.get_by_id(contact_id)
        if contact:
            emails = [e.email for e in contact.emails if e.email]
            phones = [p.phone for p in contact.phones if p.phone]
            return f"Contact: {contact.full_name} (id={contact.id}, company_id={contact.company_id}, title={contact.job_title or 'N/A'}, email={emails[0] if emails else 'N/A'}, phone={phones[0] if phones else 'N/A'}, linkedin={contact.linkedin_url or 'N/A'})"
        return f"No contact found with id={contact_id}"
    finally:
        session.close()


@tool(args_schema=GetCompanyContactsSchema)
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
        lines = [f"Contacts for {company.name} (id={company_id}): {len(contacts)}"]
        for c in contacts:
            emails = [e.email for e in c.emails if e.email]
            phones = [p.phone for p in c.phones if p.phone]
            lines.append(
                f"  - {c.full_name} (id={c.id}, title={c.job_title or 'N/A'}, "
                f"emails={', '.join(emails) or 'N/A'}, phones={', '.join(phones) or 'N/A'})"
            )
        return "\n".join(lines)
    finally:
        session.close()


@tool(args_schema=GetCompanyEmailsSchema)
def get_company_emails(company_id: int) -> str:
    """Get only the unique saved email addresses for a company, with one address per line."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        company = service.company_repo.get_by_id(company_id)
        if not company:
            return f"No company with id={company_id}"

        emails = sorted(
            {
                email.email.strip()
                for contact in service.contact_repo.get_by_company(company_id)
                for email in contact.emails
                if email.email and email.email.strip()
            },
            key=str.casefold,
        )
        return "\n".join(emails) if emails else f"No email addresses found for {company.name}."
    finally:
        session.close()


@tool(args_schema=GetCompanyPhonesSchema)
def get_company_phones(company_id: int) -> str:
    """Get only the unique saved phone numbers for a company, one per line."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        company = service.company_repo.get_by_id(company_id)
        if not company:
            return f"No company with id={company_id}"
        phones = sorted({
            phone.phone.strip()
            for contact in service.contact_repo.get_by_company(company_id)
            for phone in contact.phones
            if phone.phone and phone.phone.strip()
        })
        return "\n".join(phones) if phones else f"No phone numbers found for {company.name}."
    finally:
        session.close()


@tool(args_schema=GetContactSourcesSchema)
def get_contact_sources(contact_id: int) -> str:
    """Get the saved provenance/source records for a contact."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        contact = service.contact_repo.get_by_id(contact_id)
        if not contact:
            return f"No contact with id={contact_id}"
        sources = service.source_repo.get_by_contact_id(contact_id)
        if not sources:
            return f"No source records found for {contact.full_name}."
        lines = [f"Sources for {contact.full_name}:"]
        lines.extend(
            f"  - {source.source_type}, captured_at={source.captured_at}, url={source.source_url or 'N/A'}"
            for source in sources
        )
        return "\n".join(lines)
    finally:
        session.close()


@tool(args_schema=SearchOpportunitySchema)
def search_opportunity(title: str) -> str:
    """Search saved opportunities by full or partial title."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        opportunities = service.opportunity_repo.search_by_title(title)
        if not opportunities:
            return f"No opportunities found matching '{title}'."
        lines = [f"Found {len(opportunities)} opportunity(ies):"]
        lines.extend(
            f"  - {opportunity.title} (company_id={opportunity.company_id}, status={opportunity.status}, url={opportunity.url or 'N/A'})"
            for opportunity in opportunities
        )
        return "\n".join(lines)
    finally:
        session.close()


@tool(args_schema=GetCompanyOpportunitiesSchema)
def get_company_opportunities(company_id: int) -> str:
    """Get all saved opportunities for a company."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        company = service.company_repo.get_by_id(company_id)
        if not company:
            return f"No company with id={company_id}"
        opportunities = service.opportunity_repo.get_by_company_id(company_id)
        if not opportunities:
            return f"No opportunities found for {company.name}."
        lines = [f"Opportunities for {company.name}:"]
        lines.extend(
            f"  - {opportunity.title} (id={opportunity.id}, status={opportunity.status}, url={opportunity.url or 'N/A'})"
            for opportunity in opportunities
        )
        return "\n".join(lines)
    finally:
        session.close()


@tool(args_schema=CreateContactSchema)
def create_contact(
    company_name: Optional[str] = None,
    full_name: Optional[str] = None,
    job_title: str = "",
    emails: List[str] = [],
    phones: List[str] = [],
) -> str:
    """Create/update one contact. Keep all supplied personal and business emails for that same person together; infer company from the business domain when needed."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        result = service.ingest_contact({
            "full_name": full_name,
            "company_name": company_name,
            "job_title": job_title,
            "emails": emails,
            "phones": phones,
            "source_type": "user_input",
        })
        if result.get("status") == "success":
            company_info = result.get("company", {})
            contact_info = result.get("contact", {})
            emails_text = ", ".join(contact_info.get("emails", [])) or "none"
            phones_text = ", ".join(contact_info.get("phones", [])) or "none"
            return (
                f"{result.get('message')}: {contact_info.get('full_name')} at "
                f"{company_info.get('name', company_name)} "
                f"(contact_id={contact_info.get('id')}, company_id={company_info.get('id')}). "
                f"Emails: {emails_text}. Phones: {phones_text}."
            )
        return f"Contact was not saved: {result.get('message', result.get('status'))}"
    finally:
        session.close()


@tool(args_schema=CreateOpportunitySchema)
def create_opportunity(company_name: str, title: str, url: str = "") -> str:
    """Create or update an opportunity/job opening at a company."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        result = service.ingest_opportunity({
            "title": title,
            "company_name": company_name,
            "url": url,
        })
        session.commit()
        if result.get("status") == "success":
            op = result.get("opportunity", {})
            return f"Opportunity recorded: {op.get('title')} at {op.get('company_name', company_name)} (opportunity_id={op.get('id')})"
        else:
            return f"Failed to create opportunity: {result.get('message', result.get('status'))}"
    finally:
        session.close()


@tool(args_schema=CreateReferralSchema)
def create_referral(
    contact_id: int,
    company_id: int,
    opportunity_id: Optional[int] = None,
    status: str = "pending",
    notes: str = "",
) -> str:
    """Record a referral from a saved contact for a saved company."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        contact = service.contact_repo.get_by_id(contact_id)
        company = service.company_repo.get_by_id(company_id)
        if not contact:
            return f"No contact with id={contact_id}"
        if not company:
            return f"No company with id={company_id}"
        referral = Referral(
            contact_id=contact_id,
            company_id=company_id,
            opportunity_id=opportunity_id,
            status=status or "pending",
            notes=notes or None,
        )
        service.referral_repo.create(referral)
        session.commit()
        return f"Referral recorded for {contact.full_name} at {company.name} (referral_id={referral.id})."
    finally:
        session.close()


@tool(args_schema=CreateOutreachEventSchema)
def create_outreach_event(
    channel: str,
    direction: str,
    contact_id: Optional[int] = None,
    company_id: Optional[int] = None,
    opportunity_id: Optional[int] = None,
    subject: str = "",
    message: str = "",
    status: str = "",
) -> str:
    """Record an inbound or outbound outreach event for a saved contact or company."""
    normalized_direction = direction.strip().lower()
    if normalized_direction not in {"inbound", "outbound"}:
        return "Outreach event was not saved: direction must be 'inbound' or 'outbound'."
    session = SessionLocal()
    try:
        service = IngestionService(session)
        if not contact_id and not company_id:
            return "Outreach event was not saved: provide a contact_id or company_id."
        if contact_id and not service.contact_repo.get_by_id(contact_id):
            return f"No contact with id={contact_id}"
        if company_id and not service.company_repo.get_by_id(company_id):
            return f"No company with id={company_id}"
        event = OutreachEvent(
            contact_id=contact_id,
            company_id=company_id,
            opportunity_id=opportunity_id,
            channel=channel.strip(),
            direction=normalized_direction,
            subject=subject or None,
            message=message or None,
            status=status or None,
            sent_at=datetime.utcnow() if normalized_direction == "outbound" else None,
            response_at=datetime.utcnow() if normalized_direction == "inbound" else None,
        )
        service.outreach_repo.create(event)
        session.commit()
        return f"Outreach event recorded (event_id={event.id}, channel={event.channel}, direction={event.direction})."
    finally:
        session.close()


@tool(args_schema=GetUncontactedCompanyContactsSchema)
def get_uncontacted_company_contacts(company_id: int) -> str:
    """Get company contacts that have no recorded outreach event."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        company = service.company_repo.get_by_id(company_id)
        if not company:
            return f"No company with id={company_id}"
        contacted_ids = {event.contact_id for event in service.outreach_repo.get_by_company(company_id) if event.contact_id}
        contacts = [contact for contact in service.contact_repo.get_by_company(company_id) if contact.id not in contacted_ids]
        if not contacts:
            return f"Every saved contact at {company.name} has outreach history."
        lines = [f"Contacts at {company.name} with no outreach history:"]
        lines.extend(f"  - {contact.full_name} (id={contact.id})" for contact in contacts)
        return "\n".join(lines)
    finally:
        session.close()


@tool(args_schema=RankCandidatesSchema)
def rank_outreach_candidates(company_name: str, opportunity_title: Optional[str] = None) -> str:
    """Rank the best saved contacts to approach for an opportunity at a company."""
    session = SessionLocal()
    try:
        candidates = CandidateRankingService(session).rank_candidates(company_name, opportunity_title)
        if not candidates:
            return f"No outreach candidates found for {company_name}."
        lines = [f"Ranked outreach candidates for {company_name}:"]
        lines.extend(
            f"  - {candidate['full_name']} (contact_id={candidate['contact_id']}, score={candidate['score']}, title={candidate['job_title']}, email={candidate['email']})"
            for candidate in candidates
        )
        return "\n".join(lines)
    finally:
        session.close()


@tool(args_schema=GetReferralsSchema)
def get_referrals(company_id: int) -> str:
    """Get all referrals for a company."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        company = service.company_repo.get_by_id(company_id)
        if not company:
            return f"No company with id={company_id}"
        referrals = service.referral_repo.get_by_company(company_id)
        if not referrals:
            return f"No referrals recorded for company: {company.name} (id={company_id})"
        lines = [f"Referrals for {company.name} (id={company_id}): {len(referrals)}"]
        for r in referrals:
            lines.append(f"  - Contact ID {r.contact_id}, status={r.status}, referred_at={r.referred_at}, notes={r.notes or 'None'}")
        return "\n".join(lines)
    finally:
        session.close()


@tool(args_schema=GetOutreachHistorySchema)
def get_outreach_history(contact_id: int) -> str:
    """Get outreach events/history for a contact."""
    session = SessionLocal()
    try:
        service = IngestionService(session)
        events = service.outreach_repo.get_by_contact_and_opportunity(contact_id)
        contact = service.contact_repo.get_by_id(contact_id)
        name = contact.full_name if contact else f"contact_id={contact_id}"
        if not events:
            return f"No outreach events recorded for {name} (contact_id={contact_id})"
        lines = [f"Outreach history for {name} (contact_id={contact_id}): {len(events)} event(s)"]
        for e in events:
            lines.append(f"  - Channel: {e.channel}, Direction: {e.direction}, Subject: {e.subject or 'None'}, Status: {e.status or 'None'}, Sent: {e.sent_at}, Response: {e.response_at}")
        return "\n".join(lines)
    finally:
        session.close()
