"""
Main Bot class for LinkedIn automation with stealth features.
"""

import os
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from typing import Optional

from src.config import Config
from src.logger import get_logger
from src.utils import StealthUtils

logger = get_logger()


class LinkedInBot:
    """Main bot class for LinkedIn automation."""

    def __init__(self, config: Config, headless: bool = False):
        """
        Initialize the LinkedIn bot.

        Args:
            config: Configuration object
            headless: Whether to run browser in headless mode
        """
        self.config = config
        self.headless = headless
        self.driver: Optional[uc.Chrome] = None
        self.wait: Optional[WebDriverWait] = None

        logger.info("Initializing LinkedIn Bot...")
        self._setup_browser()

    def _setup_browser(self):
        """Set up undetected Chrome browser with stealth options."""
        try:
            options = uc.ChromeOptions()

            # Stealth options
            options.add_argument("--start-maximized")
            options.add_argument(
                "--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--no-sandbox")

            # User agent randomization
            user_agents = [
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ]
            import random
            options.add_argument(f"user-agent={random.choice(user_agents)}")

            # Disable automation flags
            # Note: These are handled automatically by undetected-chromedriver
            # options.add_experimental_option("excludeSwitches", ["enable-automation"])
            # options.add_experimental_option("useAutomationExtension", False)

            # Preferences to appear more human
            prefs = {
                "profile.default_content_setting_values.notifications": 2,
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
            }
            options.add_experimental_option("prefs", prefs)

            if self.headless:
                options.add_argument("--headless=new")
                logger.info("Running in headless mode")

            # Check for macOS Chrome location
            chrome_path = None
            if os.path.exists(
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
                chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                options.binary_location = chrome_path
                logger.info(f"Using Chrome from: {chrome_path}")

            # Initialize undetected ChromeDriver
            # version_main=144 to match Chrome 144.0.7559.110
            # use_subprocess=True helps with stability on newer Chrome versions
            self.driver = uc.Chrome(
                options=options, 
                version_main=144,
                use_subprocess=True,
                driver_executable_path=None
            )
            self.wait = WebDriverWait(self.driver, 30)
            
            # Give browser extra time to fully initialize with Chrome 144+
            logger.info("Waiting for browser to stabilize...")
            time.sleep(5)
            
            # Test that browser is responsive
            try:
                _ = self.driver.window_handles
                logger.info(f"✅ Browser responsive with {len(self.driver.window_handles)} window(s)")
            except Exception as e:
                logger.error(f"Browser not responsive: {e}")
                raise

            # Execute CDP commands to hide webdriver (with error handling)
            try:
                self.driver.execute_cdp_cmd(
                    "Page.addScriptToEvaluateOnNewDocument", {
                        "source": """
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                        Object.defineProperty(navigator, 'plugins', {
                            get: () => [1, 2, 3, 4, 5]
                        });
                        Object.defineProperty(navigator, 'languages', {
                            get: () => ['en-US', 'en']
                        });
                    """})
                logger.info("✅ Browser stealth features applied")
            except Exception as cdp_error:
                logger.warning(f"⚠️  Could not apply CDP stealth features: {cdp_error}")
                logger.warning("Continuing without CDP commands (bot may be detectable)")

            logger.info(
                "Browser initialized successfully")

        except Exception as e:
            logger.critical(
                f"Failed to initialize browser: {e}",
                exc_info=True)
            raise

    def login(self) -> bool:
        """
        Log in to LinkedIn.

        Returns:
            True if login successful, False otherwise
        """
        try:
            # Verify browser is still alive before attempting login
            try:
                window_count = len(self.driver.window_handles)
                if window_count == 0:
                    logger.error("No browser windows available - browser closed unexpectedly")
                    return False
                logger.debug(f"Browser has {window_count} window(s) available")
            except Exception as window_error:
                logger.error(f"Browser not accessible: {window_error}")
                return False
            
            logger.info("Navigating to LinkedIn login page...")
            self.driver.get("https://www.linkedin.com/login")

            StealthUtils.human_sleep(2, 4)

            # Wait for and fill username
            logger.info("Entering credentials...")
            username_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            StealthUtils.type_like_human(username_field, self.config.username)

            StealthUtils.human_sleep(0.5, 1.5)

            # Fill password
            password_field = self.driver.find_element(By.ID, "password")
            StealthUtils.type_like_human(password_field, self.config.password)

            StealthUtils.human_sleep(1, 2)

            # Click login button
            login_button = self.driver.find_element(
                By.CSS_SELECTOR, 'button[type="submit"]')
            StealthUtils.smooth_scroll_to_element(self.driver, login_button)
            login_button.click()

            logger.info("Login button clicked, waiting for redirect...")
            StealthUtils.human_sleep(5, 8)

            # Check if login was successful
            if "feed" in self.driver.current_url or "mynetwork" in self.driver.current_url:
                logger.info("✅ Successfully logged in to LinkedIn")
                return True
            elif "checkpoint" in self.driver.current_url or "challenge" in self.driver.current_url:
                logger.warning(
                    "⚠️  LinkedIn security checkpoint detected - please complete manually")
                logger.warning("Waiting 60 seconds for manual verification...")
                StealthUtils.human_sleep(60, 65)
                return "checkpoint" not in self.driver.current_url
            else:
                logger.error(
                    f"Login may have failed - current URL: {self.driver.current_url}")
                return False

        except TimeoutException:
            logger.error("Timeout while trying to log in", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Login failed: {e}", exc_info=True)
            return False

    def is_logged_in(self) -> bool:
        """
        Check if currently logged in to LinkedIn.

        Returns:
            True if logged in, False otherwise
        """
        try:
            current_url = self.driver.current_url
            return "linkedin.com" in current_url and "login" not in current_url
        except BaseException:
            return False

    def navigate_to_jobs(self):
        """Navigate to LinkedIn jobs page."""
        try:
            logger.info("Navigating to jobs page...")
            self.driver.get("https://www.linkedin.com/jobs/")
            StealthUtils.human_sleep(2, 4)
            logger.info("Jobs page loaded")
        except Exception as e:
            logger.error(
                f"Failed to navigate to jobs page: {e}",
                exc_info=True)

    def close(self):
        """Close the browser and clean up."""
        if self.driver:
            try:
                logger.info("Closing browser...")
                self.driver.quit()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
