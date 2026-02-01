"""
Centralized logging configuration for the LinkedIn Easy Apply Bot.
"""

import logging
from datetime import datetime
from pathlib import Path


class BotLogger:
    """Centralized logger for the application."""

    _instance = None
    _logger = None

    def __new__(cls):
        """Singleton pattern to ensure one logger instance."""
        if cls._instance is None:
            cls._instance = super(BotLogger, cls).__new__(cls)
            cls._instance._setup_logger()
        return cls._instance

    def _setup_logger(self):
        """Configure logging to both file and console."""
        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Create log filename with timestamp
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        log_file = logs_dir / f"bot_{timestamp}.log"

        # Create logger
        self._logger = logging.getLogger("LinkedInEasyApplyBot")
        self._logger.setLevel(logging.DEBUG)

        # Prevent duplicate handlers
        if self._logger.handlers:
            self._logger.handlers.clear()

        # File handler - detailed logs
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(file_formatter)

        # Console handler - important logs only
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)

        # Add handlers
        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)

        self._logger.info("=" * 80)
        self._logger.info("LinkedIn Easy Apply Bot - Session Started")
        self._logger.info(f"Log file: {log_file}")
        self._logger.info("=" * 80)

    @property
    def logger(self):
        """Get the logger instance."""
        return self._logger

    def debug(self, message):
        """Log debug message."""
        self._logger.debug(message)

    def info(self, message):
        """Log info message."""
        self._logger.info(message)

    def warning(self, message):
        """Log warning message."""
        self._logger.warning(message)

    def error(self, message, exc_info=False):
        """Log error message."""
        self._logger.error(message, exc_info=exc_info)

    def critical(self, message, exc_info=False):
        """Log critical message."""
        self._logger.critical(message, exc_info=exc_info)


# Convenience function to get logger
def get_logger():
    """Get the singleton logger instance."""
    return BotLogger().logger
