#!/usr/bin/env python3
"""Vicky — LinkedIn Recruitment Automation CLI.

Usage:
    python main.py run          Run one full pipeline cycle
    python main.py monitor      Start continuous monitoring (scheduled)
    python main.py followups    Process pending follow-ups only
    python main.py book         Book calls for positive responses only
    python main.py status       Show pipeline dashboard / stats
"""

import sys
import logging

from src.orchestrator import VickyOrchestrator
from src.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


def print_usage():
    print(__doc__)


def cmd_run(orchestrator: VickyOrchestrator):
    """Run one full pipeline cycle."""
    orchestrator.run_pipeline()


def cmd_monitor(orchestrator: VickyOrchestrator):
    """Start continuous scheduled monitoring."""
    orchestrator.run_scheduled()


def cmd_followups(orchestrator: VickyOrchestrator):
    """Process follow-ups only."""
    orchestrator.followup_mgr.check_responses()
    orchestrator.followup_mgr.process_followups()
    logger.info("Follow-up processing complete")


def cmd_book(orchestrator: VickyOrchestrator):
    """Book calls for positive responses."""
    orchestrator.calendar.book_calls_for_positive_responses()
    logger.info("Call booking complete")


def cmd_status(orchestrator: VickyOrchestrator):
    """Show pipeline stats."""
    stats = orchestrator.get_dashboard_stats()
    print("\n=== Vicky Recruitment Pipeline Dashboard ===\n")
    print(f"  Total prospects: {stats['total_prospects']}")
    print()

    if stats["by_status"]:
        print("  Status breakdown:")
        for status, count in stats["by_status"].items():
            print(f"    {status:25s} {count}")
    else:
        print("  No prospects yet. Run 'python main.py run' to start monitoring.")

    print()


COMMANDS = {
    "run": cmd_run,
    "monitor": cmd_monitor,
    "followups": cmd_followups,
    "book": cmd_book,
    "status": cmd_status,
}


def main():
    setup_logging()

    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print_usage()
        sys.exit(1)

    command = sys.argv[1]
    logger.info("Vicky starting — command: %s", command)

    orchestrator = VickyOrchestrator()
    COMMANDS[command](orchestrator)


if __name__ == "__main__":
    main()
