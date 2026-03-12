"""This module is load the .env configuration and provide access to the configuration values."""

from dotenv import load_dotenv
import os

class ConfigManager:
    """ConfigManager loads the .env file and provides access to configuration values."""
    
    def __init__(self, env_file=".env"):
        """Initialize the ConfigManager by loading the .env file."""
        load_dotenv(env_file)
    
    def get(self, key, default=None):
        """Get a configuration value by key, with an optional default."""
        value = os.getenv(key)
        if value is None:
            return default

        value = value.strip()
        if value == "":
            return default

        return value

    def get_float(self, key, default: float = 0.0) -> float:
        """Get a configuration value as float."""
        raw = self.get(key)
        if raw is None:
            return default
        try:
            return float(raw)
        except ValueError:
            return default

    def get_int(self, key, default: int = 0) -> int:
        """Get a configuration value as int."""
        raw = self.get(key)
        if raw is None:
            return default
        try:
            return int(raw)
        except ValueError:
            return default

    def get_api_key(self) -> str | None:
        """Get the first usable API key from known environment variables."""
        api_key = self.get("LLM_API_KEY")
        if api_key == "your_github_token_here":
            api_key = None
        return api_key or self.get("GITHUB_API_KEY") or self.get("GITHUB_TOKEN")


LLM_CONFIG = ConfigManager()