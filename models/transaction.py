"""
Transaction domain model.
"""

from sqlalchemy import Column, String, Float, ForeignKey, Integer, DateTime
from sqlalchemy.orm import relationship
from models.base import BaseModel
from datetime import datetime, timezone


class Transaction(BaseModel):
    """
    Transaction model representing buy/sell operations.
    Maintains transaction history for audit and analysis.
    """

    __tablename__ = "transactions"

    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    transaction_type = Column(String(10), nullable=False)  # BUY, SELL, DIVIDEND, FEE
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    commission = Column(Float, nullable=False, default=0.0)
    transaction_date = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    notes = Column(String(500), nullable=True)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="transactions")

    def calculate_net_amount(self) -> float:
        """
        Calculate net transaction amount including commission.

        Returns:
            Net amount
        """
        if self.transaction_type in ["BUY", "FEE"]:
            return -(self.total_amount + self.commission)
        else:  # SELL, DIVIDEND
            return self.total_amount - self.commission

    def __repr__(self) -> str:
        """String representation of transaction."""
        return (f"<Transaction(id={self.id}, type='{self.transaction_type}', "
                f"symbol='{self.symbol}', quantity={self.quantity}, "
                f"price={self.price:.2f})>")
