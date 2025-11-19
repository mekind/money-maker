"""
Risk Management Service.
Calculates risk metrics and provides risk management recommendations.
"""

from typing import Optional, Dict, List, Any, Tuple
import numpy as np
import pandas as pd
from scipy import stats
from services.base_service import BaseService
from services.market_data_service import MarketDataService
from services.portfolio_service import PortfolioService
from models import Portfolio, Position


class RiskManagementService(BaseService):
    """
    Service for risk management operations.
    Calculates risk metrics, position sizing, and portfolio risk.
    """

    def _initialize(self) -> None:
        """Initialize risk management service resources."""
        self._market_data_service = MarketDataService(self.settings)
        self._portfolio_service = PortfolioService(self.settings, self.db_session)
        self._risk_free_rate = self.settings.DEFAULT_RISK_FREE_RATE
        self.logger.info("RiskManagementService initialized")

    # ==================== Position Sizing ====================

    def calculate_position_size(
        self,
        portfolio_id: int,
        symbol: str,
        risk_per_trade: Optional[float] = None,
        stop_loss_percent: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate recommended position size based on risk parameters.

        Args:
            portfolio_id: Portfolio ID
            symbol: Stock symbol
            risk_per_trade: Risk per trade as decimal (default from settings)
            stop_loss_percent: Stop loss as decimal (default from settings)

        Returns:
            Dictionary with position sizing recommendations
        """
        try:
            portfolio = self._portfolio_service.get_portfolio(portfolio_id)
            if not portfolio:
                raise ValueError(f"Portfolio {portfolio_id} not found")

            if risk_per_trade is None:
                risk_per_trade = self.settings.DEFAULT_POSITION_SIZE_PERCENT

            if stop_loss_percent is None:
                stop_loss_percent = self.settings.DEFAULT_STOP_LOSS_PERCENT

            # Get current price
            current_price = self._market_data_service.get_current_price(symbol)
            if not current_price:
                raise ValueError(f"Could not fetch price for {symbol}")

            # Calculate risk amount
            portfolio_value = portfolio.calculate_total_value()
            risk_amount = portfolio_value * risk_per_trade

            # Calculate position size
            # Position Size = Risk Amount / (Entry Price * Stop Loss %)
            position_value = risk_amount / stop_loss_percent
            shares = int(position_value / current_price)

            # Calculate stop loss price
            stop_loss_price = current_price * (1 - stop_loss_percent)

            # Verify position doesn't exceed max allocation
            max_position_value = portfolio_value * self.settings.MAX_POSITION_SIZE_PERCENT
            actual_position_value = shares * current_price

            if actual_position_value > max_position_value:
                shares = int(max_position_value / current_price)
                actual_position_value = shares * current_price

            return {
                'symbol': symbol,
                'current_price': current_price,
                'recommended_shares': shares,
                'position_value': actual_position_value,
                'stop_loss_price': stop_loss_price,
                'stop_loss_percent': stop_loss_percent * 100,
                'risk_amount': risk_amount,
                'risk_percent': (actual_position_value / portfolio_value) * 100,
                'max_loss': shares * current_price * stop_loss_percent
            }

        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            raise

    def calculate_kelly_criterion(
        self,
        win_probability: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """
        Calculate Kelly Criterion for optimal position sizing.

        Args:
            win_probability: Probability of winning trade (0-1)
            avg_win: Average win amount
            avg_loss: Average loss amount

        Returns:
            Kelly percentage (0-1)
        """
        if avg_loss == 0:
            return 0.0

        win_loss_ratio = avg_win / abs(avg_loss)
        kelly = (win_probability * win_loss_ratio - (1 - win_probability)) / win_loss_ratio

        # Use fractional Kelly (50%) for safety
        return max(0, min(kelly * 0.5, 0.25))  # Cap at 25%

    # ==================== Portfolio Risk Metrics ====================

    def calculate_portfolio_var(
        self,
        portfolio_id: int,
        confidence_level: float = 0.95,
        time_horizon: int = 1
    ) -> Optional[Dict[str, float]]:
        """
        Calculate Portfolio Value at Risk (VaR).

        Args:
            portfolio_id: Portfolio ID
            confidence_level: Confidence level (0.90, 0.95, 0.99)
            time_horizon: Time horizon in days

        Returns:
            Dictionary with VaR metrics
        """
        try:
            portfolio = self._portfolio_service.get_portfolio(portfolio_id)
            if not portfolio:
                return None

            positions = portfolio.get_open_positions()
            if not positions:
                return {'var_amount': 0.0, 'var_percent': 0.0}

            portfolio_value = portfolio.calculate_total_value()
            returns_data = []

            # Collect historical returns for each position
            for position in positions:
                hist_data = self._market_data_service.get_historical_data(
                    position.symbol,
                    period='1y'
                )
                if hist_data is not None and not hist_data.empty:
                    returns = hist_data['Close'].pct_change().dropna()
                    weight = position.calculate_current_value() / portfolio_value
                    weighted_returns = returns * weight
                    returns_data.append(weighted_returns)

            if not returns_data:
                return None

            # Combine returns
            portfolio_returns = pd.concat(returns_data, axis=1).sum(axis=1)

            # Calculate VaR using historical method
            var_percentile = 1 - confidence_level
            var_return = np.percentile(portfolio_returns, var_percentile * 100)

            # Scale to time horizon
            var_scaled = var_return * np.sqrt(time_horizon)
            var_amount = portfolio_value * abs(var_scaled)

            return {
                'var_amount': var_amount,
                'var_percent': abs(var_scaled) * 100,
                'confidence_level': confidence_level,
                'time_horizon_days': time_horizon,
                'portfolio_value': portfolio_value
            }

        except Exception as e:
            self.logger.error(f"Error calculating VaR: {e}")
            return None

    def calculate_sharpe_ratio(
        self,
        portfolio_id: int,
        period: str = '1y'
    ) -> Optional[float]:
        """
        Calculate Sharpe Ratio for portfolio.

        Args:
            portfolio_id: Portfolio ID
            period: Historical period

        Returns:
            Sharpe ratio or None
        """
        try:
            # Get portfolio returns
            returns = self._get_portfolio_returns(portfolio_id, period)
            if returns is None or len(returns) < 2:
                return None

            # Calculate excess returns
            excess_returns = returns - (self._risk_free_rate / 252)  # Daily risk-free rate

            # Calculate Sharpe ratio
            sharpe = np.sqrt(252) * (excess_returns.mean() / excess_returns.std())

            return float(sharpe)

        except Exception as e:
            self.logger.error(f"Error calculating Sharpe ratio: {e}")
            return None

    def calculate_sortino_ratio(
        self,
        portfolio_id: int,
        period: str = '1y'
    ) -> Optional[float]:
        """
        Calculate Sortino Ratio (downside deviation version of Sharpe).

        Args:
            portfolio_id: Portfolio ID
            period: Historical period

        Returns:
            Sortino ratio or None
        """
        try:
            returns = self._get_portfolio_returns(portfolio_id, period)
            if returns is None or len(returns) < 2:
                return None

            # Calculate excess returns
            excess_returns = returns - (self._risk_free_rate / 252)

            # Calculate downside deviation (only negative returns)
            downside_returns = excess_returns[excess_returns < 0]
            downside_std = downside_returns.std()

            if downside_std == 0:
                return None

            sortino = np.sqrt(252) * (excess_returns.mean() / downside_std)

            return float(sortino)

        except Exception as e:
            self.logger.error(f"Error calculating Sortino ratio: {e}")
            return None

    def calculate_max_drawdown(
        self,
        portfolio_id: int,
        period: str = '1y'
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate maximum drawdown for portfolio.

        Args:
            portfolio_id: Portfolio ID
            period: Historical period

        Returns:
            Dictionary with drawdown metrics
        """
        try:
            returns = self._get_portfolio_returns(portfolio_id, period)
            if returns is None or len(returns) < 2:
                return None

            # Calculate cumulative returns
            cumulative = (1 + returns).cumprod()

            # Calculate running maximum
            running_max = cumulative.expanding().max()

            # Calculate drawdown
            drawdown = (cumulative - running_max) / running_max

            # Find maximum drawdown
            max_dd = drawdown.min()
            max_dd_idx = drawdown.idxmin()

            # Find peak before max drawdown
            peak_idx = cumulative[:max_dd_idx].idxmax()

            return {
                'max_drawdown_percent': abs(max_dd) * 100,
                'peak_date': peak_idx,
                'trough_date': max_dd_idx,
                'current_drawdown_percent': abs(drawdown.iloc[-1]) * 100
            }

        except Exception as e:
            self.logger.error(f"Error calculating max drawdown: {e}")
            return None

    def calculate_beta(
        self,
        symbol: str,
        benchmark: Optional[str] = None,
        period: str = '1y'
    ) -> Optional[float]:
        """
        Calculate beta relative to benchmark.

        Args:
            symbol: Stock symbol
            benchmark: Benchmark symbol (default: S&P 500)
            period: Historical period

        Returns:
            Beta value or None
        """
        try:
            if benchmark is None:
                benchmark = self.settings.DEFAULT_MARKET_INDEX

            # Get historical data
            stock_data = self._market_data_service.get_historical_data(symbol, period=period)
            benchmark_data = self._market_data_service.get_historical_data(benchmark, period=period)

            if stock_data is None or benchmark_data is None:
                return None

            # Calculate returns
            stock_returns = stock_data['Close'].pct_change().dropna()
            benchmark_returns = benchmark_data['Close'].pct_change().dropna()

            # Align data
            combined = pd.DataFrame({
                'stock': stock_returns,
                'benchmark': benchmark_returns
            }).dropna()

            if len(combined) < 30:
                return None

            # Calculate beta using covariance
            covariance = combined['stock'].cov(combined['benchmark'])
            benchmark_variance = combined['benchmark'].var()

            if benchmark_variance == 0:
                return None

            beta = covariance / benchmark_variance

            return float(beta)

        except Exception as e:
            self.logger.error(f"Error calculating beta: {e}")
            return None

    def calculate_correlation_matrix(
        self,
        portfolio_id: int,
        period: str = '6mo'
    ) -> Optional[pd.DataFrame]:
        """
        Calculate correlation matrix for portfolio positions.

        Args:
            portfolio_id: Portfolio ID
            period: Historical period

        Returns:
            Correlation matrix DataFrame or None
        """
        try:
            portfolio = self._portfolio_service.get_portfolio(portfolio_id)
            if not portfolio:
                return None

            positions = portfolio.get_open_positions()
            if len(positions) < 2:
                return None

            # Collect returns for each position
            returns_dict = {}
            for position in positions:
                hist_data = self._market_data_service.get_historical_data(
                    position.symbol,
                    period=period
                )
                if hist_data is not None and not hist_data.empty:
                    returns = hist_data['Close'].pct_change().dropna()
                    returns_dict[position.symbol] = returns

            if len(returns_dict) < 2:
                return None

            # Create DataFrame and calculate correlation
            returns_df = pd.DataFrame(returns_dict).dropna()
            correlation_matrix = returns_df.corr()

            return correlation_matrix

        except Exception as e:
            self.logger.error(f"Error calculating correlation matrix: {e}")
            return None

    # ==================== Risk Assessment ====================

    def assess_position_risk(self, position_id: int) -> Optional[Dict[str, Any]]:
        """
        Assess risk for a specific position.

        Args:
            position_id: Position ID

        Returns:
            Dictionary with risk assessment
        """
        try:
            position = self.db_session.query(Position).filter(
                Position.id == position_id
            ).first()

            if not position or not position.is_open:
                return None

            # Get volatility
            volatility = self._market_data_service.calculate_volatility(
                position.symbol,
                period='1y',
                window=30
            )

            # Get beta
            beta = self.calculate_beta(position.symbol)

            # Calculate current P&L
            current_pnl = position.calculate_pnl()
            pnl_percent = position.calculate_pnl_percentage()

            # Risk level assessment
            risk_level = "LOW"
            if volatility and volatility > 0.4:
                risk_level = "HIGH"
            elif volatility and volatility > 0.25:
                risk_level = "MEDIUM"

            return {
                'position_id': position_id,
                'symbol': position.symbol,
                'current_pnl': current_pnl,
                'pnl_percent': pnl_percent,
                'volatility': volatility,
                'beta': beta,
                'risk_level': risk_level,
                'has_stop_loss': position.stop_loss is not None,
                'stop_loss_price': position.stop_loss,
                'current_price': position.current_price
            }

        except Exception as e:
            self.logger.error(f"Error assessing position risk: {e}")
            return None

    def get_portfolio_risk_summary(self, portfolio_id: int) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive risk summary for portfolio.

        Args:
            portfolio_id: Portfolio ID

        Returns:
            Dictionary with risk metrics
        """
        try:
            var_metrics = self.calculate_portfolio_var(portfolio_id)
            sharpe = self.calculate_sharpe_ratio(portfolio_id)
            sortino = self.calculate_sortino_ratio(portfolio_id)
            max_dd = self.calculate_max_drawdown(portfolio_id)

            return {
                'value_at_risk': var_metrics,
                'sharpe_ratio': sharpe,
                'sortino_ratio': sortino,
                'max_drawdown': max_dd
            }

        except Exception as e:
            self.logger.error(f"Error generating risk summary: {e}")
            return None

    # ==================== Helper Methods ====================

    def _get_portfolio_returns(
        self,
        portfolio_id: int,
        period: str
    ) -> Optional[pd.Series]:
        """
        Calculate portfolio returns based on positions.

        Args:
            portfolio_id: Portfolio ID
            period: Historical period

        Returns:
            Series of portfolio returns or None
        """
        try:
            portfolio = self._portfolio_service.get_portfolio(portfolio_id)
            if not portfolio:
                return None

            positions = portfolio.get_open_positions()
            if not positions:
                return None

            portfolio_value = portfolio.calculate_total_value()
            returns_data = []

            for position in positions:
                hist_data = self._market_data_service.get_historical_data(
                    position.symbol,
                    period=period
                )
                if hist_data is not None and not hist_data.empty:
                    returns = hist_data['Close'].pct_change().dropna()
                    weight = position.calculate_current_value() / portfolio_value
                    weighted_returns = returns * weight
                    returns_data.append(weighted_returns)

            if not returns_data:
                return None

            portfolio_returns = pd.concat(returns_data, axis=1).sum(axis=1)
            return portfolio_returns

        except Exception as e:
            self.logger.error(f"Error calculating portfolio returns: {e}")
            return None
