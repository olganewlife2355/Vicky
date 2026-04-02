# Vicky — LinkedIn Recruitment Automation

Automated pipeline that monitors LinkedIn job posts, identifies potential clients for recruitment agencies, generates and sends commercial proposals, manages follow-ups, and books discovery calls.

## Pipeline Flow

```
LinkedIn Job Posts → Parse Client Info → Generate Proposal → Send Outreach
                                                                    ↓
                                              Monitor Responses ← Wait
                                                    ↓
                                    ┌───── Response? ─────┐
                                    │                     │
                                   YES                    NO
                                    │                     │
                              Book Call            Send Follow-up (×3)
                              in Calendar                 │
                                                   No response after 3?
                                                          │
                                                   Send Thank You
```

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Google Calendar (optional):**
   - Create a Google Cloud project with Calendar API enabled
   - Download `credentials.json` to project root
   - First run will open browser for OAuth consent

## Usage

```bash
# Run one full pipeline cycle
python main.py run

# Start continuous monitoring (runs every N minutes)
python main.py monitor

# Process pending follow-ups only
python main.py followups

# Book calls for positive responses
python main.py book

# View pipeline dashboard
python main.py status
```

## Configuration

All settings are in `.env`. Key options:

| Variable | Description |
|---|---|
| `LINKEDIN_EMAIL` | LinkedIn login email |
| `LINKEDIN_PASSWORD` | LinkedIn login password |
| `SMTP_EMAIL` | Email for sending proposals |
| `AGENCY_NAME` | Your recruitment agency name |
| `MONITOR_INTERVAL_MINUTES` | How often to check for new posts |
| `MAX_FOLLOWUPS` | Number of follow-ups before closing (default: 3) |
| `FOLLOWUP_INTERVAL_DAYS` | Days between follow-ups (default: 3) |

## Architecture

```
src/
├── monitors/       # LinkedIn job post monitoring
├── parsers/        # Client info extraction & enrichment
├── proposals/      # Commercial proposal generation
├── outreach/       # Email & LinkedIn message sending
├── followups/      # Follow-up sequence management
├── calendar/       # Google Calendar booking
├── templates/      # Email templates (Jinja2)
├── models/         # SQLAlchemy database models
├── utils/          # Logging and helpers
├── config.py       # Environment configuration
└── orchestrator.py # Main pipeline coordinator
```
