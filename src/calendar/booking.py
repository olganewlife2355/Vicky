"""Google Calendar booking integration.

When a prospect responds positively, this module:
- Finds available time slots
- Creates a calendar event with meeting details
- Sends a calendar invite to the prospect
"""

import logging
from datetime import datetime, timedelta, timezone

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from src.config import settings
from src.models import SessionLocal, Prospect, ProspectStatus

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarBooking:
    """Manages calendar booking for positive prospect responses."""

    def __init__(self):
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Google Calendar API using OAuth2."""
        creds = None
        token_path = "token.json"

        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except (FileNotFoundError, ValueError):
            pass

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    settings.GOOGLE_CREDENTIALS_FILE, SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(token_path, "w") as token_file:
                token_file.write(creds.to_json())

        self.service = build("calendar", "v3", credentials=creds)
        logger.info("Google Calendar API authenticated")

    def find_available_slots(self, days_ahead: int = 5,
                              slot_duration_minutes: int = 30) -> list[dict]:
        """Find available time slots in the calendar.

        Args:
            days_ahead: How many days ahead to look.
            slot_duration_minutes: Duration of each slot in minutes.

        Returns:
            List of available slot dicts with 'start' and 'end' datetimes.
        """
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=days_ahead)

        # Get existing events
        events_result = self.service.events().list(
            calendarId=settings.GOOGLE_CALENDAR_ID,
            timeMin=now.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        busy_times = []
        for event in events_result.get("items", []):
            start = event["start"].get("dateTime", event["start"].get("date"))
            end_time = event["end"].get("dateTime", event["end"].get("date"))
            busy_times.append({
                "start": datetime.fromisoformat(start),
                "end": datetime.fromisoformat(end_time),
            })

        # Generate available slots (business hours: 9 AM - 5 PM)
        available = []
        current_day = now.date() + timedelta(days=1)

        for _ in range(days_ahead):
            if current_day.weekday() >= 5:  # Skip weekends
                current_day += timedelta(days=1)
                continue

            for hour in range(9, 17):
                for minute in [0, 30]:
                    slot_start = datetime(
                        current_day.year, current_day.month, current_day.day,
                        hour, minute, tzinfo=timezone.utc
                    )
                    slot_end = slot_start + timedelta(minutes=slot_duration_minutes)

                    # Check if slot overlaps with busy times
                    is_busy = any(
                        slot_start < busy["end"] and slot_end > busy["start"]
                        for busy in busy_times
                    )

                    if not is_busy:
                        available.append({
                            "start": slot_start,
                            "end": slot_end,
                        })

            current_day += timedelta(days=1)

        return available

    def book_call(self, prospect: Prospect,
                  slot: dict | None = None) -> dict | None:
        """Book a discovery call with a prospect.

        If no slot is provided, the first available slot is used.

        Args:
            prospect: Prospect who responded positively.
            slot: Optional specific time slot dict with 'start' and 'end'.

        Returns:
            Created Google Calendar event dict, or None on failure.
        """
        session = SessionLocal()

        try:
            if slot is None:
                available = self.find_available_slots()
                if not available:
                    logger.warning("No available slots for booking with %s",
                                 prospect.contact_name)
                    return None
                slot = available[0]

            event = {
                "summary": (
                    f"Discovery Call — {settings.AGENCY_NAME} & "
                    f"{prospect.company_name}"
                ),
                "description": (
                    f"Recruitment partnership discussion\n\n"
                    f"Company: {prospect.company_name}\n"
                    f"Contact: {prospect.contact_name} "
                    f"({prospect.contact_title})\n"
                    f"Open Role: {prospect.job_title}\n"
                    f"Location: {prospect.job_location}\n\n"
                    f"Agenda:\n"
                    f"1. Company overview and hiring needs\n"
                    f"2. Current recruitment challenges\n"
                    f"3. Our approach and methodology\n"
                    f"4. Partnership terms and next steps"
                ),
                "start": {
                    "dateTime": slot["start"].isoformat(),
                    "timeZone": "UTC",
                },
                "end": {
                    "dateTime": slot["end"].isoformat(),
                    "timeZone": "UTC",
                },
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "email", "minutes": 60},
                        {"method": "popup", "minutes": 15},
                    ],
                },
            }

            # Add attendee if email is available
            if prospect.contact_email:
                event["attendees"] = [
                    {"email": prospect.contact_email},
                    {"email": settings.SMTP_EMAIL},
                ]
                event["conferenceData"] = {
                    "createRequest": {
                        "requestId": f"vicky-{prospect.id}-{int(slot['start'].timestamp())}",
                        "conferenceSolutionKey": {"type": "hangoutsMeet"},
                    }
                }

            created_event = self.service.events().insert(
                calendarId=settings.GOOGLE_CALENDAR_ID,
                body=event,
                conferenceDataVersion=1,
                sendUpdates="all",
            ).execute()

            # Update prospect status
            prospect.status = ProspectStatus.CALL_BOOKED
            prospect.call_scheduled_at = slot["start"]
            session.merge(prospect)
            session.commit()

            logger.info(
                "Call booked with %s at %s on %s. Event: %s",
                prospect.contact_name,
                prospect.company_name,
                slot["start"].strftime("%Y-%m-%d %H:%M UTC"),
                created_event.get("htmlLink", ""),
            )

            return created_event

        except Exception as e:
            session.rollback()
            logger.error("Failed to book call with %s: %s",
                        prospect.contact_name, e)
            return None
        finally:
            session.close()

    def book_calls_for_positive_responses(self):
        """Find all prospects who responded YES and book calls for them."""
        session = SessionLocal()

        try:
            prospects = session.query(Prospect).filter(
                Prospect.status == ProspectStatus.RESPONDED_YES
            ).all()

            for prospect in prospects:
                event = self.book_call(prospect)
                if event:
                    logger.info("Booked call for %s at %s",
                              prospect.contact_name, prospect.company_name)

        except Exception as e:
            logger.error("Error booking calls: %s", e)
        finally:
            session.close()
