"""Commercial proposal generator.

Creates personalized recruitment service proposals based on parsed client
profiles. Uses Jinja2 templates for email body and subject lines.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.config import settings
from src.parsers.client_parser import ClientProfile

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


@dataclass
class Proposal:
    """Generated proposal ready to send."""
    subject: str
    body: str
    client_profile: ClientProfile


class ProposalGenerator:
    """Generates personalized commercial proposals for recruitment services."""

    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(self, client: ClientProfile) -> Proposal:
        """Generate a commercial proposal for a client.

        Args:
            client: Parsed client profile with company and job data.

        Returns:
            Proposal with subject line and email body.
        """
        template = self.env.get_template("proposal_email.html")

        subject = self._generate_subject(client)
        body = template.render(
            client=client,
            agency_name=settings.AGENCY_NAME,
            sender_name=settings.SENDER_NAME,
            sender_title=settings.SENDER_TITLE,
            sender_email=settings.SMTP_EMAIL,
        )

        logger.info("Generated proposal for %s at %s",
                     client.contact_name, client.company_name)

        return Proposal(subject=subject, body=body, client_profile=client)

    def _generate_subject(self, client: ClientProfile) -> str:
        if client.estimated_difficulty == "hard":
            return (
                f"Executive Recruitment Partnership — "
                f"Finding Your Next {client.job_title}"
            )
        return (
            f"Recruitment Support for Your {client.job_title} Opening "
            f"at {client.company_name}"
        )
