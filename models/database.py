"""
Database configuration and session management using Singleton pattern.
"""

from typing import Optional, Generator
from sqlalchemy import create_engine, Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from threading import Lock


# Create base class for models
Base = declarative_base()


class DatabaseManager:
    """
    Singleton database manager following OOP principles.
    Ensures only one database connection instance exists throughout the application.
    """

    _instance: Optional['DatabaseManager'] = None
    _lock: Lock = Lock()
    _engine: Optional[Engine] = None
    _session_factory: Optional[sessionmaker] = None
    _scoped_session: Optional[scoped_session] = None

    def __new__(cls, database_url: Optional[str] = None, echo: bool = False) -> 'DatabaseManager':
        """
        Thread-safe singleton implementation.

        Args:
            database_url: Database connection URL
            echo: Enable SQL query logging

        Returns:
            DatabaseManager instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, database_url: Optional[str] = None, echo: bool = False) -> None:
        """
        Initialize database manager.

        Args:
            database_url: Database connection URL
            echo: Enable SQL query logging
        """
        if self._initialized:
            return

        if database_url is None:
            raise ValueError("database_url must be provided on first initialization")

        self._database_url = database_url
        self._echo = echo
        self._initialize_engine()
        self._initialize_session_factory()
        self._initialized = True

    def _initialize_engine(self) -> None:
        """Initialize SQLAlchemy engine with appropriate settings."""
        connect_args = {}

        # SQLite-specific settings
        if "sqlite" in self._database_url:
            connect_args["check_same_thread"] = False

        self._engine = create_engine(
            self._database_url,
            connect_args=connect_args,
            echo=self._echo,
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600,   # Recycle connections after 1 hour
        )

    def _initialize_session_factory(self) -> None:
        """Initialize session factory for creating database sessions."""
        self._session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self._engine
        )
        self._scoped_session = scoped_session(self._session_factory)

    @property
    def engine(self) -> Engine:
        """Get database engine."""
        if self._engine is None:
            raise RuntimeError("Database engine not initialized")
        return self._engine

    @property
    def session_factory(self) -> sessionmaker:
        """Get session factory."""
        if self._session_factory is None:
            raise RuntimeError("Session factory not initialized")
        return self._session_factory

    def get_session(self) -> Session:
        """
        Create a new database session.

        Returns:
            SQLAlchemy Session instance
        """
        if self._scoped_session is None:
            raise RuntimeError("Scoped session not initialized")
        return self._scoped_session()

    def get_session_context(self) -> Generator[Session, None, None]:
        """
        Get database session with context manager support.
        Automatically handles commit/rollback and cleanup.

        Yields:
            SQLAlchemy Session instance

        Example:
            with db_manager.get_session_context() as session:
                session.add(user)
                session.commit()
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_all_tables(self) -> None:
        """Create all database tables defined in models."""
        Base.metadata.create_all(bind=self.engine)

    def drop_all_tables(self) -> None:
        """Drop all database tables. Use with caution!"""
        Base.metadata.drop_all(bind=self.engine)

    def close(self) -> None:
        """Close all database connections and cleanup resources."""
        if self._scoped_session:
            self._scoped_session.remove()

        if self._engine:
            self._engine.dispose()

    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset singleton instance.
        Useful for testing or reconnecting to different database.
        """
        with cls._lock:
            if cls._instance:
                cls._instance.close()
                cls._instance = None


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    Compatible with FastAPI dependency injection.

    Yields:
        SQLAlchemy Session instance
    """
    from config.settings import settings

    db_manager = DatabaseManager(
        database_url=settings.DATABASE_URL,
        echo=settings.DEBUG
    )

    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    """
    Initialize database tables.
    Should be called on application startup.
    """
    from config.settings import settings

    db_manager = DatabaseManager(
        database_url=settings.DATABASE_URL,
        echo=settings.DEBUG
    )
    db_manager.create_all_tables()
