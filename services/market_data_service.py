"""
Market Data Service for fetching and processing market data.
Uses Singleton pattern and follows OOP principles.
"""

from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta, timezone
from threading import Lock
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from services.base_service import BaseService


class MarketDataService(BaseService):
    """
    Singleton service for market data operations.
    Handles fetching prices, technical indicators, and fundamental data.
    """

    _instance: Optional['MarketDataService'] = None
    _lock: Lock = Lock()
    _cache: Dict[str, Dict[str, Any]] = {}

    def __new__(cls, *args, **kwargs) -> 'MarketDataService':
        """
        Thread-safe singleton implementation.

        Returns:
            MarketDataService instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(MarketDataService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, settings=None, db_session=None):
        """Initialize market data service."""
        if self._initialized:
            return
        super().__init__(settings, db_session)

    def _initialize(self) -> None:
        """Initialize service resources."""
        self._cache_ttl = self.settings.MARKET_DATA_CACHE_TTL
        self._default_currency = self.settings.DEFAULT_CURRENCY
        self.logger.info("MarketDataService initialized")

    def get_current_price(self, symbol: str, use_cache: bool = True) -> Optional[float]:
        """
        Get current market price for a symbol.

        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'MSFT')
            use_cache: Whether to use cached data

        Returns:
            Current price or None if unavailable
        """
        try:
            if use_cache and self._is_cache_valid(symbol, 'price'):
                return self._cache[symbol]['price']['value']

            ticker = yf.Ticker(symbol)
            data = ticker.history(period='1d', interval='1m')

            if data.empty:
                self.logger.warning(f"No price data available for {symbol}")
                return None

            current_price = float(data['Close'].iloc[-1])

            # Cache the result
            self._update_cache(symbol, 'price', current_price)

            return current_price

        except Exception as e:
            self.logger.error(f"Error fetching price for {symbol}: {e}")
            return None

    def get_historical_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = '1y',
        interval: str = '1d'
    ) -> Optional[pd.DataFrame]:
        """
        Get historical market data.

        Args:
            symbol: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            period: Period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

        Returns:
            DataFrame with OHLCV data or None if unavailable
        """
        try:
            ticker = yf.Ticker(symbol)

            if start_date and end_date:
                data = ticker.history(start=start_date, end=end_date, interval=interval)
            else:
                data = ticker.history(period=period, interval=interval)

            if data.empty:
                self.logger.warning(f"No historical data available for {symbol}")
                return None

            return data

        except Exception as e:
            self.logger.error(f"Error fetching historical data for {symbol}: {e}")
            return None

    def calculate_technical_indicators(
        self,
        symbol: str,
        period: str = '3mo'
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate technical indicators for a symbol.

        Args:
            symbol: Stock symbol
            period: Historical period for calculation

        Returns:
            Dictionary of technical indicators
        """
        try:
            data = self.get_historical_data(symbol, period=period)

            if data is None or data.empty:
                return None

            # Calculate indicators using pandas_ta
            indicators = {}

            # Moving Averages
            data.ta.sma(length=20, append=True)
            data.ta.sma(length=50, append=True)
            data.ta.sma(length=200, append=True)
            data.ta.ema(length=12, append=True)
            data.ta.ema(length=26, append=True)

            indicators['SMA_20'] = float(data['SMA_20'].iloc[-1]) if 'SMA_20' in data else None
            indicators['SMA_50'] = float(data['SMA_50'].iloc[-1]) if 'SMA_50' in data else None
            indicators['SMA_200'] = float(data['SMA_200'].iloc[-1]) if 'SMA_200' in data else None
            indicators['EMA_12'] = float(data['EMA_12'].iloc[-1]) if 'EMA_12' in data else None
            indicators['EMA_26'] = float(data['EMA_26'].iloc[-1]) if 'EMA_26' in data else None

            # RSI (Relative Strength Index)
            data.ta.rsi(length=14, append=True)
            indicators['RSI_14'] = float(data['RSI_14'].iloc[-1]) if 'RSI_14' in data else None

            # MACD
            data.ta.macd(append=True)
            indicators['MACD'] = float(data['MACD_12_26_9'].iloc[-1]) if 'MACD_12_26_9' in data else None
            indicators['MACD_signal'] = float(data['MACDs_12_26_9'].iloc[-1]) if 'MACDs_12_26_9' in data else None
            indicators['MACD_histogram'] = float(data['MACDh_12_26_9'].iloc[-1]) if 'MACDh_12_26_9' in data else None

            # Bollinger Bands
            data.ta.bbands(length=20, append=True)
            indicators['BB_upper'] = float(data['BBU_20_2.0'].iloc[-1]) if 'BBU_20_2.0' in data else None
            indicators['BB_middle'] = float(data['BBM_20_2.0'].iloc[-1]) if 'BBM_20_2.0' in data else None
            indicators['BB_lower'] = float(data['BBL_20_2.0'].iloc[-1]) if 'BBL_20_2.0' in data else None

            # Volume indicators
            data.ta.obv(append=True)
            indicators['OBV'] = float(data['OBV'].iloc[-1]) if 'OBV' in data else None

            # Current price
            indicators['current_price'] = float(data['Close'].iloc[-1])

            # Cache the result
            self._update_cache(symbol, 'indicators', indicators)

            return indicators

        except Exception as e:
            self.logger.error(f"Error calculating technical indicators for {symbol}: {e}")
            return None

    def get_fundamental_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get fundamental data for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary of fundamental data
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            fundamentals = {
                'market_cap': info.get('marketCap'),
                'enterprise_value': info.get('enterpriseValue'),
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'peg_ratio': info.get('pegRatio'),
                'price_to_book': info.get('priceToBook'),
                'price_to_sales': info.get('priceToSalesTrailing12Months'),
                'profit_margin': info.get('profitMargins'),
                'operating_margin': info.get('operatingMargins'),
                'roe': info.get('returnOnEquity'),
                'roa': info.get('returnOnAssets'),
                'revenue': info.get('totalRevenue'),
                'revenue_per_share': info.get('revenuePerShare'),
                'earnings_growth': info.get('earningsGrowth'),
                'revenue_growth': info.get('revenueGrowth'),
                'debt_to_equity': info.get('debtToEquity'),
                'current_ratio': info.get('currentRatio'),
                'quick_ratio': info.get('quickRatio'),
                'dividend_yield': info.get('dividendYield'),
                'payout_ratio': info.get('payoutRatio'),
                'beta': info.get('beta'),
                '52_week_high': info.get('fiftyTwoWeekHigh'),
                '52_week_low': info.get('fiftyTwoWeekLow'),
                'avg_volume': info.get('averageVolume'),
                'shares_outstanding': info.get('sharesOutstanding'),
            }

            # Cache the result
            self._update_cache(symbol, 'fundamentals', fundamentals)

            return fundamentals

        except Exception as e:
            self.logger.error(f"Error fetching fundamental data for {symbol}: {e}")
            return None

    def get_company_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get company information.

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary of company info
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            company_info = {
                'name': info.get('longName'),
                'symbol': symbol,
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'website': info.get('website'),
                'description': info.get('longBusinessSummary'),
                'employees': info.get('fullTimeEmployees'),
                'city': info.get('city'),
                'state': info.get('state'),
                'country': info.get('country'),
            }

            return company_info

        except Exception as e:
            self.logger.error(f"Error fetching company info for {symbol}: {e}")
            return None

    def calculate_volatility(
        self,
        symbol: str,
        period: str = '1y',
        window: int = 30
    ) -> Optional[float]:
        """
        Calculate historical volatility (annualized standard deviation).

        Args:
            symbol: Stock symbol
            period: Historical period
            window: Rolling window in days

        Returns:
            Annualized volatility or None
        """
        try:
            data = self.get_historical_data(symbol, period=period)

            if data is None or data.empty:
                return None

            # Calculate daily returns
            returns = data['Close'].pct_change().dropna()

            # Calculate rolling standard deviation
            volatility = returns.rolling(window=window).std().iloc[-1]

            # Annualize (assuming 252 trading days)
            annualized_volatility = volatility * (252 ** 0.5)

            return float(annualized_volatility)

        except Exception as e:
            self.logger.error(f"Error calculating volatility for {symbol}: {e}")
            return None

    def _is_cache_valid(self, symbol: str, data_type: str) -> bool:
        """
        Check if cached data is still valid.

        Args:
            symbol: Stock symbol
            data_type: Type of data (price, indicators, fundamentals)

        Returns:
            True if cache is valid
        """
        if symbol not in self._cache or data_type not in self._cache[symbol]:
            return False

        cache_entry = self._cache[symbol][data_type]
        cache_time = cache_entry.get('timestamp')

        if cache_time is None:
            return False

        time_diff = (datetime.now(timezone.utc) - cache_time).total_seconds()
        return time_diff < self._cache_ttl

    def _update_cache(self, symbol: str, data_type: str, value: Any) -> None:
        """
        Update cache with new data.

        Args:
            symbol: Stock symbol
            data_type: Type of data
            value: Data value to cache
        """
        if symbol not in self._cache:
            self._cache[symbol] = {}

        self._cache[symbol][data_type] = {
            'value': value,
            'timestamp': datetime.now(timezone.utc)
        }

    def clear_cache(self, symbol: Optional[str] = None) -> None:
        """
        Clear cached data.

        Args:
            symbol: Specific symbol to clear, or None to clear all
        """
        if symbol:
            self._cache.pop(symbol, None)
            self.logger.info(f"Cache cleared for {symbol}")
        else:
            self._cache.clear()
            self.logger.info("All cache cleared")

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance. Useful for testing."""
        with cls._lock:
            if cls._instance:
                cls._instance.close()
                cls._instance = None
