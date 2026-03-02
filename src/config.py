"""
Configuration management with environment variable support.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from src.logger import get_logger

logger = get_logger()


class Config:
    """Configuration manager for the LinkedIn Easy Apply Bot."""

    def __init__(self, config_file: str = "config.yaml"):
        """
        Initialize configuration.

        Args:
            config_file: Path to YAML configuration file
        """
        # Load YAML configuration first to resolve paths
        self.config_file = Path(config_file)
        self._load_config()

        # Load .env from project root (directory of config file) so key is found when run from any cwd
        env_path = self.config_file.resolve().parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        load_dotenv()  # Also try cwd for backward compatibility

        # Load credentials from environment
        self._load_credentials()

        logger.info("Configuration loaded successfully")

    def _load_config(self):
        """Load configuration from YAML file."""
        try:
            with open(self.config_file, 'r') as f:
                self._config = yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_file}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            raise

    def _load_credentials(self):
        """Load credentials from environment variables."""
        def _getenv(key: str) -> Optional[str]:
            val = os.getenv(key)
            return val.strip() if isinstance(val, str) else val

        self.username = _getenv('LINKEDIN_USERNAME')
        self.password = _getenv('LINKEDIN_PASSWORD')
        self.openai_api_key = _getenv('OPENAI_API_KEY')

        if not self.username or not self.password:
            logger.critical(
                "LINKEDIN_USERNAME and LINKEDIN_PASSWORD must be set in .env file")
            raise ValueError(
                "Missing required credentials in environment variables")

        logger.info(f"Credentials loaded for user: {self.username[:3]}***")

        if not self.openai_api_key:
            logger.warning(
                "OPENAI_API_KEY not set - AI features will be limited")
        else:
            logger.info("OPENAI_API_KEY loaded - AI form filling enabled")

    @property
    def phone_number(self) -> Optional[str]:
        """Get phone number from config."""
        return self._config.get('phone_number')

    @property
    def positions(self) -> List[str]:
        """Get list of job positions to search for."""
        positions = self._config.get('positions', [])
        return [p for p in positions if p]  # Filter out None/empty values

    @property
    def locations(self) -> List[str]:
        """Get list of locations to search in."""
        locations = self._config.get('locations', [])
        return [l for l in locations if l]  # Filter out None/empty values

    @property
    def salary(self) -> Optional[str]:
        """Get salary requirement."""
        return self._config.get('salary')

    @property
    def rate(self) -> Optional[int]:
        """Get hourly rate requirement."""
        return self._config.get('rate')

    @property
    def uploads(self) -> Dict[str, str]:
        """Get file upload paths (resume, cover letter, etc.)."""
        uploads = self._config.get('uploads', {})

        # Validate file paths
        validated_uploads = {}
        for key, path in uploads.items():
            if path and Path(path).exists():
                validated_uploads[key] = str(Path(path).resolve())
                logger.debug(f"Upload file validated: {key} -> {path}")
            else:
                logger.warning(f"Upload file not found: {key} -> {path}")

        return validated_uploads

    @property
    def output_filename(self) -> str:
        """Get output CSV filename."""
        output = self._config.get('output_filename', ['output.csv'])
        if isinstance(output, list):
            return output[0] if output else 'output.csv'
        return output

    @property
    def blacklist(self) -> List[str]:
        """Get list of blacklisted companies."""
        return self._config.get('blacklist', [])

    @property
    def blacklist_titles(self) -> List[str]:
        """Get list of blacklisted job titles."""
        return self._config.get('blackListTitles', [])

    @property
    def experience_level(self) -> List[str]:
        """
        Get desired experience levels as text labels.
        
        Returns:
            List of experience level text labels (e.g., ["Associate", "Mid-Senior level"])
        """
        exp_levels = self._config.get('experience_level', [])
        
        # If levels are provided as text, return as-is
        if exp_levels and isinstance(exp_levels[0], str):
            return exp_levels
        
        # If levels are provided as numbers, convert to text
        level_map = {
            1: "Entry level",
            2: "Associate",
            3: "Mid-Senior level",
            4: "Director",
            5: "Executive",
            6: "Internship"
        }
        
        return [level_map.get(level, str(level)) for level in exp_levels if isinstance(level, int)]

    @property
    def max_search_time(self) -> int:
        """Get maximum search time in seconds."""
        return self._config.get('max_search_time', 60 * 60)  # Default 1 hour
    
    @property
    def require_submission_confirmation(self) -> bool:
        """Get whether to require user confirmation before submitting."""
        return self._config.get('require_submission_confirmation', False)
    
    @property
    def date_posted_filter(self) -> str:
        """Get date posted filter."""
        search_config = self._config.get('search', {})
        filters = search_config.get('filters', {})
        return filters.get('date_posted', 'any')
    
    @property
    def workplace_type_filters(self) -> List[str]:
        """Get workplace type filters."""
        search_config = self._config.get('search', {})
        filters = search_config.get('filters', {})
        workplace = filters.get('workplace_type', [])
        # Ensure it's a list
        if isinstance(workplace, str):
            return [workplace]
        return workplace if workplace else []
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        return self._config.get(key, default)

    def log_config_summary(self):
        """Log configuration summary (without sensitive data)."""
        logger.info("Configuration Summary:")
        logger.info(
            f"  Positions: {len(self.positions)} ({', '.join(self.positions[:3])}...)")
        logger.info(
            f"  Locations: {len(self.locations)} ({', '.join(self.locations[:3])}...)")
        logger.info(f"  Experience Levels: {self.experience_level}")
        logger.info(f"  Uploads: {list(self.uploads.keys())}")
        logger.info(f"  Output File: {self.output_filename}")
        logger.info(f"  Max Search Time: {self.max_search_time // 60} minutes")
