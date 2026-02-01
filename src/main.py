"""
Main entry point for LinkedIn Easy Apply Bot.
"""

import argparse
import random
import sys
import time
from pathlib import Path
from typing import List, Dict

from src.config import Config
from src.logger import get_logger
from src.bot import LinkedInBot
from src.job_search import JobSearch
from src.application import JobApplication, DailyLimitReachedException
from src.utils import StealthUtils

logger = get_logger()


class LinkedInEasyApplyBot:
    """Main orchestrator for the LinkedIn Easy Apply Bot."""

    def __init__(
            self,
            config_file: str = "config.yaml",
            dry_run: bool = False,
            headless: bool = False):
        """
        Initialize the bot.

        Args:
            config_file: Path to configuration file
            dry_run: If True, simulate applications without submitting
            headless: If True, run browser in headless mode
        """
        self.dry_run = dry_run
        self.headless = headless

        logger.info("=" * 80)
        logger.info("LinkedIn Easy Apply Bot v2.0")
        logger.info("=" * 80)

        if dry_run:
            logger.info(
                "🔵 DRY RUN MODE: Applications will be simulated (not submitted)")

        # Load configuration
        self.config = Config(config_file)
        self.config.log_config_summary()

        # Initialize components
        self.bot: LinkedInBot = None
        self.job_search: JobSearch = None
        self.application: JobApplication = None

        # Statistics
        self.stats = {
            "jobs_found": 0,
            "jobs_attempted": 0,
            "jobs_applied": 0,
            "jobs_failed": 0
        }

    def run(self):
        """Main execution method."""
        try:
            # Initialize bot and login
            self.bot = LinkedInBot(self.config, headless=self.headless)

            if not self.bot.login():
                logger.critical("Failed to login to LinkedIn")
                return

            # Initialize job search and application components
            self.job_search = JobSearch(self.bot.driver, self.config)
            self.application = JobApplication(
                self.bot.driver, self.config, dry_run=self.dry_run)

            # Navigate to jobs page
            self.bot.navigate_to_jobs()

            # Start job search and application loop
            self._application_loop()

            # Print final statistics
            self._print_statistics()

        except DailyLimitReachedException:
            logger.warning("\n⛔ Bot stopped: LinkedIn daily application limit reached")
            logger.warning("This is normal behavior to avoid appearing suspicious.")
            logger.warning("Please run the bot again tomorrow (after 24 hours).")
            self._print_statistics()
        except KeyboardInterrupt:
            logger.warning("\n⚠️  Process interrupted by user")
            self._print_statistics()
        except Exception as e:
            logger.critical(f"Fatal error: {e}", exc_info=True)
        finally:
            if self.bot:
                self.bot.close()

    def _application_loop(self):
        """
        Main loop for searching and applying to jobs with URL-based filters.
        
        NEW STRATEGY (URL PARAMETERS):
        All filters are now applied via URL parameters:
        - Experience Level (Associate, Mid-Senior, etc.)
        - Workplace Type (Remote, Hybrid, On-site)
        - Date Posted (24h, week, month)
        
        No UI interaction needed - filters are embedded in the search URL!
        """
        logger.info("=" * 80)
        logger.info("Starting job application loop with URL-BASED FILTERS...")
        logger.info("=" * 80)

        start_time = time.time()
        max_search_time = self.config.max_search_time

        # Get positions and locations
        positions = self.config.positions
        locations = self.config.locations

        logger.info(f"Positions to search: {len(positions)}")
        logger.info(f"Locations to search: {len(locations)}")
        logger.info(f"Total combinations: {len(positions) * len(locations)}")
        logger.info(f"Filters: Date={self.config.date_posted_filter}, "
                   f"Workplace={self.config.workplace_type_filters}, "
                   f"Experience={self.config.experience_level}")
        logger.info("=" * 80)

        # Loop through search combinations
        for position_idx, position in enumerate(positions, 1):
            for location_idx, location in enumerate(locations, 1):
                # Check if we've exceeded max search time
                elapsed = time.time() - start_time
                if elapsed > max_search_time:
                    logger.info(
                        f"Max search time reached ({max_search_time / 60:.1f} minutes)")
                    return

                remaining = (max_search_time - elapsed) / 60
                logger.info("\n" + "=" * 80)
                logger.info(f"🔍 SEARCH {position_idx}/{len(positions)} x {location_idx}/{len(locations)}")
                logger.info(f"Position: {position}")
                logger.info(f"Location: {location}")
                logger.info(f"⏱️  Remaining: {remaining:.1f} min")
                logger.info("=" * 80)

                # Search and apply (all filters in URL)
                self._search_and_apply_with_filters(position, location)

                # Random delay between searches
                logger.info("Waiting before next search...")
                StealthUtils.human_sleep(5, 10)

    def _search_and_apply_with_filters(self, position: str, location: str):
        """
        Search for jobs and process them with URL-based filters.
        
        This method:
        1. Navigates to search URL with ALL filters embedded (date, experience, workplace)
        2. Processes all jobs in the filtered view
        
        Args:
            position: Job position/keyword
            location: Location to search
        """
        try:
            # Step 1: Navigate to search results with filters in URL
            logger.info(f"📍 Navigating to: '{position}' in '{location}' (filters in URL)")
            if not self.job_search.search_jobs(position, location):
                logger.error("❌ Failed to load search results")
                return

            # Step 2: Filters already applied via URL
            logger.info("✅ All filters applied via URL (no UI interaction needed)")
            
            # Give time for results to load
            StealthUtils.human_sleep(2, 3)

            # Step 3: Get job cards from filtered results
            logger.info("Step 3: Retrieving job cards from filtered results")
            jobs = self.job_search.get_job_cards()
            self.stats["jobs_found"] += len(jobs)

            if not jobs:
                logger.info("No eligible jobs found for this search combination")
                return

            logger.info(f"✅ Found {len(jobs)} jobs to process in this filtered view")

            # Step 4: Apply to each job
            self._process_job_list(jobs)

        except Exception as e:
            logger.error(f"Error in search and apply: {e}", exc_info=True)

    def _process_job_list(self, jobs: List[Dict]):
        """
        Process a list of job cards and apply to them.
        
        Args:
            jobs: List of job dictionaries with 'id' and 'element'
        """
        for i, job in enumerate(jobs, 1):
            job_id = job["id"]

            logger.info(f"\n--- Job {i}/{len(jobs)} (ID: {job_id}) ---")

            try:
                # Click job card to view details
                if not self.job_search.click_job_card(job_id):
                    logger.warning("Failed to click job card")
                    continue

                # Check for Easy Apply button
                if not self.job_search.has_easy_apply_button():
                    logger.info("❌ No Easy Apply button - skipping")
                    continue

                # Get job details
                job_title, company = self.job_search.get_job_title_and_company()

                # Check blacklisted titles
                if any(title.lower() in job_title.lower()
                       for title in self.config.blacklist_titles):
                    logger.info(f"❌ Blacklisted title: {job_title}")
                    continue

                # Apply to job
                self.stats["jobs_attempted"] += 1
                
                try:
                    result = self.application.apply_to_job(
                        job_id, job_title, company)

                    if result == "success":
                        self.stats["jobs_applied"] += 1
                        self.job_search.applied_job_ids.add(job_id)
                    else:  # result == "failed"
                        self.stats["jobs_failed"] += 1

                    # Random delay between applications
                    StealthUtils.human_sleep(3, 7)
                    
                except DailyLimitReachedException as e:
                    # LinkedIn daily limit reached - stop entire bot
                    logger.critical("\n🛑 STOPPING BOT: Daily application limit reached")
                    logger.critical("The bot will now exit to avoid appearing suspicious.")
                    logger.critical("Please try again tomorrow.")
                    self.stats["jobs_failed"] += 1
                    raise  # Re-raise to stop the entire run() method

            except Exception as e:
                logger.error(
                    f"Error processing job {job_id}: {e}",
                    exc_info=True)
                self.stats["jobs_failed"] += 1
                continue
    
    def _search_and_apply(self, position: str, location: str):
        """
        Legacy method - redirects to new filter-based method.
        
        Args:
            position: Job position/keyword
            location: Location to search
        """
        self._search_and_apply_with_filters(position, location)

    def _print_statistics(self):
        """Print final statistics."""
        logger.info("\n" + "=" * 80)
        logger.info("📊 Session Statistics")
        logger.info("=" * 80)
        logger.info(f"Jobs Found:     {self.stats['jobs_found']}")
        logger.info(f"Jobs Attempted: {self.stats['jobs_attempted']}")
        logger.info(f"Jobs Applied:   {self.stats['jobs_applied']}")
        logger.info(f"Jobs Failed:    {self.stats['jobs_failed']}")

        if self.stats['jobs_attempted'] > 0:
            success_rate = (
                self.stats['jobs_applied'] / self.stats['jobs_attempted']) * 100
            logger.info(f"Success Rate:   {success_rate:.1f}%")

        logger.info("=" * 80)


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="LinkedIn Easy Apply Bot - Automated job applications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main                    # Run normally
  python -m src.main --dry-run          # Simulate without submitting
  python -m src.main --headless         # Run without visible browser
  python -m src.main --config custom.yaml  # Use custom config file
        """
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration YAML file (default: config.yaml)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate applications without submitting (for testing)'
    )

    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode (no visible window)'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='LinkedIn Easy Apply Bot v2.0.0'
    )

    args = parser.parse_args()

    # Validate config file exists
    if not Path(args.config).exists():
        print(f"Error: Configuration file not found: {args.config}")
        sys.exit(1)

    # Create and run bot
    try:
        bot = LinkedInEasyApplyBot(
            config_file=args.config,
            dry_run=args.dry_run,
            headless=args.headless
        )
        bot.run()
    except KeyboardInterrupt:
        logger.info("\nBot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
