"""
Base service class for all business logic services.
Provides common functionality following OOP principles.
"""

from abc import ABC, abstractmethod
from typing import Optional
from sqlalchemy.orm import Session
from models.database import DatabaseManager
from config.settings import Settings, settings as default_settings
from loguru import logger


class BaseService(ABC):
    """
    Abstract base service class.
    All service classes should inherit from this to ensure consistent structure.
    """

    def __init__(self, settings: Optional[Settings] = None, db_session: Optional[Session] = None):
        """
        Initialize base service.

        Args:
            settings: Application settings (optional, uses global settings if not provided)
            db_session: Database session (optional, creates new if not provided)
        """
        self._settings = settings or default_settings
        self._db_session = db_session
        self._logger = logger
        self._initialize()

    @abstractmethod
    def _initialize(self) -> None:
        """
        Initialize service-specific resources.
        Must be implemented by subclasses.
        """
        pass

    @property
    def settings(self) -> Settings:
        """Get application settings."""
        return self._settings

    @property
    def logger(self):
        """Get logger instance."""
        return self._logger

    @property
    def db_session(self) -> Session:
        """
        Get database session.
        Creates new session if not provided in constructor.
        """
        if self._db_session is None:
            db_manager = DatabaseManager(
                database_url=self._settings.DATABASE_URL,
                echo=self._settings.DEBUG
            )
            self._db_session = db_manager.get_session()
        return self._db_session

    def close(self) -> None:
        """
        Clean up service resources.
        Should be called when service is no longer needed.
        """
        if self._db_session:
            self._db_session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
