from sqlalchemy.orm import Session
from reachai.repositories.company_repo import (
    CompanyRepository,
    ContactRepository,
    ContactEmailRepository,
    ContactPhoneRepository,
    ContactSourceRepository,
    OpportunityRepository,
    OutreachEventRepository,
    ReferralRepository,
    normalize_name,
)
from reachai.models.database import Company, Contact, ContactEmail, ContactPhone, ContactSource, Opportunity, OutreachEvent, Referral
from reachai.core.data_quality import company_from_business_email, is_valid_email, name_from_email, normalize_email, normalize_phone
from sqlalchemy.exc import IntegrityError
from typing import Optional, Dict, Any, List
import datetime


class IngestionService:
    """Deterministic business logic for contact/company ingestion."""

    def __init__(self, session: Session):
        self.session = session
        self.company_repo = CompanyRepository(session)
        self.contact_repo = ContactRepository(session)
        self.email_repo = ContactEmailRepository(session)
        self.phone_repo = ContactPhoneRepository(session)
        self.source_repo = ContactSourceRepository(session)
        self.opportunity_repo = OpportunityRepository(session)
        self.outreach_repo = OutreachEventRepository(session)
        self.referral_repo = ReferralRepository(session)

    def ingest_contact(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update one contact from an explicit company and contact methods.

        This service is the source of truth for validation, normalization, and
        de-duplication. A valid contact must have a company and at least one
        email address or phone number; a name is optional and becomes ``N/A``.
        """
        company_name = str(data.get("company_name") or data.get("company") or "").strip()
        company_was_explicit = bool(company_name)

        raw_emails = [data.get("email"), *(data.get("emails") or [])]
        emails = []
        for value in raw_emails:
            if value is None or not str(value).strip():
                continue
            email = normalize_email(str(value))
            if not is_valid_email(email):
                return {"status": "error", "message": f"Invalid email address: {value}"}
            if email not in emails:
                emails.append(email)

        raw_phones = [data.get("phone"), *(data.get("phones") or [])]
        phones = []
        for value in raw_phones:
            if value is None or not str(value).strip():
                continue
            phone = normalize_phone(str(value))
            if not phone:
                return {"status": "error", "message": f"Invalid phone number: {value}"}
            if phone not in phones:
                phones.append(phone)

        if not emails and not phones:
            return {
                "status": "error",
                "message": "Provide at least one email address or phone number.",
            }

        inferred_company = next(
            (company_from_business_email(email) for email in emails if company_from_business_email(email)),
            None,
        )
        inferred_domain = inferred_company[1] if inferred_company else None
        if not company_name and inferred_company:
            company_name = inferred_company[0]
        if not company_name:
            return {
                "status": "error",
                "message": "A company name is required when no business email domain is available.",
            }

        matched_contacts = {}
        for email in emails:
            contact = self.contact_repo.get_by_email(email)
            if contact:
                matched_contacts[contact.id] = contact
        for phone in phones:
            phone_record = self.phone_repo.get_by_phone(phone)
            if phone_record:
                matched_contacts[phone_record.contact_id] = phone_record.contact

        if len(matched_contacts) > 1:
            return {
                "status": "error",
                "message": "The supplied email addresses and phone numbers belong to different contacts.",
            }

        company = self.company_repo.get_by_name(company_name)
        if not company and not company_was_explicit and inferred_domain:
            company = self.company_repo.get_by_domain(inferred_domain)
        if not company and not company_was_explicit and inferred_company:
            inferred_compact_name = normalize_name(company_name).replace("_", "")
            company = next(
                (
                    candidate
                    for candidate in self.company_repo.list_all()
                    if candidate.normalized_name.replace("_", "") == inferred_compact_name
                ),
                None,
            )
        if not company:
            company = Company(
                name=company_name,
                normalized_name=normalize_name(company_name),
                domain=data.get("company_domain") or inferred_domain,
            )
            self.company_repo.create(company)
            try:
                self.session.flush()
            except IntegrityError:
                # Another tool call may have created the same company between
                # our lookup and insert. Re-read it instead of failing the save.
                self.session.rollback()
                company = self.company_repo.get_by_name(company_name)
                if not company:
                    return {"status": "error", "message": "Could not resolve the company."}
                # rollback detaches rows loaded before the failed insert; reload
                # any matched contact before applying this request's updates.
                matched_contacts = {
                    contact_id: self.contact_repo.get_by_id(contact_id)
                    for contact_id in matched_contacts
                }
                if any(contact is None for contact in matched_contacts.values()):
                    return {"status": "error", "message": "Could not resolve the existing contact."}

        full_name = str(data.get("full_name") or data.get("name") or "").strip()
        if not full_name and emails:
            full_name = name_from_email(emails[0]) or "N/A"
        full_name = full_name or "N/A"
        contact = next(iter(matched_contacts.values()), None)
        existing_contact = contact is not None

        if contact:
            if full_name != "N/A":
                contact.full_name = full_name
            if data.get("job_title"):
                contact.job_title = data["job_title"]
            if data.get("department"):
                contact.department = data["department"]
            if contact.company_id != company.id:
                contact.company_id = company.id
        else:
            contact = Contact(
                company_id=company.id,
                full_name=full_name,
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
                job_title=data.get("job_title"),
                department=data.get("department"),
                contact_type=data.get("contact_type"),
                linkedin_url=data.get("linkedin_url"),
            )
            self.contact_repo.create(contact)
            self.session.flush()

        has_primary_email = any(item.is_primary for item in contact.emails)
        for email in emails:
            email_record = self.email_repo.get_by_email(email)
            if not email_record:
                self.email_repo.create(ContactEmail(
                    contact_id=contact.id,
                    email=email,
                    email_type=data.get("email_type", "work"),
                    is_primary=not has_primary_email,
                ))
                has_primary_email = True

        has_primary_phone = any(item.is_primary for item in contact.phones)
        for phone in phones:
            phone_record = self.phone_repo.get_by_phone(phone)
            if not phone_record:
                self.phone_repo.create(ContactPhone(
                    contact_id=contact.id,
                    phone=phone,
                    phone_type=data.get("phone_type", "mobile"),
                    is_primary=not has_primary_phone,
                ))
                has_primary_phone = True

        self.source_repo.create(ContactSource(
            contact_id=contact.id,
            source_type=data.get("source_type", "user_input"),
            source_url=data.get("source_url"),
            raw_text=data.get("raw_text", data.get("notes")),
        ))
        self.session.commit()

        return {
            "status": "success",
            "company": {"id": company.id, "name": company.name},
            "contact": {
                "id": contact.id,
                "full_name": contact.full_name,
                "emails": emails,
                "phones": phones,
            },
            "message": "Contact updated" if existing_contact else "Contact created",
            "duplicate_detected": existing_contact,
            "company_inferred": not company_was_explicit and inferred_company is not None,
        }

    def get_company_intelligence(self, company_name: str) -> Dict[str, Any]:
        # Strip punctuation for lookup
        cleaned_name = company_name.strip(".?;!,") if company_name else company_name
        company = self.company_repo.get_by_name(cleaned_name)
        if not company:
            return {"status": "not_found", "message": f"No company found: {company_name}"}

        contacts = self.contact_repo.get_by_company(company.id)
        referrals = self.referral_repo.get_by_company(company.id)
        outreach_events = self.outreach_repo.get_by_company(company.id)
        opportunities = self.opportunity_repo.get_by_company_id(company.id)

        result = {
            "status": "success",
            "company": {
                "id": company.id,
                "name": company.name,
                "normalized_name": company.normalized_name,
                "domain": company.domain,
                "website": company.website,
                "linkedin_url": company.linkedin_url,
                "industry": company.industry,
                "location": company.location,
            },
            "contacts_count": len(contacts),
            "contacts": [
                {
                    "id": c.id,
                    "full_name": c.full_name,
                    "first_name": c.first_name,
                    "last_name": c.last_name,
                    "job_title": c.job_title,
                    "department": c.department,
                    "contact_type": c.contact_type,
                    "linkedin_url": c.linkedin_url,
                    "emails": [{"email": e.email, "type": e.email_type, "primary": e.is_primary, "verified": e.verified} for e in c.emails],
                    "phones": [{"phone": p.phone, "type": p.phone_type, "primary": p.is_primary} for p in c.phones],
                }
                for c in contacts
            ],
            "referrals": [
                {"contact_id": r.contact_id, "contact_name": next((c.full_name for c in contacts if c.id == r.contact_id), "NA"), "status": r.status, "referred_at": r.referred_at, "notes": r.notes}
                for r in referrals
            ],
            "opportunities": [
                {"id": o.id, "title": o.title, "status": o.status, "discovered_at": o.discovered_at, "url": o.url, "location": o.location}
                for o in opportunities
            ],
        }
        return result

    def ingest_opportunity(self, data: Dict[str, Any]) -> Dict[str, Any]:
        company_name = data.get("company_name") or data.get("company")
        company = None
        if company_name:
            company = self.company_repo.get_by_name(company_name)
            if not company:
                company = Company(
                    name=company_name,
                    normalized_name=normalize_name(company_name),
                )
                self.company_repo.create(company)

        title = data.get("title")
        if not title:
            return {"status": "error", "message": "Opportunity requires a title"}

        opportunity = None
        if company:
            opportunity = self.opportunity_repo.get_by_company_and_title(company.id, title)

        if not opportunity:
            opportunity = Opportunity(
                company_id=company.id if company else None,
                title=title,
                url=data.get("url"),
                source=data.get("source"),
                location=data.get("location"),
                description=data.get("description"),
                status=data.get("status", "open"),
            )
            self.opportunity_repo.create(opportunity)
        else:
            # Idempotent update
            if data.get("url"):
                opportunity.url = data.get("url")
            if data.get("description"):
                opportunity.description = data.get("description")
            if data.get("status"):
                opportunity.status = data.get("status")

        self.session.commit()
        return {
            "status": "success",
            "opportunity": {
                "id": opportunity.id,
                "title": opportunity.title,
                "company_id": opportunity.company_id,
                "company_name": company.name if company else "NA",
            },
            "message": "Opportunity ingested successfully",
        }

    def get_referrals_for_company(self, company_name: str) -> Dict[str, Any]:
        company = self.company_repo.get_by_name(company_name)
        if not company:
            return {"status": "not_found", "message": f"No company found: {company_name}"}
        referrals = self.referral_repo.get_by_company(company.id)
        return {
            "status": "success",
            "company": company.name,
            "referrals": [
                {
                    "contact_id": r.contact_id,
                    "contact_name": next((c.full_name for c in self.contact_repo.get_by_company(company.id) if c.id == r.contact_id), "NA"),
                    "referred_at": r.referred_at,
                    "status": r.status,
                    "notes": r.notes,
                }
                for r in referrals
            ],
        }

    def get_outreach_history_for_contact(self, contact_name: str, company_name: Optional[str] = None) -> Dict[str, Any]:
        contacts = self.contact_repo.search_by_full_name(contact_name)
        if not contacts:
            return {"status": "not_found", "message": f"No contact found: {contact_name}"}
        contact = contacts[0]
        events = self.outreach_repo.get_by_contact_and_opportunity(contact.id)
        return {
            "status": "success",
            "contact": {"id": contact.id, "full_name": contact.full_name},
            "events": [
                {
                    "channel": e.channel,
                    "direction": e.direction,
                    "subject": e.subject,
                    "status": e.status,
                    "sent_at": e.sent_at,
                    "response_at": e.response_at,
                    "notes": e.notes,
                }
                for e in events
            ],
        }

    def get_potential_outreach_candidates(self, company_name: str, opportunity_title: Optional[str] = None) -> Dict[str, Any]:
        company = self.company_repo.get_by_name(company_name)
        if not company:
            return {"status": "not_found", "message": f"No company found: {company_name}"}
        contacts = self.contact_repo.get_by_company(company.id)
        referrals = self.referral_repo.get_by_company(company.id)
        referral_contact_ids = {r.contact_id for r in referrals}
        outreach_events = self.outreach_repo.get_by_company(company.id)

        candidates = []
        for c in contacts:
            # Basic signals
            has_email = len([e for e in c.emails if e.email]) > 0
            has_referral = c.id in referral_contact_ids
            previous_outreach = len([e for e in outreach_events if e.contact_id == c.id]) > 0
            emails = [e.email for e in c.emails if e.email]
            phones = [p.phone for p in c.phones if p.phone]

            candidates.append({
                "contact_id": c.id,
                "full_name": c.full_name,
                "job_title": c.job_title or "NA",
                "email": emails[0] if emails else "NA",
                "phone": phones[0] if phones else "NA",
                "referral_history": "YES" if has_referral else "NO",
                "previous_outreach": "YES" if previous_outreach else "NONE",
                "contact_type": c.contact_type or "NA",
                "department": c.department or "NA",
            })

        # Simple deterministic ranking: referrals first, then previous outreach, then role relevance
        def score(candidate):
            s = 0
            if candidate["referral_history"] == "YES":
                s += 3
            if candidate["previous_outreach"] == "NONE":
                s += 2  # Prefer people not yet contacted
            elif candidate["previous_outreach"] == "YES":
                s += 1
            if candidate["email"] != "NA":
                s += 1
            if "recruiter" in (candidate.get("job_title", "") or "").lower():
                s += 2
            if "engineer" in (candidate.get("job_title", "") or "").lower():
                s += 2
            if "manager" in (candidate.get("job_title", "") or "").lower():
                s += 1
            return s

        candidates.sort(key=lambda c: score(c), reverse=True)

        return {
            "status": "success",
            "company": company.name,
            "opportunity_title": opportunity_title,
            "candidates": candidates,
            "message": f"Found {len(candidates)} potential contacts at {company.name}",
        }
