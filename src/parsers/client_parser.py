"""Client information parser.

Enriches prospect records by extracting and normalizing data from LinkedIn
profiles, company pages, and job posts into structured client profiles
for commercial proposal generation.
"""

import logging
import re
from dataclasses import dataclass, field

from src.models import Prospect

logger = logging.getLogger(__name__)


@dataclass
class ClientProfile:
    """Structured client profile for proposal generation."""

    # Contact
    contact_name: str = ""
    contact_title: str = ""
    contact_email: str = ""
    contact_linkedin_url: str = ""

    # Company
    company_name: str = ""
    company_industry: str = ""
    company_size: str = ""
    company_location: str = ""
    company_website: str = ""

    # Hiring need
    job_title: str = ""
    job_description_summary: str = ""
    job_location: str = ""
    job_type: str = ""
    seniority_level: str = ""
    estimated_difficulty: str = ""  # easy, medium, hard

    # Derived insights
    key_requirements: list[str] = field(default_factory=list)
    industry_challenges: list[str] = field(default_factory=list)
    proposed_services: list[str] = field(default_factory=list)


class ClientInfoParser:
    """Parses and enriches prospect data into structured client profiles."""

    SENIORITY_KEYWORDS = {
        "executive": ["ceo", "cto", "cfo", "coo", "vp", "vice president",
                       "chief", "director", "head of", "president"],
        "senior": ["senior", "sr.", "lead", "principal", "staff", "architect"],
        "mid": ["manager", "specialist", "analyst", "engineer", "developer"],
        "junior": ["junior", "jr.", "associate", "entry", "intern", "trainee"],
    }

    DIFFICULTY_MAP = {
        "executive": "hard",
        "senior": "hard",
        "mid": "medium",
        "junior": "easy",
    }

    INDUSTRY_CHALLENGES = {
        "technology": [
            "High competition for tech talent",
            "Rapid skill obsolescence",
            "Remote work expectations",
        ],
        "finance": [
            "Strict regulatory compliance requirements",
            "Competitive compensation packages",
            "Specialized certifications needed",
        ],
        "healthcare": [
            "Licensing and certification requirements",
            "Shift-based scheduling challenges",
            "Burnout and retention issues",
        ],
        "manufacturing": [
            "Skilled trades shortage",
            "Safety certification requirements",
            "Location-dependent talent pools",
        ],
    }

    SERVICE_RECOMMENDATIONS = {
        "easy": [
            "Candidate sourcing and screening",
            "Job posting optimization",
            "Interview coordination",
        ],
        "medium": [
            "Executive-level sourcing strategies",
            "Competency-based assessment",
            "Market salary benchmarking",
            "Candidate pipeline management",
        ],
        "hard": [
            "Executive search and headhunting",
            "Confidential candidate approach",
            "Compensation package consulting",
            "Employer branding advisory",
            "Retained search partnership",
        ],
    }

    def parse(self, prospect: Prospect) -> ClientProfile:
        """Parse a Prospect record into a structured ClientProfile.

        Args:
            prospect: Database prospect record.

        Returns:
            Enriched ClientProfile for proposal generation.
        """
        profile = ClientProfile(
            contact_name=prospect.contact_name or "Hiring Manager",
            contact_title=prospect.contact_title or "",
            contact_email=prospect.contact_email or "",
            contact_linkedin_url=self._build_linkedin_url(prospect.linkedin_profile_url),
            company_name=prospect.company_name or "",
            company_industry=prospect.company_industry or "",
            company_size=prospect.company_size or "",
            company_location=prospect.company_location or "",
            company_website=prospect.company_website or "",
            job_title=prospect.job_title or "",
            job_description_summary=self._summarize_description(
                prospect.job_description or ""
            ),
            job_location=prospect.job_location or "",
            job_type=prospect.job_type or "Full-time",
        )

        profile.seniority_level = self._detect_seniority(profile.job_title)
        profile.estimated_difficulty = self.DIFFICULTY_MAP.get(
            profile.seniority_level, "medium"
        )
        profile.key_requirements = self._extract_requirements(
            prospect.job_description or ""
        )
        profile.industry_challenges = self._get_industry_challenges(
            profile.company_industry
        )
        profile.proposed_services = self.SERVICE_RECOMMENDATIONS.get(
            profile.estimated_difficulty, self.SERVICE_RECOMMENDATIONS["medium"]
        )

        logger.info(
            "Parsed client profile: %s at %s (seniority=%s, difficulty=%s)",
            profile.contact_name,
            profile.company_name,
            profile.seniority_level,
            profile.estimated_difficulty,
        )

        return profile

    def _detect_seniority(self, job_title: str) -> str:
        title_lower = job_title.lower()
        for level, keywords in self.SENIORITY_KEYWORDS.items():
            if any(kw in title_lower for kw in keywords):
                return level
        return "mid"

    def _summarize_description(self, description: str, max_sentences: int = 3) -> str:
        if not description:
            return ""
        sentences = re.split(r'(?<=[.!?])\s+', description.strip())
        return " ".join(sentences[:max_sentences])

    def _extract_requirements(self, description: str) -> list[str]:
        requirements = []
        lines = description.split("\n")
        capture = False

        for line in lines:
            line = line.strip()
            lower = line.lower()

            if any(kw in lower for kw in ["requirement", "qualif", "must have",
                                            "what you need", "skills"]):
                capture = True
                continue

            if capture:
                if line.startswith(("-", "•", "*", "·")) or re.match(r'^\d+[.)]\s', line):
                    cleaned = re.sub(r'^[-•*·\d.)]+\s*', '', line).strip()
                    if cleaned:
                        requirements.append(cleaned)
                elif line == "":
                    if requirements:
                        capture = False

        return requirements[:10]

    def _get_industry_challenges(self, industry: str) -> list[str]:
        industry_lower = industry.lower()
        for key, challenges in self.INDUSTRY_CHALLENGES.items():
            if key in industry_lower:
                return challenges
        return ["Competitive talent market", "Need for specialized skills"]

    @staticmethod
    def _build_linkedin_url(profile_id: str) -> str:
        if not profile_id:
            return ""
        if profile_id.startswith("http"):
            return profile_id
        return f"https://www.linkedin.com/in/{profile_id}/"
