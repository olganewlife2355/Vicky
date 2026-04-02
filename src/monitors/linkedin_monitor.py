"""LinkedIn job posts monitoring module.

Monitors LinkedIn for new job postings that match target keywords and industries.
Extracts post data and creates prospect records for the recruitment pipeline.
"""

import logging
import time
from datetime import datetime, timezone

from linkedin_api import Linkedin

from src.config import settings
from src.models import SessionLocal, Prospect, ProspectStatus

logger = logging.getLogger(__name__)


class LinkedInJobMonitor:
    """Monitors LinkedIn for job role posts from potential recruitment clients."""

    def __init__(self):
        self.api = None
        self._connect()

    def _connect(self):
        """Authenticate with LinkedIn API."""
        try:
            self.api = Linkedin(
                settings.LINKEDIN_EMAIL,
                settings.LINKEDIN_PASSWORD,
            )
            logger.info("Successfully connected to LinkedIn API")
        except Exception as e:
            logger.error("Failed to connect to LinkedIn: %s", e)
            raise

    def search_job_posts(self, keywords: list[str] | None = None) -> list[dict]:
        """Search LinkedIn for job posts matching configured keywords.

        Args:
            keywords: Override default search keywords.

        Returns:
            List of raw job post data dictionaries.
        """
        keywords = keywords or settings.SEARCH_KEYWORDS
        all_results = []

        for keyword in keywords:
            try:
                logger.info("Searching LinkedIn for: '%s'", keyword)
                jobs = self.api.search_jobs(
                    keywords=keyword,
                    limit=25,
                )
                all_results.extend(jobs)
                time.sleep(2)  # Rate limiting
            except Exception as e:
                logger.error("Error searching for '%s': %s", keyword, e)

        # Deduplicate by job tracking ID
        seen = set()
        unique_results = []
        for job in all_results:
            tracking_id = job.get("dashEntityUrn", job.get("entityUrn", ""))
            if tracking_id and tracking_id not in seen:
                seen.add(tracking_id)
                unique_results.append(job)

        logger.info("Found %d unique job posts", len(unique_results))
        return unique_results

    def get_job_details(self, job_id: str) -> dict:
        """Fetch full details for a specific job posting.

        Args:
            job_id: LinkedIn job ID.

        Returns:
            Complete job posting data.
        """
        try:
            details = self.api.get_job(job_id)
            time.sleep(1)  # Rate limiting
            return details
        except Exception as e:
            logger.error("Error fetching job details for %s: %s", job_id, e)
            return {}

    def get_company_info(self, company_urn: str) -> dict:
        """Fetch company profile information.

        Args:
            company_urn: LinkedIn company URN identifier.

        Returns:
            Company profile data.
        """
        try:
            company_id = company_urn.split(":")[-1]
            company = self.api.get_company(company_id)
            time.sleep(1)
            return company
        except Exception as e:
            logger.error("Error fetching company info for %s: %s", company_urn, e)
            return {}

    def get_poster_profile(self, profile_urn: str) -> dict:
        """Fetch the profile of the person who posted the job.

        Args:
            profile_urn: LinkedIn profile URN.

        Returns:
            Profile data for the job poster.
        """
        try:
            profile_id = profile_urn.split(":")[-1]
            profile = self.api.get_profile(profile_id)
            time.sleep(1)
            return profile
        except Exception as e:
            logger.error("Error fetching profile for %s: %s", profile_urn, e)
            return {}

    def search_company_hr_contacts(self, company_name: str) -> list[dict]:
        """Search for HR/recruiting decision-makers at a company.

        Args:
            company_name: Name of the target company.

        Returns:
            List of potential HR contact profiles.
        """
        hr_titles = ["HR Director", "HR Manager", "Head of Talent",
                      "Talent Acquisition", "Recruiting Manager",
                      "VP Human Resources", "People Operations"]
        contacts = []

        for title in hr_titles:
            try:
                results = self.api.search_people(
                    keywords=f"{title} {company_name}",
                    limit=5,
                )
                contacts.extend(results)
                time.sleep(2)
            except Exception as e:
                logger.warning("Error searching for %s at %s: %s",
                             title, company_name, e)

        # Deduplicate
        seen = set()
        unique_contacts = []
        for contact in contacts:
            urn = contact.get("urn_id", "")
            if urn and urn not in seen:
                seen.add(urn)
                unique_contacts.append(contact)

        return unique_contacts

    def monitor_and_collect(self) -> list[Prospect]:
        """Run a full monitoring cycle: search, extract, and store new prospects.

        Returns:
            List of newly created Prospect records.
        """
        new_prospects = []
        session = SessionLocal()

        try:
            job_posts = self.search_job_posts()

            for job in job_posts:
                job_url = self._extract_job_url(job)

                # Skip if already tracked
                existing = session.query(Prospect).filter_by(
                    linkedin_post_url=job_url
                ).first()
                if existing:
                    logger.debug("Already tracking: %s", job_url)
                    continue

                # Get detailed info
                job_id = self._extract_job_id(job)
                details = self.get_job_details(job_id) if job_id else {}

                company_urn = job.get("companyUrn", "")
                company_info = self.get_company_info(company_urn) if company_urn else {}

                # Find HR contacts
                company_name = (
                    details.get("companyDetails", {})
                    .get("company", {})
                    .get("name", "")
                ) or company_info.get("name", "")

                hr_contacts = self.search_company_hr_contacts(company_name) if company_name else []
                primary_contact = hr_contacts[0] if hr_contacts else {}

                prospect = Prospect(
                    linkedin_post_url=job_url,
                    linkedin_profile_url=primary_contact.get("public_id", ""),
                    contact_name=self._format_name(primary_contact),
                    contact_title=primary_contact.get("jobtitle", "HR Manager"),
                    contact_email=primary_contact.get("email", ""),
                    contact_linkedin_id=primary_contact.get("urn_id", ""),
                    company_name=company_name,
                    company_industry=company_info.get("companyIndustries", [{}])[0].get(
                        "localizedName", ""
                    ) if company_info.get("companyIndustries") else "",
                    company_size=self._parse_company_size(company_info),
                    company_location=company_info.get("headquarter", {}).get(
                        "geographicArea", ""
                    ) if company_info.get("headquarter") else "",
                    company_website=company_info.get("companyPageUrl", ""),
                    job_title=details.get("title", job.get("title", "")),
                    job_description=details.get("description", {}).get("text", ""),
                    job_location=details.get("formattedLocation", ""),
                    job_type=details.get("employmentStatus", ""),
                    status=ProspectStatus.NEW,
                )

                session.add(prospect)
                new_prospects.append(prospect)
                logger.info("New prospect: %s at %s", prospect.job_title, prospect.company_name)

            session.commit()
            logger.info("Monitoring cycle complete: %d new prospects", len(new_prospects))

        except Exception as e:
            session.rollback()
            logger.error("Error during monitoring cycle: %s", e)
            raise
        finally:
            session.close()

        return new_prospects

    @staticmethod
    def _extract_job_url(job: dict) -> str:
        entity_urn = job.get("dashEntityUrn", job.get("entityUrn", ""))
        job_id = entity_urn.split(":")[-1] if entity_urn else ""
        return f"https://www.linkedin.com/jobs/view/{job_id}/" if job_id else ""

    @staticmethod
    def _extract_job_id(job: dict) -> str:
        entity_urn = job.get("dashEntityUrn", job.get("entityUrn", ""))
        return entity_urn.split(":")[-1] if entity_urn else ""

    @staticmethod
    def _format_name(profile: dict) -> str:
        first = profile.get("firstName", "")
        last = profile.get("lastName", "")
        return f"{first} {last}".strip() or "Hiring Manager"

    @staticmethod
    def _parse_company_size(company_info: dict) -> str:
        staff_range = company_info.get("staffCountRange", {})
        if staff_range:
            start = staff_range.get("start", 0)
            end = staff_range.get("end", "")
            return f"{start}-{end}" if end else f"{start}+"
        return ""
