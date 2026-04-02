"""Outreach sender module.

Sends commercial proposals and follow-up messages via email (SMTP)
and LinkedIn messaging. Tracks delivery status in the database.
"""

import logging
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from linkedin_api import Linkedin

from src.config import settings
from src.models import SessionLocal, Prospect, Outreach, ProspectStatus
from src.proposals.generator import Proposal

logger = logging.getLogger(__name__)


class OutreachSender:
    """Sends proposals and messages via email and LinkedIn."""

    def __init__(self):
        self.linkedin_api = None

    def _get_linkedin_api(self) -> Linkedin:
        if self.linkedin_api is None:
            self.linkedin_api = Linkedin(
                settings.LINKEDIN_EMAIL,
                settings.LINKEDIN_PASSWORD,
            )
        return self.linkedin_api

    def send_proposal(self, prospect: Prospect, proposal: Proposal) -> bool:
        """Send the initial commercial proposal to a prospect.

        Attempts email first if available, falls back to LinkedIn message.
        Records the outreach in the database and updates prospect status.

        Args:
            prospect: Target prospect record.
            proposal: Generated proposal with subject and body.

        Returns:
            True if sent successfully via at least one channel.
        """
        session = SessionLocal()
        sent = False

        try:
            # Try email first
            if prospect.contact_email:
                sent = self._send_email(
                    to_email=prospect.contact_email,
                    subject=proposal.subject,
                    html_body=proposal.body,
                )
                if sent:
                    self._record_outreach(
                        session, prospect.id, "email",
                        proposal.subject, proposal.body,
                    )

            # Also send via LinkedIn if we have their profile
            if prospect.contact_linkedin_id:
                linkedin_sent = self._send_linkedin_message(
                    profile_urn=prospect.contact_linkedin_id,
                    subject=proposal.subject,
                    message=self._html_to_plain(proposal.body),
                )
                if linkedin_sent:
                    self._record_outreach(
                        session, prospect.id, "linkedin",
                        proposal.subject, proposal.body,
                    )
                    sent = True

            if sent:
                prospect.status = ProspectStatus.PROPOSAL_SENT
                prospect.last_contacted_at = datetime.now(timezone.utc)
                session.merge(prospect)
                session.commit()
                logger.info("Proposal sent to %s at %s",
                           prospect.contact_name, prospect.company_name)
            else:
                logger.warning("Could not send proposal to %s — no valid channel",
                             prospect.contact_name)

        except Exception as e:
            session.rollback()
            logger.error("Error sending proposal to %s: %s",
                        prospect.contact_name, e)
        finally:
            session.close()

        return sent

    def send_followup(self, prospect: Prospect, subject: str,
                      html_body: str, followup_number: int) -> bool:
        """Send a follow-up message to a prospect.

        Args:
            prospect: Target prospect.
            subject: Follow-up email subject.
            html_body: Follow-up HTML body.
            followup_number: Which follow-up this is (1, 2, or 3).

        Returns:
            True if sent successfully.
        """
        session = SessionLocal()
        sent = False

        try:
            if prospect.contact_email:
                sent = self._send_email(
                    to_email=prospect.contact_email,
                    subject=f"Re: {subject}",
                    html_body=html_body,
                )

            if not sent and prospect.contact_linkedin_id:
                sent = self._send_linkedin_message(
                    profile_urn=prospect.contact_linkedin_id,
                    subject=f"Follow-up: {subject}",
                    message=self._html_to_plain(html_body),
                )

            if sent:
                from src.models import FollowUp
                followup = FollowUp(
                    prospect_id=prospect.id,
                    followup_number=followup_number,
                    channel="email" if prospect.contact_email else "linkedin",
                    subject=subject,
                    body=html_body,
                )
                session.add(followup)

                status_map = {
                    1: ProspectStatus.FOLLOWUP_1,
                    2: ProspectStatus.FOLLOWUP_2,
                    3: ProspectStatus.FOLLOWUP_3,
                }
                prospect.status = status_map.get(followup_number, ProspectStatus.FOLLOWUP_3)
                prospect.followup_count = followup_number
                prospect.last_contacted_at = datetime.now(timezone.utc)
                session.merge(prospect)
                session.commit()

                logger.info("Follow-up #%d sent to %s", followup_number,
                           prospect.contact_name)

        except Exception as e:
            session.rollback()
            logger.error("Error sending follow-up to %s: %s",
                        prospect.contact_name, e)
        finally:
            session.close()

        return sent

    def send_thank_you(self, prospect: Prospect, subject: str,
                       html_body: str) -> bool:
        """Send a thank-you / closing letter.

        Args:
            prospect: Target prospect.
            subject: Email subject.
            html_body: HTML body.

        Returns:
            True if sent successfully.
        """
        session = SessionLocal()
        sent = False

        try:
            if prospect.contact_email:
                sent = self._send_email(
                    to_email=prospect.contact_email,
                    subject=subject,
                    html_body=html_body,
                )
            elif prospect.contact_linkedin_id:
                sent = self._send_linkedin_message(
                    profile_urn=prospect.contact_linkedin_id,
                    subject=subject,
                    message=self._html_to_plain(html_body),
                )

            if sent:
                prospect.status = ProspectStatus.THANK_YOU_SENT
                session.merge(prospect)
                session.commit()
                logger.info("Thank-you letter sent to %s", prospect.contact_name)

        except Exception as e:
            session.rollback()
            logger.error("Error sending thank-you to %s: %s",
                        prospect.contact_name, e)
        finally:
            session.close()

        return sent

    def _send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        """Send an email via SMTP."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{settings.SENDER_NAME} <{settings.SMTP_EMAIL}>"
            msg["To"] = to_email

            msg.attach(MIMEText(self._html_to_plain(html_body), "plain"))
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
                server.send_message(msg)

            logger.info("Email sent to %s", to_email)
            return True

        except Exception as e:
            logger.error("Failed to send email to %s: %s", to_email, e)
            return False

    def _send_linkedin_message(self, profile_urn: str, subject: str,
                                message: str) -> bool:
        """Send a LinkedIn InMail/message."""
        try:
            api = self._get_linkedin_api()
            api.send_message(
                message_body=f"{subject}\n\n{message}",
                recipients=[profile_urn],
            )
            logger.info("LinkedIn message sent to %s", profile_urn)
            return True
        except Exception as e:
            logger.error("Failed to send LinkedIn message to %s: %s",
                        profile_urn, e)
            return False

    @staticmethod
    def _html_to_plain(html: str) -> str:
        """Simple HTML to plain-text conversion."""
        import re
        text = re.sub(r'<br\s*/?>', '\n', html)
        text = re.sub(r'<li>', '• ', text)
        text = re.sub(r'</li>', '\n', text)
        text = re.sub(r'<p>', '\n', text)
        text = re.sub(r'</p>', '\n', text)
        text = re.sub(r'<strong>', '', text)
        text = re.sub(r'</strong>', '', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    @staticmethod
    def _record_outreach(session, prospect_id: int, channel: str,
                         subject: str, body: str):
        outreach = Outreach(
            prospect_id=prospect_id,
            channel=channel,
            subject=subject,
            body=body,
            delivered=True,
        )
        session.add(outreach)
