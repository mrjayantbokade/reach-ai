from typing import List, Dict, Any, Optional
from reachai.models.database import Contact, Opportunity
from reachai.repositories.company_repo import ContactRepository, CompanyRepository, ReferralRepository, OutreachEventRepository, OpportunityRepository
from sqlalchemy.orm import Session


class CandidateRankingService:
    """Deterministic ranking service for outreach candidates."""

    def __init__(self, session: Session):
        self.session = session
        self.contact_repo = ContactRepository(session)
        self.company_repo = CompanyRepository(session)
        self.referral_repo = ReferralRepository(session)
        self.outreach_repo = OutreachEventRepository(session)
        self.opportunity_repo = OpportunityRepository(session)

    def rank_candidates(self, company_name: str, opportunity_title: Optional[str] = None) -> List[Dict[str, Any]]:
        company = self.company_repo.get_by_name(company_name)
        if not company:
            return []
        contacts = self.contact_repo.get_by_company(company.id)
        referrals = self.referral_repo.get_by_company(company.id)
        referral_ids = {r.contact_id for r in referrals}
        outreach_events = self.outreach_repo.get_by_company(company.id)

        candidates = []
        for c in contacts:
            # Signals
            has_email = len([e for e in c.emails if e.email]) > 0
            has_referral = c.id in referral_ids
            previous_outreach = len([e for e in outreach_events if e.contact_id == c.id]) > 0
            emails = [e.email for e in c.emails if e.email]
            phones = [p.phone for p in c.phones if p.phone]

            # Simple deterministic score
            score = 0
            if has_referral:
                score += 10
            if previous_outreach == 0:
                score += 5
            elif previous_outreach > 0:
                score += 2
            if has_email:
                score += 3
            if c.contact_type and "recruiter" in (c.contact_type or "").lower():
                score += 8
            if c.contact_type and "engineer" in (c.contact_type or "").lower():
                score += 8
            if c.contact_type and "manager" in (c.contact_type or "").lower():
                score += 5
            if c.job_title and "recruiter" in (c.job_title or "").lower():
                score += 8
            if c.job_title and "engineer" in (c.job_title or "").lower():
                score += 8
            if c.job_title and "manager" in (c.job_title or "").lower():
                score += 5

            candidates.append({
                "contact_id": c.id,
                "full_name": c.full_name,
                "job_title": c.job_title or "NA",
                "contact_type": c.contact_type or "NA",
                "department": c.department or "NA",
                "email": emails[0] if emails else "NA",
                "emails": emails,
                "phone": phones[0] if phones else "NA",
                "phones": phones,
                "referral_history": "YES" if has_referral else "NO",
                "previous_outreach_count": previous_outreach,
                "previous_outreach": "YES" if previous_outreach > 0 else "NONE",
                "score": score,
                "linkedin_url": c.linkedin_url or "NA",
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates
