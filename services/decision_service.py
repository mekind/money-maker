"""
Decision Engine Service with AI integration.
Generates trading recommendations using technical analysis, fundamentals, and AI reasoning.
"""

from typing import Optional, Dict, List, Any
import json
from datetime import datetime, timezone
from anthropic import Anthropic
from services.base_service import BaseService
from services.market_data_service import MarketDataService
from services.risk_service import RiskManagementService
from services.portfolio_service import PortfolioService
from models import Decision


class DecisionEngineService(BaseService):
    """
    AI-powered decision engine for trading recommendations.
    Combines technical analysis, fundamental data, and AI reasoning.
    """

    def _initialize(self) -> None:
        """Initialize decision engine service resources."""
        self._market_data_service = MarketDataService(self.settings)
        self._risk_service = RiskManagementService(self.settings, self.db_session)
        self._portfolio_service = PortfolioService(self.settings, self.db_session)

        # Initialize AI client if enabled
        self._ai_client = None
        if self.settings.ENABLE_AI_REASONING and self.settings.has_anthropic_key():
            self._ai_client = Anthropic(api_key=self.settings.ANTHROPIC_API_KEY)

        self._min_confidence = self.settings.MIN_CONFIDENCE_THRESHOLD
        self.logger.info("DecisionEngineService initialized")

    # ==================== Decision Generation ====================

    def generate_decision(
        self,
        portfolio_id: int,
        symbol: str,
        use_ai_reasoning: Optional[bool] = None
    ) -> Optional[Decision]:
        """
        Generate trading decision for a symbol.

        Args:
            portfolio_id: Portfolio ID
            symbol: Stock symbol
            use_ai_reasoning: Use AI for reasoning (default from settings)

        Returns:
            Decision object or None
        """
        try:
            # Gather market data
            technical_signals = self._analyze_technical_signals(symbol)
            fundamental_signals = self._analyze_fundamental_signals(symbol)
            risk_signals = self._analyze_risk_signals(symbol)

            if not technical_signals:
                self.logger.warning(f"Could not generate technical signals for {symbol}")
                return None

            # Calculate base decision
            decision_type, confidence = self._calculate_decision(
                technical_signals,
                fundamental_signals,
                risk_signals
            )

            # Get position sizing recommendation
            position_size = None
            if decision_type == "BUY":
                try:
                    sizing = self._risk_service.calculate_position_size(
                        portfolio_id,
                        symbol
                    )
                    position_size = sizing
                except Exception as e:
                    self.logger.warning(f"Could not calculate position size: {e}")

            # Generate AI reasoning if enabled
            reasoning = None
            if use_ai_reasoning is None:
                use_ai_reasoning = self.settings.ENABLE_AI_REASONING

            if use_ai_reasoning and self._ai_client:
                reasoning = self._generate_ai_reasoning(
                    symbol,
                    decision_type,
                    technical_signals,
                    fundamental_signals,
                    risk_signals,
                    confidence
                )

            # Create decision record
            decision = Decision(
                portfolio_id=portfolio_id,
                symbol=symbol,
                decision_type=decision_type,
                recommended_quantity=position_size.get('recommended_shares') if position_size else None,
                recommended_price=technical_signals.get('current_price'),
                confidence_score=confidence,
                reasoning=reasoning,
                technical_signals=json.dumps(technical_signals),
                fundamental_signals=json.dumps(fundamental_signals) if fundamental_signals else None,
                risk_assessment=json.dumps(risk_signals) if risk_signals else None,
                status="PENDING"
            )

            self.db_session.add(decision)
            self.db_session.commit()
            self.db_session.refresh(decision)

            self.logger.info(
                f"Generated {decision_type} decision for {symbol} "
                f"with confidence {confidence:.2f}"
            )

            return decision

        except Exception as e:
            self.db_session.rollback()
            self.logger.error(f"Error generating decision for {symbol}: {e}")
            return None

    def _analyze_technical_signals(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Analyze technical indicators to generate signals.

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary of technical signals
        """
        try:
            indicators = self._market_data_service.calculate_technical_indicators(symbol)
            if not indicators:
                return None

            signals = {}
            score = 0
            max_score = 0

            current_price = indicators.get('current_price')
            signals['current_price'] = current_price

            # Moving Average signals
            if indicators.get('SMA_20') and indicators.get('SMA_50'):
                max_score += 1
                if indicators['SMA_20'] > indicators['SMA_50']:
                    score += 1
                    signals['ma_trend'] = 'BULLISH'
                else:
                    signals['ma_trend'] = 'BEARISH'

            # Golden Cross / Death Cross
            if indicators.get('SMA_50') and indicators.get('SMA_200'):
                max_score += 1
                if indicators['SMA_50'] > indicators['SMA_200']:
                    score += 1
                    signals['long_term_trend'] = 'BULLISH'
                else:
                    signals['long_term_trend'] = 'BEARISH'

            # RSI signals
            rsi = indicators.get('RSI_14')
            if rsi:
                max_score += 1
                if rsi < 30:
                    score += 1
                    signals['rsi_signal'] = 'OVERSOLD'
                elif rsi > 70:
                    signals['rsi_signal'] = 'OVERBOUGHT'
                else:
                    score += 0.5
                    signals['rsi_signal'] = 'NEUTRAL'
                signals['rsi_value'] = rsi

            # MACD signals
            macd = indicators.get('MACD')
            macd_signal = indicators.get('MACD_signal')
            if macd and macd_signal:
                max_score += 1
                if macd > macd_signal:
                    score += 1
                    signals['macd_signal'] = 'BULLISH'
                else:
                    signals['macd_signal'] = 'BEARISH'

            # Bollinger Bands signals
            bb_upper = indicators.get('BB_upper')
            bb_lower = indicators.get('BB_lower')
            if bb_upper and bb_lower and current_price:
                max_score += 1
                if current_price < bb_lower:
                    score += 1
                    signals['bb_signal'] = 'OVERSOLD'
                elif current_price > bb_upper:
                    signals['bb_signal'] = 'OVERBOUGHT'
                else:
                    score += 0.5
                    signals['bb_signal'] = 'NORMAL'

            # Calculate technical score
            signals['technical_score'] = score / max_score if max_score > 0 else 0.5
            signals['indicators'] = indicators

            return signals

        except Exception as e:
            self.logger.error(f"Error analyzing technical signals: {e}")
            return None

    def _analyze_fundamental_signals(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Analyze fundamental data to generate signals.

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary of fundamental signals
        """
        try:
            fundamentals = self._market_data_service.get_fundamental_data(symbol)
            if not fundamentals:
                return None

            signals = {}
            score = 0
            max_score = 0

            # P/E Ratio analysis
            pe_ratio = fundamentals.get('pe_ratio')
            if pe_ratio and pe_ratio > 0:
                max_score += 1
                if pe_ratio < 15:
                    score += 1
                    signals['pe_signal'] = 'UNDERVALUED'
                elif pe_ratio < 25:
                    score += 0.5
                    signals['pe_signal'] = 'FAIR'
                else:
                    signals['pe_signal'] = 'OVERVALUED'
                signals['pe_ratio'] = pe_ratio

            # Growth metrics
            earnings_growth = fundamentals.get('earnings_growth')
            revenue_growth = fundamentals.get('revenue_growth')
            if earnings_growth and revenue_growth:
                max_score += 1
                if earnings_growth > 0.15 and revenue_growth > 0.10:
                    score += 1
                    signals['growth_signal'] = 'STRONG'
                elif earnings_growth > 0 and revenue_growth > 0:
                    score += 0.5
                    signals['growth_signal'] = 'MODERATE'
                else:
                    signals['growth_signal'] = 'WEAK'

            # Profitability metrics
            profit_margin = fundamentals.get('profit_margin')
            roe = fundamentals.get('roe')
            if profit_margin and roe:
                max_score += 1
                if profit_margin > 0.15 and roe > 0.15:
                    score += 1
                    signals['profitability_signal'] = 'STRONG'
                elif profit_margin > 0 and roe > 0:
                    score += 0.5
                    signals['profitability_signal'] = 'MODERATE'
                else:
                    signals['profitability_signal'] = 'WEAK'

            # Financial health
            debt_to_equity = fundamentals.get('debt_to_equity')
            current_ratio = fundamentals.get('current_ratio')
            if debt_to_equity is not None and current_ratio:
                max_score += 1
                if debt_to_equity < 0.5 and current_ratio > 1.5:
                    score += 1
                    signals['financial_health'] = 'STRONG'
                elif debt_to_equity < 1.0 and current_ratio > 1.0:
                    score += 0.5
                    signals['financial_health'] = 'MODERATE'
                else:
                    signals['financial_health'] = 'WEAK'

            signals['fundamental_score'] = score / max_score if max_score > 0 else 0.5
            signals['fundamentals'] = fundamentals

            return signals

        except Exception as e:
            self.logger.error(f"Error analyzing fundamental signals: {e}")
            return None

    def _analyze_risk_signals(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Analyze risk metrics.

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary of risk signals
        """
        try:
            volatility = self._market_data_service.calculate_volatility(symbol)
            beta = self._risk_service.calculate_beta(symbol)

            signals = {}

            if volatility:
                signals['volatility'] = volatility
                if volatility < 0.2:
                    signals['volatility_level'] = 'LOW'
                elif volatility < 0.4:
                    signals['volatility_level'] = 'MEDIUM'
                else:
                    signals['volatility_level'] = 'HIGH'

            if beta:
                signals['beta'] = beta
                if abs(beta - 1.0) < 0.3:
                    signals['beta_level'] = 'MARKET'
                elif beta > 1.3:
                    signals['beta_level'] = 'HIGH'
                elif beta < 0.7:
                    signals['beta_level'] = 'LOW'
                else:
                    signals['beta_level'] = 'MODERATE'

            return signals

        except Exception as e:
            self.logger.error(f"Error analyzing risk signals: {e}")
            return None

    def _calculate_decision(
        self,
        technical_signals: Dict[str, Any],
        fundamental_signals: Optional[Dict[str, Any]],
        risk_signals: Optional[Dict[str, Any]]
    ) -> tuple[str, float]:
        """
        Calculate final decision and confidence based on all signals.

        Args:
            technical_signals: Technical analysis signals
            fundamental_signals: Fundamental analysis signals
            risk_signals: Risk analysis signals

        Returns:
            Tuple of (decision_type, confidence_score)
        """
        # Weight the scores
        tech_weight = 0.5
        fund_weight = 0.3
        risk_weight = 0.2

        tech_score = technical_signals.get('technical_score', 0.5)
        fund_score = fundamental_signals.get('fundamental_score', 0.5) if fundamental_signals else 0.5

        # Risk adjustment
        risk_adjustment = 1.0
        if risk_signals:
            volatility_level = risk_signals.get('volatility_level')
            if volatility_level == 'HIGH':
                risk_adjustment = 0.8
            elif volatility_level == 'LOW':
                risk_adjustment = 1.0

        # Calculate weighted score
        total_score = (
            tech_score * tech_weight +
            fund_score * fund_weight
        ) * risk_adjustment

        # Determine decision
        if total_score >= 0.65:
            decision_type = "BUY"
            confidence = min(total_score, 0.95)
        elif total_score <= 0.35:
            decision_type = "SELL"
            confidence = min(1 - total_score, 0.95)
        else:
            decision_type = "HOLD"
            confidence = 1 - abs(total_score - 0.5) * 2

        return decision_type, confidence

    def _generate_ai_reasoning(
        self,
        symbol: str,
        decision_type: str,
        technical_signals: Dict[str, Any],
        fundamental_signals: Optional[Dict[str, Any]],
        risk_signals: Optional[Dict[str, Any]],
        confidence: float
    ) -> str:
        """
        Generate AI-powered reasoning for the decision.

        Args:
            symbol: Stock symbol
            decision_type: BUY, SELL, or HOLD
            technical_signals: Technical signals
            fundamental_signals: Fundamental signals
            risk_signals: Risk signals
            confidence: Confidence score

        Returns:
            AI-generated reasoning text
        """
        try:
            if not self._ai_client:
                return f"Recommendation: {decision_type} with {confidence:.1%} confidence based on technical and fundamental analysis."

            # Prepare context for AI
            context = f"""
Analyze the following trading signals for {symbol} and provide a concise explanation for the {decision_type} recommendation.

Technical Signals:
- Trend: {technical_signals.get('ma_trend', 'N/A')}
- Long-term Trend: {technical_signals.get('long_term_trend', 'N/A')}
- RSI: {technical_signals.get('rsi_value', 'N/A')} ({technical_signals.get('rsi_signal', 'N/A')})
- MACD: {technical_signals.get('macd_signal', 'N/A')}
- Bollinger Bands: {technical_signals.get('bb_signal', 'N/A')}

"""

            if fundamental_signals:
                context += f"""Fundamental Signals:
- P/E Ratio: {fundamental_signals.get('pe_signal', 'N/A')}
- Growth: {fundamental_signals.get('growth_signal', 'N/A')}
- Profitability: {fundamental_signals.get('profitability_signal', 'N/A')}
- Financial Health: {fundamental_signals.get('financial_health', 'N/A')}

"""

            if risk_signals:
                context += f"""Risk Assessment:
- Volatility: {risk_signals.get('volatility_level', 'N/A')}
- Beta: {risk_signals.get('beta_level', 'N/A')}

"""

            context += f"Confidence Score: {confidence:.1%}\n\nProvide a 2-3 sentence explanation focusing on the key factors driving this {decision_type} recommendation."

            # Call Claude API
            message = self._ai_client.messages.create(
                model=self.settings.AI_MODEL,
                max_tokens=300,
                messages=[{
                    "role": "user",
                    "content": context
                }]
            )

            reasoning = message.content[0].text
            return reasoning

        except Exception as e:
            self.logger.error(f"Error generating AI reasoning: {e}")
            return f"Recommendation: {decision_type} with {confidence:.1%} confidence based on quantitative analysis."

    # ==================== Decision Management ====================

    def get_portfolio_decisions(
        self,
        portfolio_id: int,
        status: Optional[str] = None,
        limit: int = 10
    ) -> List[Decision]:
        """
        Get decisions for a portfolio.

        Args:
            portfolio_id: Portfolio ID
            status: Filter by status (PENDING, ACCEPTED, REJECTED, EXECUTED)
            limit: Maximum number of decisions

        Returns:
            List of decisions
        """
        try:
            query = self.db_session.query(Decision).filter(
                Decision.portfolio_id == portfolio_id
            )

            if status:
                query = query.filter(Decision.status == status)

            query = query.order_by(Decision.decision_date.desc()).limit(limit)

            return query.all()

        except Exception as e:
            self.logger.error(f"Error fetching decisions: {e}")
            return []

    def execute_decision(self, decision_id: int) -> bool:
        """
        Execute a decision (create actual position).

        Args:
            decision_id: Decision ID

        Returns:
            True if successful
        """
        try:
            decision = self.db_session.query(Decision).filter(
                Decision.id == decision_id
            ).first()

            if not decision or decision.status != "ACCEPTED":
                return False

            if decision.decision_type == "BUY" and decision.recommended_quantity:
                # Open position
                position = self._portfolio_service.open_position(
                    portfolio_id=decision.portfolio_id,
                    symbol=decision.symbol,
                    quantity=decision.recommended_quantity,
                    entry_price=decision.recommended_price or decision.symbol,  # Should use current price
                    position_type="LONG"
                )

                if position:
                    decision.mark_executed(position.current_price)
                    self.db_session.commit()
                    return True

            return False

        except Exception as e:
            self.db_session.rollback()
            self.logger.error(f"Error executing decision: {e}")
            return False
