"""
Configuration management using Singleton pattern.
Loads settings from environment variables with fallback to .env file.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from threading import Lock
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Uses Pydantic for validation and type safety.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application Configuration
    APP_NAME: str = Field(default="Money Management Service")
    APP_ENV: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    LOG_LEVEL: str = Field(default="INFO")

    # Database Configuration
    DATABASE_URL: str = Field(default="sqlite:///./money_management.db")

    # API Keys
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)
    OPENAI_API_KEY: Optional[str] = Field(default=None)

    # Market Data Configuration
    DEFAULT_MARKET_INDEX: str = Field(default="^GSPC")
    DEFAULT_CURRENCY: str = Field(default="USD")
    MARKET_DATA_CACHE_TTL: int = Field(default=300)  # seconds

    # Risk Management Defaults
    DEFAULT_RISK_FREE_RATE: float = Field(default=0.04)
    DEFAULT_POSITION_SIZE_PERCENT: float = Field(default=0.05)
    MAX_POSITION_SIZE_PERCENT: float = Field(default=0.20)
    DEFAULT_STOP_LOSS_PERCENT: float = Field(default=0.05)

    # Alert Configuration
    ENABLE_EMAIL_ALERTS: bool = Field(default=False)
    SMTP_SERVER: str = Field(default="smtp.gmail.com")
    SMTP_PORT: int = Field(default=587)
    SMTP_USERNAME: Optional[str] = Field(default=None)
    SMTP_PASSWORD: Optional[str] = Field(default=None)
    ALERT_RECIPIENT_EMAIL: Optional[str] = Field(default=None)

    # Decision Engine Configuration
    MIN_CONFIDENCE_THRESHOLD: float = Field(default=0.60)
    ENABLE_AI_REASONING: bool = Field(default=True)
    AI_MODEL: str = Field(default="claude-sonnet-4-5-20250929")

    # Backtesting Configuration
    DEFAULT_INITIAL_CAPITAL: float = Field(default=100000.0)
    DEFAULT_BACKTEST_START_DATE: str = Field(default="2023-01-01")
    TRANSACTION_COST_PERCENT: float = Field(default=0.001)

    # UI Configuration
    STREAMLIT_SERVER_PORT: int = Field(default=8501)
    STREAMLIT_SERVER_ADDRESS: str = Field(default="localhost")
    STREAMLIT_THEME: str = Field(default="dark")

    # Feature Flags
    ENABLE_LIVE_TRADING: bool = Field(default=False)
    ENABLE_PAPER_TRADING: bool = Field(default=True)
    ENABLE_ALERTS: bool = Field(default=True)
    ENABLE_BACKTESTING: bool = Field(default=True)

    @field_validator('LOG_LEVEL')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid LOG_LEVEL. Must be one of {valid_levels}")
        return v_upper

    @field_validator('APP_ENV')
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        """Validate application environment."""
        valid_envs = ["development", "staging", "production", "testing"]
        v_lower = v.lower()
        if v_lower not in valid_envs:
            raise ValueError(f"Invalid APP_ENV. Must be one of {valid_envs}")
        return v_lower

    @field_validator('MIN_CONFIDENCE_THRESHOLD')
    @classmethod
    def validate_confidence_threshold(cls, v: float) -> float:
        """Validate confidence threshold is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("MIN_CONFIDENCE_THRESHOLD must be between 0 and 1")
        return v

    @field_validator('DEFAULT_POSITION_SIZE_PERCENT', 'MAX_POSITION_SIZE_PERCENT',
                     'DEFAULT_STOP_LOSS_PERCENT', 'TRANSACTION_COST_PERCENT')
    @classmethod
    def validate_percentage(cls, v: float) -> float:
        """Validate percentage values are between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError(f"Percentage value must be between 0 and 1, got {v}")
        return v

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.APP_ENV == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.APP_ENV == "development"

    def has_anthropic_key(self) -> bool:
        """Check if Anthropic API key is configured."""
        return self.ANTHROPIC_API_KEY is not None and len(self.ANTHROPIC_API_KEY) > 0

    def has_openai_key(self) -> bool:
        """Check if OpenAI API key is configured."""
        return self.OPENAI_API_KEY is not None and len(self.OPENAI_API_KEY) > 0


class SettingsManager:
    """
    Singleton Settings Manager for centralized configuration access.
    Ensures only one settings instance exists throughout the application.
    """

    _instance: Optional['SettingsManager'] = None
    _lock: Lock = Lock()
    _settings: Optional[Settings] = None

    def __new__(cls) -> 'SettingsManager':
        """
        Thread-safe singleton implementation.

        Returns:
            SettingsManager instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(SettingsManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize settings manager."""
        if self._initialized:
            return

        self._settings = Settings()
        self._initialized = True

    @property
    def settings(self) -> Settings:
        """
        Get settings instance.

        Returns:
            Settings object
        """
        if self._settings is None:
            raise RuntimeError("Settings not initialized")
        return self._settings

    def reload(self) -> None:
        """Reload settings from environment variables."""
        self._settings = Settings()

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance. Useful for testing."""
        with cls._lock:
            cls._instance = None


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses LRU cache for performance optimization.

    Returns:
        Settings object
    """
    manager = SettingsManager()
    return manager.settings


# Global settings instance for convenience
settings = get_settings()
