"""
Portfolio and Position domain models.
"""

from typing import List, Optional
from sqlalchemy import Column, String, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship
from models.base import BaseModel


class Portfolio(BaseModel):
    """
    Portfolio model representing a collection of investments.
    Follows SRP (Single Responsibility Principle) - manages portfolio data only.
    """

    __tablename__ = "portfolios"

    name = Column(String(100), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    initial_capital = Column(Float, nullable=False, default=100000.0)
    cash_balance = Column(Float, nullable=False, default=100000.0)
    currency = Column(String(3), nullable=False, default="USD")
    is_active = Column(Integer, nullable=False, default=1)  # Boolean as int for SQLite

    # Relationships
    positions = relationship(
        "Position",
        back_populates="portfolio",
        cascade="all, delete-orphan",
        lazy="select"
    )
    transactions = relationship(
        "Transaction",
        back_populates="portfolio",
        cascade="all, delete-orphan",
        lazy="select"
    )
    decisions = relationship(
        "Decision",
        back_populates="portfolio",
        cascade="all, delete-orphan",
        lazy="select"
    )

    def calculate_total_value(self) -> float:
        """
        Calculate total portfolio value (cash + positions).

        Returns:
            Total portfolio value
        """
        positions_value = sum(
            position.calculate_current_value()
            for position in self.positions
            if position.is_open
        )
        return self.cash_balance + positions_value

    def calculate_total_pnl(self) -> float:
        """
        Calculate total profit and loss.

        Returns:
            Total P&L
        """
        return self.calculate_total_value() - self.initial_capital

    def calculate_return_percentage(self) -> float:
        """
        Calculate portfolio return as percentage.

        Returns:
            Return percentage
        """
        if self.initial_capital == 0:
            return 0.0
        return ((self.calculate_total_value() - self.initial_capital) /
                self.initial_capital) * 100

    def get_open_positions(self) -> List['Position']:
        """
        Get all currently open positions.

        Returns:
            List of open positions
        """
        return [pos for pos in self.positions if pos.is_open]

    def __repr__(self) -> str:
        """String representation of portfolio."""
        return (f"<Portfolio(id={self.id}, name='{self.name}', "
                f"value={self.calculate_total_value():.2f})>")


class Position(BaseModel):
    """
    Position model representing a single investment in a portfolio.
    Encapsulates position-specific calculations and data.
    """

    __tablename__ = "positions"

    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    average_entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    position_type = Column(String(10), nullable=False, default="LONG")  # LONG or SHORT
    is_open = Column(Integer, nullable=False, default=1)  # Boolean as int
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    notes = Column(String(1000), nullable=True)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="positions")

    def calculate_current_value(self) -> float:
        """
        Calculate current position value.

        Returns:
            Current value
        """
        return self.quantity * self.current_price

    def calculate_cost_basis(self) -> float:
        """
        Calculate original cost basis.

        Returns:
            Cost basis
        """
        return self.quantity * self.average_entry_price

    def calculate_pnl(self) -> float:
        """
        Calculate profit and loss.

        Returns:
            P&L amount
        """
        if self.position_type == "LONG":
            return self.calculate_current_value() - self.calculate_cost_basis()
        else:  # SHORT
            return self.calculate_cost_basis() - self.calculate_current_value()

    def calculate_pnl_percentage(self) -> float:
        """
        Calculate P&L as percentage.

        Returns:
            P&L percentage
        """
        cost_basis = self.calculate_cost_basis()
        if cost_basis == 0:
            return 0.0

        pnl = self.calculate_pnl()
        return (pnl / cost_basis) * 100

    def update_price(self, new_price: float) -> None:
        """
        Update current price of the position.

        Args:
            new_price: New market price
        """
        self.current_price = new_price

    def close_position(self, closing_price: float) -> None:
        """
        Close the position.

        Args:
            closing_price: Final closing price
        """
        self.current_price = closing_price
        self.is_open = 0

    def __repr__(self) -> str:
        """String representation of position."""
        return (f"<Position(id={self.id}, symbol='{self.symbol}', "
                f"quantity={self.quantity}, pnl={self.calculate_pnl():.2f})>")
