"""
Decision domain model for AI-powered recommendations.
"""

from sqlalchemy import Column, String, Float, ForeignKey, Integer, Text, DateTime
from sqlalchemy.orm import relationship
from models.base import BaseModel
from datetime import datetime, timezone


class Decision(BaseModel):
    """
    Decision model representing AI-generated trading recommendations.
    Tracks decision history and outcomes for continuous learning.
    """

    __tablename__ = "decisions"

    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    decision_type = Column(String(10), nullable=False)  # BUY, SELL, HOLD
    recommended_quantity = Column(Float, nullable=True)
    recommended_price = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=False)  # 0.0 to 1.0
    reasoning = Column(Text, nullable=True)  # AI-generated explanation
    technical_signals = Column(Text, nullable=True)  # JSON string of technical indicators
    fundamental_signals = Column(Text, nullable=True)  # JSON string of fundamental data
    risk_assessment = Column(Text, nullable=True)  # Risk analysis details
    status = Column(String(20), nullable=False, default="PENDING")  # PENDING, ACCEPTED, REJECTED, EXECUTED
    decision_date = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    executed_date = Column(DateTime, nullable=True)
    execution_price = Column(Float, nullable=True)
    outcome = Column(String(20), nullable=True)  # SUCCESS, FAILURE, NEUTRAL
    outcome_pnl = Column(Float, nullable=True)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="decisions")

    def accept_decision(self) -> None:
        """Mark decision as accepted by user."""
        self.status = "ACCEPTED"

    def reject_decision(self) -> None:
        """Mark decision as rejected by user."""
        self.status = "REJECTED"

    def mark_executed(self, execution_price: float) -> None:
        """
        Mark decision as executed.

        Args:
            execution_price: Actual execution price
        """
        self.status = "EXECUTED"
        self.executed_date = datetime.now(timezone.utc)
        self.execution_price = execution_price

    def record_outcome(self, outcome: str, pnl: float) -> None:
        """
        Record the outcome of the decision.

        Args:
            outcome: Outcome status (SUCCESS, FAILURE, NEUTRAL)
            pnl: Profit/loss from the decision
        """
        self.outcome = outcome
        self.outcome_pnl = pnl

    def is_high_confidence(self, threshold: float = 0.7) -> bool:
        """
        Check if decision has high confidence.

        Args:
            threshold: Minimum confidence threshold

        Returns:
            True if confidence exceeds threshold
        """
        return self.confidence_score >= threshold

    def __repr__(self) -> str:
        """String representation of decision."""
        return (f"<Decision(id={self.id}, type='{self.decision_type}', "
                f"symbol='{self.symbol}', confidence={self.confidence_score:.2f}, "
                f"status='{self.status}')>")
