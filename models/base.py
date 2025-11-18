"""
Base model classes with common functionality.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.ext.declarative import declared_attr
from models.database import Base


class TimestampMixin:
    """
    Mixin class to add timestamp fields to models.
    Follows DRY principle by providing reusable timestamp functionality.
    """

    @declared_attr
    def created_at(cls):
        """Timestamp when record was created."""
        return Column(DateTime, default=datetime.utcnow, nullable=False)

    @declared_attr
    def updated_at(cls):
        """Timestamp when record was last updated."""
        return Column(
            DateTime,
            default=datetime.utcnow,
            onupdate=datetime.utcnow,
            nullable=False
        )


class BaseModel(Base, TimestampMixin):
    """
    Abstract base model class with common fields and methods.
    All domain models should inherit from this class.
    """

    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    def to_dict(self) -> dict:
        """
        Convert model instance to dictionary.

        Returns:
            Dictionary representation of the model
        """
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    def update(self, **kwargs) -> None:
        """
        Update model attributes.

        Args:
            **kwargs: Attribute name-value pairs to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self) -> str:
        """String representation of the model."""
        return f"<{self.__class__.__name__}(id={self.id})>"
