from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Index
)
from sqlalchemy.orm import relationship
from datetime import datetime
from reachai.db import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    normalized_name = Column(String(255), nullable=False, index=True, unique=True)
    domain = Column(String(255), nullable=True)
    website = Column(String(500), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    industry = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contacts = relationship("Contact", back_populates="company", cascade="all, delete-orphan")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    full_name = Column(String(255), nullable=False)
    job_title = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)
    contact_type = Column(String(50), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="contacts")
    emails = relationship("ContactEmail", back_populates="contact", cascade="all, delete-orphan")
    phones = relationship("ContactPhone", back_populates="contact", cascade="all, delete-orphan")
    sources = relationship("ContactSource", back_populates="contact", cascade="all, delete-orphan")


class ContactEmail(Base):
    __tablename__ = "contact_emails"

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False)
    email_type = Column(String(50), nullable=True)
    is_primary = Column(Boolean, default=False)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    contact = relationship("Contact", back_populates="emails")


class ContactPhone(Base):
    __tablename__ = "contact_phones"

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    phone = Column(String(50), nullable=False)
    phone_type = Column(String(50), nullable=True)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    contact = relationship("Contact", back_populates="phones")


class ContactSource(Base):
    __tablename__ = "contact_sources"

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    source_type = Column(String(100), nullable=False)
    source_url = Column(String(500), nullable=True)
    raw_text = Column(Text, nullable=True)
    captured_at = Column(DateTime, default=datetime.utcnow)

    contact = relationship("Contact", back_populates="sources")


class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False, index=True)
    url = Column(String(1000), nullable=True)
    source = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="open")
    discovered_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company")


class OutreachEvent(Base):
    __tablename__ = "outreach_events"

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True)
    channel = Column(String(50), nullable=False)
    direction = Column(String(20), nullable=False)  # inbound / outbound
    subject = Column(String(255), nullable=True)
    message = Column(Text, nullable=True)
    status = Column(String(50), nullable=True)
    sent_at = Column(DateTime, nullable=True)
    response_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)


class Referral(Base):
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="SET NULL"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True)
    referred_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="pending")
    notes = Column(Text, nullable=True)

    contact = relationship("Contact")
    company = relationship("Company")
