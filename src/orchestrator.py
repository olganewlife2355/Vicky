"""Main orchestrator for the Vicky recruitment automation pipeline.

Coordinates all modules in the pipeline:
1. Monitor LinkedIn for new job posts
2. Parse client information from posts
3. Generate commercial proposals
4. Send proposals via email/LinkedIn
5. Manage follow-up sequence
6. Book calls for positive responses
7. Send thank-you letters for non-responses
"""

import logging
import time

import schedule

from src.config import settings
from src.models import Base, engine, SessionLocal, Prospect, ProspectStatus
from src.monitors import LinkedInJobMonitor
from src.parsers import ClientInfoParser
from src.proposals import ProposalGenerator
from src.outreach import OutreachSender
from src.followups import FollowUpManager
from src.calendar import CalendarBooking
from src.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


class VickyOrchestrator:
    """Main pipeline orchestrator."""

    def __init__(self):
        setup_logging()
        Base.metadata.create_all(engine)

        self.monitor = LinkedInJobMonitor()
        self.parser = ClientInfoParser()
        self.proposal_gen = ProposalGenerator()
        self.sender = OutreachSender()
        self.followup_mgr = FollowUpManager()
        self.calendar = CalendarBooking()

        logger.info("Vicky Recruitment Automation initialized")

    def run_pipeline(self):
        """Execute one full pipeline cycle."""
        logger.info("=" * 60)
        logger.info("Starting pipeline cycle")
        logger.info("=" * 60)

        # Step 1: Monitor for new job posts
        logger.info("[Step 1] Monitoring LinkedIn for new job posts...")
        new_prospects = self.monitor.monitor_and_collect()
        logger.info("Found %d new prospects", len(new_prospects))

        # Step 2: Parse and enrich client profiles, then send proposals
        session = SessionLocal()
        try:
            pending = session.query(Prospect).filter(
                Prospect.status == ProspectStatus.NEW
            ).all()

            for prospect in pending:
                logger.info("[Step 2] Parsing client: %s at %s",
                           prospect.contact_name, prospect.company_name)
                client_profile = self.parser.parse(prospect)

                logger.info("[Step 3] Generating proposal for %s...",
                           prospect.company_name)
                proposal = self.proposal_gen.generate(client_profile)

                logger.info("[Step 4] Sending proposal to %s...",
                           prospect.contact_name)
                self.sender.send_proposal(prospect, proposal)

        except Exception as e:
            logger.error("Error in proposal pipeline: %s", e)
        finally:
            session.close()

        # Step 5: Check for responses
        logger.info("[Step 5] Checking for responses...")
        self.followup_mgr.check_responses()

        # Step 6: Process follow-ups
        logger.info("[Step 6] Processing follow-ups...")
        self.followup_mgr.process_followups()

        # Step 7: Book calls for positive responses
        logger.info("[Step 7] Booking calls for positive responses...")
        self.calendar.book_calls_for_positive_responses()

        logger.info("Pipeline cycle complete")
        logger.info("=" * 60)

    def run_scheduled(self):
        """Run the pipeline on a recurring schedule."""
        logger.info(
            "Starting scheduled execution every %d minutes",
            settings.MONITOR_INTERVAL_MINUTES,
        )

        # Run immediately, then on schedule
        self.run_pipeline()

        schedule.every(settings.MONITOR_INTERVAL_MINUTES).minutes.do(
            self.run_pipeline
        )

        while True:
            schedule.run_pending()
            time.sleep(60)

    def get_dashboard_stats(self) -> dict:
        """Get summary statistics for the current pipeline state."""
        session = SessionLocal()
        try:
            total = session.query(Prospect).count()
            by_status = {}
            for status in ProspectStatus:
                count = session.query(Prospect).filter(
                    Prospect.status == status
                ).count()
                if count > 0:
                    by_status[status.value] = count

            return {
                "total_prospects": total,
                "by_status": by_status,
            }
        finally:
            session.close()
