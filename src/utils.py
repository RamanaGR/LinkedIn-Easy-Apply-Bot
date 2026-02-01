"""
Utility functions for stealth operations and helper methods.
"""

import time
import random
from typing import Optional
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.webdriver import WebDriver
from src.logger import get_logger

logger = get_logger()


class StealthUtils:
    """Utilities for making the bot appear more human-like."""

    @staticmethod
    def human_sleep(min_seconds: float = 1.0, max_seconds: float = 3.0):
        """
        Sleep for a random duration to mimic human behavior.

        Args:
            min_seconds: Minimum sleep duration
            max_seconds: Maximum sleep duration
        """
        duration = random.uniform(min_seconds, max_seconds)
        logger.debug(f"Human sleep: {duration:.2f}s")
        time.sleep(duration)

    @staticmethod
    def random_scroll(driver: WebDriver, element: Optional[WebElement] = None):
        """
        Perform random scrolling to appear more human-like.

        Args:
            driver: WebDriver instance
            element: Optional element to scroll within
        """
        try:
            if element:
                # Scroll within element
                scroll_amount = random.randint(100, 500)
                driver.execute_script(
                    f"arguments[0].scrollTop = {scroll_amount};",
                    element
                )
                logger.debug(f"Scrolled within element: {scroll_amount}px")
            else:
                # Scroll the page
                scroll_amount = random.randint(300, 800)
                driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                logger.debug(f"Scrolled page: {scroll_amount}px")

            StealthUtils.human_sleep(0.5, 1.5)
        except Exception as e:
            logger.debug(f"Random scroll failed: {e}")

    @staticmethod
    def smooth_scroll_to_element(driver: WebDriver, element: WebElement):
        """
        Smoothly scroll to an element before interacting with it.

        Args:
            driver: WebDriver instance
            element: Element to scroll to
        """
        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            StealthUtils.human_sleep(0.5, 1.0)
            logger.debug("Smoothly scrolled to element")
        except Exception as e:
            logger.debug(f"Smooth scroll failed: {e}")

    @staticmethod
    def random_mouse_movement(driver: WebDriver):
        """
        Simulate random mouse movements (via JavaScript).

        Args:
            driver: WebDriver instance
        """
        try:
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            driver.execute_script(f"""
                var event = new MouseEvent('mousemove', {{
                    'view': window,
                    'bubbles': true,
                    'cancelable': true,
                    'clientX': {x},
                    'clientY': {y}
                }});
                document.dispatchEvent(event);
            """)
            logger.debug(f"Random mouse movement: ({x}, {y})")
        except Exception as e:
            logger.debug(f"Random mouse movement failed: {e}")

    @staticmethod
    def random_typing_delay() -> float:
        """
        Get a random delay between keystrokes to mimic human typing.

        Returns:
            Random delay in seconds
        """
        return random.uniform(0.05, 0.15)

    @staticmethod
    def type_like_human(element: WebElement, text: str):
        """
        Type text into an element with human-like delays.

        Args:
            element: WebElement to type into
            text: Text to type
        """
        try:
            element.clear()
            for char in text:
                element.send_keys(char)
                time.sleep(StealthUtils.random_typing_delay())
            logger.debug(
                f"Typed text with human-like delays: {len(text)} characters")
        except Exception as e:
            logger.error(f"Human typing failed: {e}")
            # Fallback to normal typing
            element.clear()
            element.send_keys(text)


class DateUtils:
    """Utilities for date and time operations."""

    @staticmethod
    def get_time_ago_filter(days: int) -> str:
        """
        Get LinkedIn time filter parameter.

        Args:
            days: Number of days ago

        Returns:
            LinkedIn time filter string
        """
        time_filters = {
            1: "r86400",      # Past 24 hours
            7: "r604800",     # Past week
            30: "r2592000",   # Past month
        }
        return time_filters.get(days, "")
