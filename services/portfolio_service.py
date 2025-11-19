"""
Portfolio Management Service.
Handles portfolio operations, positions, and transactions.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import and_
from services.base_service import BaseService
from models import Portfolio, Position, Transaction
from services.market_data_service import MarketDataService


class PortfolioService(BaseService):
    """
    Service for managing portfolios, positions, and transactions.
    Implements business logic for portfolio operations.
    """

    def _initialize(self) -> None:
        """Initialize portfolio service resources."""
        self._market_data_service = MarketDataService(self.settings)
        self.logger.info("PortfolioService initialized")

    # ==================== Portfolio Operations ====================

    def create_portfolio(
        self,
        name: str,
        initial_capital: float,
        description: Optional[str] = None,
        currency: str = "USD"
    ) -> Portfolio:
        """
        Create a new portfolio.

        Args:
            name: Portfolio name
            initial_capital: Starting capital
            description: Portfolio description
            currency: Base currency

        Returns:
            Created portfolio
        """
        try:
            portfolio = Portfolio(
                name=name,
                description=description,
                initial_capital=initial_capital,
                cash_balance=initial_capital,
                currency=currency,
                is_active=1
            )

            self.db_session.add(portfolio)
            self.db_session.commit()
            self.db_session.refresh(portfolio)

            self.logger.info(f"Created portfolio: {name} with capital {initial_capital}")
            return portfolio

        except Exception as e:
            self.db_session.rollback()
            self.logger.error(f"Error creating portfolio: {e}")
            raise

    def get_portfolio(self, portfolio_id: int) -> Optional[Portfolio]:
        """
        Get portfolio by ID.

        Args:
            portfolio_id: Portfolio ID

        Returns:
            Portfolio or None
        """
        try:
            return self.db_session.query(Portfolio).filter(
                Portfolio.id == portfolio_id
            ).first()
        except Exception as e:
            self.logger.error(f"Error fetching portfolio {portfolio_id}: {e}")
            return None

    def get_all_portfolios(self, active_only: bool = True) -> List[Portfolio]:
        """
        Get all portfolios.

        Args:
            active_only: Return only active portfolios

        Returns:
            List of portfolios
        """
        try:
            query = self.db_session.query(Portfolio)
            if active_only:
                query = query.filter(Portfolio.is_active == 1)
            return query.all()
        except Exception as e:
            self.logger.error(f"Error fetching portfolios: {e}")
            return []

    def update_portfolio(self, portfolio_id: int, **kwargs) -> Optional[Portfolio]:
        """
        Update portfolio attributes.

        Args:
            portfolio_id: Portfolio ID
            **kwargs: Attributes to update

        Returns:
            Updated portfolio or None
        """
        try:
            portfolio = self.get_portfolio(portfolio_id)
            if not portfolio:
                return None

            portfolio.update(**kwargs)
            self.db_session.commit()
            self.db_session.refresh(portfolio)

            self.logger.info(f"Updated portfolio {portfolio_id}")
            return portfolio

        except Exception as e:
            self.db_session.rollback()
            self.logger.error(f"Error updating portfolio {portfolio_id}: {e}")
            raise

    def deactivate_portfolio(self, portfolio_id: int) -> bool:
        """
        Deactivate a portfolio.

        Args:
            portfolio_id: Portfolio ID

        Returns:
            True if successful
        """
        try:
            portfolio = self.get_portfolio(portfolio_id)
            if portfolio:
                portfolio.is_active = 0
                self.db_session.commit()
                self.logger.info(f"Deactivated portfolio {portfolio_id}")
                return True
            return False
        except Exception as e:
            self.db_session.rollback()
            self.logger.error(f"Error deactivating portfolio {portfolio_id}: {e}")
            return False

    # ==================== Position Operations ====================

    def open_position(
        self,
        portfolio_id: int,
        symbol: str,
        quantity: float,
        entry_price: float,
        position_type: str = "LONG",
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        notes: Optional[str] = None
    ) -> Optional[Position]:
        """
        Open a new position.

        Args:
            portfolio_id: Portfolio ID
            symbol: Stock symbol
            quantity: Number of shares
            entry_price: Entry price per share
            position_type: LONG or SHORT
            stop_loss: Stop loss price
            take_profit: Take profit price
            notes: Additional notes

        Returns:
            Created position or None
        """
        try:
            portfolio = self.get_portfolio(portfolio_id)
            if not portfolio:
                self.logger.error(f"Portfolio {portfolio_id} not found")
                return None

            # Calculate total cost
            total_cost = quantity * entry_price

            # Check if sufficient cash
            if portfolio.cash_balance < total_cost:
                self.logger.error(f"Insufficient cash balance for position")
                return None

            # Create position
            position = Position(
                portfolio_id=portfolio_id,
                symbol=symbol,
                quantity=quantity,
                average_entry_price=entry_price,
                current_price=entry_price,
                position_type=position_type,
                is_open=1,
                stop_loss=stop_loss,
                take_profit=take_profit,
                notes=notes
            )

            # Update portfolio cash balance
            portfolio.cash_balance -= total_cost

            # Record transaction
            transaction = Transaction(
                portfolio_id=portfolio_id,
                symbol=symbol,
                transaction_type="BUY",
                quantity=quantity,
                price=entry_price,
                total_amount=total_cost,
                commission=0.0,
                notes=f"Opened {position_type} position"
            )

            self.db_session.add(position)
            self.db_session.add(transaction)
            self.db_session.commit()
            self.db_session.refresh(position)

            self.logger.info(f"Opened {position_type} position: {symbol} x {quantity} @ {entry_price}")
            return position

        except Exception as e:
            self.db_session.rollback()
            self.logger.error(f"Error opening position: {e}")
            raise

    def close_position(
        self,
        position_id: int,
        closing_price: Optional[float] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Close an existing position.

        Args:
            position_id: Position ID
            closing_price: Closing price (uses current market price if None)
            notes: Additional notes

        Returns:
            True if successful
        """
        try:
            position = self.db_session.query(Position).filter(
                Position.id == position_id
            ).first()

            if not position or not position.is_open:
                self.logger.error(f"Position {position_id} not found or already closed")
                return False

            # Get closing price
            if closing_price is None:
                closing_price = self._market_data_service.get_current_price(position.symbol)
                if closing_price is None:
                    closing_price = position.current_price

            # Calculate proceeds
            total_proceeds = position.quantity * closing_price

            # Update portfolio cash balance
            portfolio = self.get_portfolio(position.portfolio_id)
            if portfolio:
                portfolio.cash_balance += total_proceeds

            # Close position
            position.close_position(closing_price)

            # Record transaction
            transaction = Transaction(
                portfolio_id=position.portfolio_id,
                symbol=position.symbol,
                transaction_type="SELL",
                quantity=position.quantity,
                price=closing_price,
                total_amount=total_proceeds,
                commission=0.0,
                notes=notes or f"Closed {position.position_type} position"
            )

            self.db_session.add(transaction)
            self.db_session.commit()

            pnl = position.calculate_pnl()
            self.logger.info(f"Closed position {position_id}: {position.symbol}, P&L: {pnl:.2f}")
            return True

        except Exception as e:
            self.db_session.rollback()
            self.logger.error(f"Error closing position {position_id}: {e}")
            return False

    def update_position_prices(self, portfolio_id: Optional[int] = None) -> int:
        """
        Update current prices for all open positions.

        Args:
            portfolio_id: Update only positions in this portfolio (None for all)

        Returns:
            Number of positions updated
        """
        try:
            query = self.db_session.query(Position).filter(Position.is_open == 1)
            if portfolio_id:
                query = query.filter(Position.portfolio_id == portfolio_id)

            positions = query.all()
            updated_count = 0

            for position in positions:
                current_price = self._market_data_service.get_current_price(
                    position.symbol,
                    use_cache=True
                )
                if current_price:
                    position.update_price(current_price)
                    updated_count += 1

            self.db_session.commit()
            self.logger.info(f"Updated prices for {updated_count} positions")
            return updated_count

        except Exception as e:
            self.db_session.rollback()
            self.logger.error(f"Error updating position prices: {e}")
            return 0

    def get_portfolio_positions(
        self,
        portfolio_id: int,
        open_only: bool = True
    ) -> List[Position]:
        """
        Get positions for a portfolio.

        Args:
            portfolio_id: Portfolio ID
            open_only: Return only open positions

        Returns:
            List of positions
        """
        try:
            query = self.db_session.query(Position).filter(
                Position.portfolio_id == portfolio_id
            )
            if open_only:
                query = query.filter(Position.is_open == 1)
            return query.all()
        except Exception as e:
            self.logger.error(f"Error fetching positions: {e}")
            return []

    # ==================== Transaction Operations ====================

    def get_portfolio_transactions(
        self,
        portfolio_id: int,
        limit: Optional[int] = None
    ) -> List[Transaction]:
        """
        Get transactions for a portfolio.

        Args:
            portfolio_id: Portfolio ID
            limit: Maximum number of transactions to return

        Returns:
            List of transactions
        """
        try:
            query = self.db_session.query(Transaction).filter(
                Transaction.portfolio_id == portfolio_id
            ).order_by(Transaction.transaction_date.desc())

            if limit:
                query = query.limit(limit)

            return query.all()
        except Exception as e:
            self.logger.error(f"Error fetching transactions: {e}")
            return []

    def add_cash(
        self,
        portfolio_id: int,
        amount: float,
        notes: Optional[str] = None
    ) -> bool:
        """
        Add cash to portfolio.

        Args:
            portfolio_id: Portfolio ID
            amount: Amount to add
            notes: Transaction notes

        Returns:
            True if successful
        """
        try:
            portfolio = self.get_portfolio(portfolio_id)
            if not portfolio:
                return False

            portfolio.cash_balance += amount
            self.db_session.commit()

            self.logger.info(f"Added {amount} to portfolio {portfolio_id}")
            return True

        except Exception as e:
            self.db_session.rollback()
            self.logger.error(f"Error adding cash: {e}")
            return False

    def withdraw_cash(
        self,
        portfolio_id: int,
        amount: float,
        notes: Optional[str] = None
    ) -> bool:
        """
        Withdraw cash from portfolio.

        Args:
            portfolio_id: Portfolio ID
            amount: Amount to withdraw
            notes: Transaction notes

        Returns:
            True if successful
        """
        try:
            portfolio = self.get_portfolio(portfolio_id)
            if not portfolio:
                return False

            if portfolio.cash_balance < amount:
                self.logger.error("Insufficient cash balance")
                return False

            portfolio.cash_balance -= amount
            self.db_session.commit()

            self.logger.info(f"Withdrew {amount} from portfolio {portfolio_id}")
            return True

        except Exception as e:
            self.db_session.rollback()
            self.logger.error(f"Error withdrawing cash: {e}")
            return False

    # ==================== Analytics ====================

    def get_portfolio_summary(self, portfolio_id: int) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive portfolio summary.

        Args:
            portfolio_id: Portfolio ID

        Returns:
            Dictionary with portfolio metrics
        """
        try:
            portfolio = self.get_portfolio(portfolio_id)
            if not portfolio:
                return None

            # Update prices first
            self.update_position_prices(portfolio_id)
            self.db_session.refresh(portfolio)

            total_value = portfolio.calculate_total_value()
            total_pnl = portfolio.calculate_total_pnl()
            return_pct = portfolio.calculate_return_percentage()

            open_positions = portfolio.get_open_positions()
            positions_value = sum(pos.calculate_current_value() for pos in open_positions)

            summary = {
                'portfolio_id': portfolio_id,
                'name': portfolio.name,
                'initial_capital': portfolio.initial_capital,
                'cash_balance': portfolio.cash_balance,
                'positions_value': positions_value,
                'total_value': total_value,
                'total_pnl': total_pnl,
                'return_percentage': return_pct,
                'num_positions': len(open_positions),
                'currency': portfolio.currency,
                'is_active': bool(portfolio.is_active)
            }

            return summary

        except Exception as e:
            self.logger.error(f"Error generating portfolio summary: {e}")
            return None
