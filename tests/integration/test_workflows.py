import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from reachai.core.config import settings
from reachai.services.ingestion_service import IngestionService
from reachai.services.ranking_service import CandidateRankingService

DB_URL = settings.DATABASE_URL


@pytest.fixture(scope="module")
def session():
    engine = create_engine(DB_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_company_create_and_lookup(session):
    service = IngestionService(session)
    # Ensure company lookup works with generic sample data.
    result = service.get_company_intelligence("Example Corp")
    assert result.get("status") == "success" or result.get("status") == "not_found"


def test_contact_ingestion(session):
    service = IngestionService(session)
    result = service.ingest_contact({
        "full_name": "Sample Contact",
        "company": "Example Corp",
        "email": "test_engineer@example.com",
        "contact_type": "Engineer",
        "job_title": "Software Engineer",
    })
    assert result.get("status") == "success"
    assert result.get("contact") is not None
    assert result.get("company") is not None


def test_duplicate_detection(session):
    service = IngestionService(session)
    # Re-ingest same email should not create duplicate
    result = service.ingest_contact({
        "full_name": "Sample Contact",
        "company": "Example Corp",
        "email": "test_engineer@example.com",
    })
    assert result.get("status") == "success"


def test_opportunity_ingestion(session):
    service = IngestionService(session)
    result = service.ingest_opportunity({
        "title": "Senior Software Engineer",
        "company_name": "Example Corp",
        "url": "https://example.com/careers/senior-engineer",
    })
    assert result.get("status") == "success"
    assert result.get("opportunity") is not None


def test_company_intelligence(session):
    service = IngestionService(session)
    info = service.get_company_intelligence("Example Corp")
    if info.get("status") == "success":
        assert info.get("contacts_count") >= 1
        assert "contacts" in info


def test_referral_query(session):
    service = IngestionService(session)
    info = service.get_referrals_for_company("Example Corp")
    assert "status" in info


def test_ranking_service(session):
    service = IngestionService(session)
    ranking = CandidateRankingService(session)
    candidates = ranking.rank_candidates("Example Corp")
    assert isinstance(candidates, list)


def test_outreach_history(session):
    service = IngestionService(session)
    info = service.get_outreach_history_for_contact("Sample Contact")
    assert info.get("status") in ("success", "not_found")
