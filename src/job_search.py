"""
Job search and filtering functionality.
"""

import random
from typing import List, Dict, Tuple, Set
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.config import Config
from src.logger import get_logger
from src.utils import StealthUtils

logger = get_logger()


class JobSearch:
    """Handles job searching and filtering on LinkedIn."""

    def __init__(self, driver, config: Config):
        """
        Initialize job search.

        Args:
            driver: Selenium WebDriver instance
            config: Configuration object
        """
        self.driver = driver
        self.config = config
        self.wait = WebDriverWait(driver, 30)
        self.applied_job_ids: Set[str] = set()

    def build_search_url(
        self,
        position: str,
        location: str,
        page: int = 0
    ) -> str:
        """
        Build LinkedIn job search URL with ALL filters via URL parameters.
        No UI interaction needed - everything is in the URL.

        Args:
            position: Job position/keyword
            location: Location to search
            page: Page number (25 results per page)

        Returns:
            Complete search URL with all filters applied
        """
        base_url = "https://www.linkedin.com/jobs/search/"

        # Build query parameters
        params = {
            "f_AL": "true",  # Easy Apply filter (always enabled)
            "keywords": position.replace(" ", "%20"),
            "location": location.replace(" ", "%20"),
            "start": str(page * 25)
        }

        # Add Date Posted filter (f_TPR)
        date_filter = self.config.date_posted_filter
        if date_filter and date_filter.lower() != "any":
            date_map = {
                "24h": "r86400",      # Past 24 hours
                "week": "r604800",    # Past week
                "month": "r2592000"   # Past month
            }
            date_value = date_map.get(date_filter.lower())
            if date_value:
                params["f_TPR"] = date_value
                logger.debug(f"Added date filter: {date_filter} -> {date_value}")

        # Add Workplace Type filter (f_WT)
        workplace_types = self.config.workplace_type_filters
        if workplace_types:
            workplace_map = {
                "on-site": "1",
                "onsite": "1",
                "remote": "2",
                "hybrid": "3"
            }
            workplace_values = []
            for wt in workplace_types:
                wt_value = workplace_map.get(wt.lower())
                if wt_value:
                    workplace_values.append(wt_value)
            
            if workplace_values:
                params["f_WT"] = ",".join(workplace_values)
                logger.debug(f"Added workplace filters: {workplace_types} -> {params['f_WT']}")

        # Add Experience Level filter (f_E)
        experience_levels = self.config.experience_level
        if experience_levels:
            exp_map = {
                "internship": "1",
                "entry level": "2",
                "associate": "3",
                "mid-senior level": "4",
                "director": "5",
                "executive": "6"
            }
            exp_values = []
            for exp in experience_levels:
                exp_value = exp_map.get(exp.lower())
                if exp_value:
                    exp_values.append(exp_value)
            
            if exp_values:
                params["f_E"] = ",".join(exp_values)
                logger.debug(f"Added experience filters: {experience_levels} -> {params['f_E']}")

        # Build URL
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        url = f"{base_url}?{query_string}"

        logger.info(f"Built search URL with filters: {url}")
        return url

    def search_jobs(
        self,
        position: str,
        location: str,
        page: int = 0
    ) -> bool:
        """
        Navigate to job search results page with all filters in URL.
        
        All filters are now applied via URL parameters - no UI interaction needed!

        Args:
            position: Job position/keyword
            location: Location to search
            page: Page number

        Returns:
            True if successful, False otherwise
        """
        try:
            url = self.build_search_url(position, location, page)
            logger.info(f"Searching: {position} in {location} (page {page})")

            self.driver.get(url)
            StealthUtils.human_sleep(3, 5)

            # Random scroll to load results
            StealthUtils.random_scroll(self.driver)
            StealthUtils.human_sleep(1, 2)

            return True

        except Exception as e:
            logger.error(f"Failed to search jobs: {e}", exc_info=True)
            return False
    
    def scroll_job_list(self):
        """Scroll through the job list to load all results."""
        try:
            # Find the scrollable job list container
            job_list = self.wait.until(
                EC.presence_of_element_located((
                    By.CLASS_NAME,
                    "jobs-search-results-list"
                ))
            )

            # Scroll gradually to load all jobs
            for scroll_pos in range(300, 3000, 200):
                self.driver.execute_script(
                    f"arguments[0].scrollTo(0, {scroll_pos});",
                    job_list
                )
                StealthUtils.human_sleep(0.3, 0.7)

            logger.debug("Job list scrolled successfully")
            return True

        except Exception as e:
            logger.debug(f"Could not scroll job list: {e}")
            return False

    def get_job_cards(self) -> List[Dict[str, str]]:
        """
        Get all job cards from the current search results.

        Returns:
            List of job dictionaries with id and element
        """
        jobs = []

        try:
            # Scroll to load all jobs
            self.scroll_job_list()
            StealthUtils.human_sleep(1, 2)

            # Find all job card elements
            job_elements = self.driver.find_elements(
                By.XPATH,
                '//div[@data-job-id]'
            )

            logger.info(f"Found {len(job_elements)} job cards")

            for element in job_elements:
                try:
                    job_id = element.get_attribute("data-job-id")

                    # Skip if already applied
                    if job_id in self.applied_job_ids:
                        logger.debug(f"Skipping already applied job: {job_id}")
                        continue

                    # Check if already applied (UI indicator)
                    if "Applied" in element.text:
                        logger.debug(
                            f"Job {job_id} already applied (UI indicator)")
                        self.applied_job_ids.add(job_id)
                        continue

                    # Check blacklist
                    job_text = element.text.lower()
                    if any(
                            company.lower() in job_text for company in self.config.blacklist):
                        logger.debug(f"Job {job_id} in blacklist")
                        continue

                    jobs.append({
                        "id": job_id,
                        "element": element
                    })

                except Exception as e:
                    logger.debug(f"Error processing job card: {e}")
                    continue

            logger.info(f"Collected {len(jobs)} eligible jobs")
            return jobs

        except Exception as e:
            logger.error(f"Failed to get job cards: {e}", exc_info=True)
            return []

    def click_job_card(self, job_id: str) -> bool:
        """
        Click on a job card to view details.

        Args:
            job_id: LinkedIn job ID

        Returns:
            True if successful, False otherwise
        """
        try:
            # First, dismiss any open modals (like "Discard application?" dialog)
            self._dismiss_modals()
            
            # Find and click the job card
            job_card = self.wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    f'//div[@data-job-id="{job_id}"]'
                ))
            )

            StealthUtils.smooth_scroll_to_element(self.driver, job_card)
            StealthUtils.human_sleep(0.5, 1.0)

            job_card.click()
            StealthUtils.human_sleep(2, 3)

            logger.debug(f"Clicked job card: {job_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to click job card {job_id}: {e}")
            return False
    
    def _dismiss_modals(self):
        """Dismiss any open modals that might block interactions."""
        try:
            # Check for discard confirmation modal
            discard_button = self.driver.find_elements(
                By.XPATH,
                '//button[@data-test-dialog-primary-btn or @data-test-modal-close-btn or contains(@aria-label, "Discard")]'
            )
            
            if discard_button:
                discard_button[0].click()
                logger.debug("Dismissed modal dialog")
                StealthUtils.human_sleep(0.5, 1.0)
        except Exception as e:
            logger.debug(f"No modal to dismiss: {e}")

    def get_job_title_and_company(self) -> Tuple[str, str]:
        """
        Get the job title and company name from the current job view using DOM elements.
        
        Scrapes actual elements instead of browser tab title to avoid garbage data.

        Returns:
            Tuple of (job_title, company_name)
        """
        job_title = "Unknown Position"
        company = "Unknown Company"
        
        try:
            # Wait for job details to load
            StealthUtils.human_sleep(1, 2)

            # Try multiple selectors for job title
            title_selectors = [
                ".job-details-jobs-unified-top-card__job-title",
                ".jobs-unified-top-card__job-title",
                "h2.job-title",
                "h1.jobs-unified-top-card__job-title",
                ".jobs-details-top-card__job-title"
            ]
            
            for selector in title_selectors:
                try:
                    title_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if title_elem and title_elem.text.strip():
                        job_title = title_elem.text.strip()
                        logger.debug(f"Found job title using selector: {selector}")
                        break
                except NoSuchElementException:
                    continue
            
            # Try multiple selectors for company name
            company_selectors = [
                ".job-details-jobs-unified-top-card__company-name",
                ".jobs-unified-top-card__company-name",
                ".jobs-unified-top-card__subtitle-primary-grouping .app-aware-link",
                "a.jobs-unified-top-card__company-name",
                ".jobs-details-top-card__company-url"
            ]
            
            for selector in company_selectors:
                try:
                    company_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if company_elem and company_elem.text.strip():
                        company = company_elem.text.strip()
                        logger.debug(f"Found company using selector: {selector}")
                        break
                except NoSuchElementException:
                    continue
            
            # Log what we found
            if job_title != "Unknown Position" and company != "Unknown Company":
                logger.info(f"Scraped job details: {job_title} at {company}")
            else:
                logger.warning(f"Could not scrape complete job details. Title: {job_title}, Company: {company}")
            
            return job_title, company

        except Exception as e:
            logger.error(f"Error extracting job title/company: {e}", exc_info=True)
            return "Unknown Position", "Unknown Company"

    def has_easy_apply_button(self) -> bool:
        """
        Check if the current job has an Easy Apply button.

        Returns:
            True if Easy Apply button exists, False otherwise
        """
        try:
            # Look for Easy Apply button with shorter timeout
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    '//button[contains(@class, "jobs-apply-button") and contains(., "Easy Apply")]'
                ))
            )
            return True

        except TimeoutException:
            logger.debug("Easy Apply button not found")
            return False

    def get_easy_apply_button(self):
        """
        Get the Easy Apply button element.

        Returns:
            WebElement or None
        """
        try:
            button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    '//button[contains(@class, "jobs-apply-button") and contains(., "Easy Apply")]'
                ))
            )
            return button

        except TimeoutException:
            return None
