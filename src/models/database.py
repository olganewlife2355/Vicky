"""Database models for tracking prospects, outreach, and follow-ups."""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from src.config import settings

Base = declarative_base()
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


class ProspectStatus(str, enum.Enum):
    NEW = "new"
    PROPOSAL_SENT = "proposal_sent"
    FOLLOWUP_1 = "followup_1"
    FOLLOWUP_2 = "followup_2"
    FOLLOWUP_3 = "followup_3"
    RESPONDED_YES = "responded_yes"
    RESPONDED_NO = "responded_no"
    CALL_BOOKED = "call_booked"
    THANK_YOU_SENT = "thank_you_sent"
    CLOSED = "closed"


class Prospect(Base):
    __tablename__ = "prospects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    linkedin_post_url = Column(String(500), unique=True, nullable=False)
    linkedin_profile_url = Column(String(500))

    # Contact info
    contact_name = Column(String(200))
    contact_title = Column(String(200))
    contact_email = Column(String(200))
    contact_linkedin_id = Column(String(200))

    # Company info
    company_name = Column(String(300))
    company_industry = Column(String(200))
    company_size = Column(String(100))
    company_location = Column(String(300))
    company_website = Column(String(500))

    # Job post info
    job_title = Column(String(300))
    job_description = Column(Text)
    job_location = Column(String(300))
    job_type = Column(String(100))  # full-time, contract, etc.

    # Tracking
    status = Column(Enum(ProspectStatus), default=ProspectStatus.NEW)
    followup_count = Column(Integer, default=0)
    last_contacted_at = Column(DateTime)
    next_followup_at = Column(DateTime)
    responded_at = Column(DateTime)
    call_scheduled_at = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    outreach_messages = relationship("Outreach", back_populates="prospect")
    followups = relationship("FollowUp", back_populates="prospect")

    def __repr__(self):
        return f"<Prospect {self.company_name} - {self.job_title} ({self.status.value})>"


class Outreach(Base):
    __tablename__ = "outreach"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prospect_id = Column(Integer, ForeignKey("prospects.id"), nullable=False)
    channel = Column(String(50))  # email, linkedin
    subject = Column(String(500))
    body = Column(Text)
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    delivered = Column(Boolean, default=False)
    opened = Column(Boolean, default=False)
    replied = Column(Boolean, default=False)

    prospect = relationship("Prospect", back_populates="outreach_messages")

    def __repr__(self):
        return f"<Outreach to {self.prospect_id} via {self.channel}>"


class FollowUp(Base):
    __tablename__ = "followups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prospect_id = Column(Integer, ForeignKey("prospects.id"), nullable=False)
    followup_number = Column(Integer, nullable=False)
    channel = Column(String(50))
    subject = Column(String(500))
    body = Column(Text)
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    replied = Column(Boolean, default=False)

    prospect = relationship("Prospect", back_populates="followups")

    def __repr__(self):
        return f"<FollowUp #{self.followup_number} to {self.prospect_id}>"
