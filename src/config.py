"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


def _parse_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass
class Settings:
    # LinkedIn
    LINKEDIN_EMAIL: str = os.getenv("LINKEDIN_EMAIL", "")
    LINKEDIN_PASSWORD: str = os.getenv("LINKEDIN_PASSWORD", "")

    # SMTP / Email
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_EMAIL: str = os.getenv("SMTP_EMAIL", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SENDER_NAME: str = os.getenv("SENDER_NAME", "")
    SENDER_TITLE: str = os.getenv("SENDER_TITLE", "Business Development Manager")
    AGENCY_NAME: str = os.getenv("AGENCY_NAME", "")

    # Google Calendar
    GOOGLE_CREDENTIALS_FILE: str = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    GOOGLE_CALENDAR_ID: str = os.getenv("GOOGLE_CALENDAR_ID", "primary")

    # Monitoring
    MONITOR_INTERVAL_MINUTES: int = int(os.getenv("MONITOR_INTERVAL_MINUTES", "30"))
    MAX_FOLLOWUPS: int = int(os.getenv("MAX_FOLLOWUPS", "3"))
    FOLLOWUP_INTERVAL_DAYS: int = int(os.getenv("FOLLOWUP_INTERVAL_DAYS", "3"))

    # Search
    SEARCH_KEYWORDS: list[str] = field(default_factory=lambda: _parse_list(
        os.getenv("LINKEDIN_SEARCH_KEYWORDS",
                   "hiring,recruiting,looking for,open position,job opening")
    ))
    TARGET_INDUSTRIES: list[str] = field(default_factory=lambda: _parse_list(
        os.getenv("LINKEDIN_TARGET_INDUSTRIES",
                   "technology,finance,healthcare,manufacturing")
    ))

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///vicky.db")


settings = Settings()
