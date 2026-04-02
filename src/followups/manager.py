"""Follow-up manager.

Handles the automated follow-up sequence:
- Tracks which prospects need follow-ups based on timing
- Generates and sends follow-up messages (up to 3)
- Monitors for responses and updates prospect status
- Triggers thank-you letters after 3rd follow-up with no response
"""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.config import settings
from src.models import SessionLocal, Prospect, ProspectStatus
from src.outreach.sender import OutreachSender
from src.parsers.client_parser import ClientInfoParser

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class FollowUpManager:
    """Manages the follow-up sequence for all active prospects."""

    def __init__(self):
        self.sender = OutreachSender()
        self.parser = ClientInfoParser()
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def process_followups(self):
        """Check all prospects and send follow-ups where due.

        This is the main method called by the scheduler. It:
        1. Finds prospects needing follow-ups (based on time elapsed)
        2. Sends the appropriate follow-up message
        3. Sends thank-you letters for prospects past the 3rd follow-up
        """
        session = SessionLocal()

        try:
            now = datetime.now(timezone.utc)
            interval = timedelta(days=settings.FOLLOWUP_INTERVAL_DAYS)

            # Prospects that need follow-ups
            followup_statuses = [
                ProspectStatus.PROPOSAL_SENT,
                ProspectStatus.FOLLOWUP_1,
                ProspectStatus.FOLLOWUP_2,
            ]

            prospects = session.query(Prospect).filter(
                Prospect.status.in_(followup_statuses),
                Prospect.last_contacted_at <= now - interval,
            ).all()

            for prospect in prospects:
                next_followup = prospect.followup_count + 1

                if next_followup > settings.MAX_FOLLOWUPS:
                    self._send_thank_you(prospect)
                    continue

                self._send_followup(prospect, next_followup)

            # Handle prospects stuck at followup_3 with no response
            stale_prospects = session.query(Prospect).filter(
                Prospect.status == ProspectStatus.FOLLOWUP_3,
                Prospect.last_contacted_at <= now - interval,
            ).all()

            for prospect in stale_prospects:
                self._send_thank_you(prospect)

            session.commit()

        except Exception as e:
            session.rollback()
            logger.error("Error processing follow-ups: %s", e)
        finally:
            session.close()

    def check_responses(self):
        """Check LinkedIn messages and email for responses from prospects.

        Updates prospect status based on detected responses.
        """
        session = SessionLocal()

        try:
            active_statuses = [
                ProspectStatus.PROPOSAL_SENT,
                ProspectStatus.FOLLOWUP_1,
                ProspectStatus.FOLLOWUP_2,
                ProspectStatus.FOLLOWUP_3,
            ]

            prospects = session.query(Prospect).filter(
                Prospect.status.in_(active_statuses)
            ).all()

            for prospect in prospects:
                response = self._check_linkedin_response(prospect)
                if response:
                    self._handle_response(session, prospect, response)

            session.commit()

        except Exception as e:
            session.rollback()
            logger.error("Error checking responses: %s", e)
        finally:
            session.close()

    def _send_followup(self, prospect: Prospect, followup_number: int):
        """Generate and send a specific follow-up message."""
        client = self.parser.parse(prospect)

        template_name = f"followup_{followup_number}.html"
        template = self.env.get_template(template_name)

        body = template.render(
            client=client,
            agency_name=settings.AGENCY_NAME,
            sender_name=settings.SENDER_NAME,
            sender_title=settings.SENDER_TITLE,
        )

        subject = (
            f"Following up: Recruitment Support for "
            f"{prospect.job_title} at {prospect.company_name}"
        )

        self.sender.send_followup(prospect, subject, body, followup_number)
        logger.info("Sent follow-up #%d to %s at %s",
                     followup_number, prospect.contact_name, prospect.company_name)

    def _send_thank_you(self, prospect: Prospect):
        """Send a thank-you / closing letter."""
        client = self.parser.parse(prospect)

        template = self.env.get_template("thank_you.html")
        body = template.render(
            client=client,
            agency_name=settings.AGENCY_NAME,
            sender_name=settings.SENDER_NAME,
            sender_title=settings.SENDER_TITLE,
            sender_email=settings.SMTP_EMAIL,
        )

        subject = (
            f"Thank you — {prospect.company_name} & {settings.AGENCY_NAME}"
        )

        self.sender.send_thank_you(prospect, subject, body)
        logger.info("Sent thank-you letter to %s at %s",
                     prospect.contact_name, prospect.company_name)

    def _check_linkedin_response(self, prospect: Prospect) -> dict | None:
        """Check if a prospect has replied via LinkedIn."""
        try:
            from linkedin_api import Linkedin
            api = Linkedin(settings.LINKEDIN_EMAIL, settings.LINKEDIN_PASSWORD)

            conversations = api.get_conversations()
            for convo in conversations.get("elements", []):
                participants = convo.get("participants", [])
                for participant in participants:
                    profile_id = (
                        participant
                        .get("com.linkedin.voyager.messaging.MessagingMember", {})
                        .get("miniProfile", {})
                        .get("publicIdentifier", "")
                    )
                    if profile_id and profile_id in (
                        prospect.contact_linkedin_id or ""
                    ):
                        last_msg = convo.get("lastMessage", {})
                        if last_msg and not last_msg.get("fromMe", True):
                            return {
                                "text": last_msg.get("body", ""),
                                "from": profile_id,
                            }
        except Exception as e:
            logger.warning("Could not check LinkedIn responses: %s", e)

        return None

    def _handle_response(self, session, prospect: Prospect, response: dict):
        """Process a prospect's response and update status."""
        text = response.get("text", "").lower()

        positive_signals = [
            "yes", "sure", "interested", "let's talk", "sounds good",
            "schedule", "call", "meet", "available", "book",
        ]
        negative_signals = [
            "no thank", "not interested", "no need", "pass",
            "already filled", "not looking", "decline",
        ]

        if any(signal in text for signal in positive_signals):
            prospect.status = ProspectStatus.RESPONDED_YES
            prospect.responded_at = datetime.now(timezone.utc)
            session.merge(prospect)
            logger.info("POSITIVE response from %s at %s!",
                       prospect.contact_name, prospect.company_name)

        elif any(signal in text for signal in negative_signals):
            prospect.status = ProspectStatus.RESPONDED_NO
            prospect.responded_at = datetime.now(timezone.utc)
            session.merge(prospect)
            logger.info("Negative response from %s at %s",
                       prospect.contact_name, prospect.company_name)
            self._send_thank_you(prospect)
