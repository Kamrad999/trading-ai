"""
Hybrid trading strategy combining news sentiment and technical analysis.
Following Freqtrade patterns for multi-factor signal generation.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from .base_strategy import BaseStrategy
from .strategy_interface import StrategyContext, StrategyOutput
from ..core.models import Signal, SignalDirection, Urgency, MarketRegime, SignalType
from ..infrastructure.logging import get_logger


class HybridStrategy(BaseStrategy):
    """
    Hybrid strategy that combines news sentiment and technical analysis.
    
    Following patterns from:
    - Freqtrade: Multi-factor strategy system
    - ai-trade: LLM-based decision integration
    - VectorBT: Signal combination and weighting
    """
    
    def __init__(self, **kwargs):
        """Initialize hybrid strategy."""
        super().__init__("HybridStrategy", **kwargs)
        
        # Strategy weights
        self.news_weight = kwargs.get("news_weight", 0.4)
        self.technical_weight = kwargs.get("technical_weight", 0.6)
        
        # Combination thresholds
        self.min_combined_confidence = kwargs.get("min_combined_confidence", 0.5)
        self.conflict_threshold = kwargs.get("conflict_threshold", 0.3)
        self.agreement_bonus = kwargs.get("agreement_bonus", 0.2)
        
        # Confluence requirements (enabled for quality signals)
        self.require_confluence = kwargs.get("require_confluence", True)
        self.min_confluence_score = kwargs.get("min_confluence_score", 0.6)
        
        # Risk adjustments
        self.hybrid_stop_loss = kwargs.get("hybrid_stop_loss", 0.05)
        self.hybrid_take_profit = kwargs.get("hybrid_take_profit", 0.10)
        
        # Entry filters to avoid bad trades (RELAXED for 20-100 trades/month target)
        self.max_momentum_pct = kwargs.get("max_momentum_pct", 0.08)  # Don't chase >8% moves (was 5%)
        self.momentum_lookback = kwargs.get("momentum_lookback", 5)  # Check last 5 bars
        self.min_signal_count = kwargs.get("min_signal_count", 1)  # Need 1+ confirming signals (was 2)
        self.trade_cooldown_bars = kwargs.get("trade_cooldown_bars", 5)  # Min 5 bars between trades (was 10)
        
        # Track last trade time per symbol for cooldown
        self.last_trade_time = {}  # symbol -> timestamp
        
        self.logger.info(f"HybridStrategy initialized with news_weight={self.news_weight}, technical_weight={self.technical_weight}")
    
    def analyze(self, context: StrategyContext) -> StrategyOutput:
        """
        Analyze market conditions and generate trading signals.
        Required by IStrategy abstract base class.
        
        Args:
            context: Current market context
            
        Returns:
            StrategyOutput with signals and position adjustments
        """
        return self.execute(context)
    
    def execute(self, context: StrategyContext) -> StrategyOutput:
        """
        Execute hybrid strategy combining news and technical analysis.
        
        Args:
            context: Current market context
            
        Returns:
            Strategy output with combined signals
        """
        signals = []
        
        try:
            # Get symbols from metadata (backtest compatibility)
            symbols = context.metadata.get('symbols', list(context.market_data.keys()))
            
            # Process each symbol
            for symbol in symbols:
                # Get news analysis
                news_analysis = self._analyze_news_sentiment(symbol, context)
                
                # Get technical analysis
                technical_analysis = self._analyze_technicals(symbol, context)
                
                # Combine analyses
                combined_analysis = self._combine_analyses(news_analysis, technical_analysis)
                
                # Generate hybrid signal
                signal = self._generate_hybrid_signal(symbol, combined_analysis, context)
                if signal and self.validate_signal(signal, context):
                    signals.append(signal)
            
            self.logger.info(f"HybridStrategy generated {len(signals)} signals")
            
            return StrategyOutput(
                signals=signals,
                position_adjustments={},  # No position adjustments in this strategy
                risk_adjustments={},  # No risk adjustments in this strategy
                metadata={
                    "strategy": "HybridStrategy",
                    "processed_symbols": len(symbols),
                    "combination_method": "weighted_average",
                    "news_weight": self.news_weight,
                    "technical_weight": self.technical_weight
                }
            )
            
        except Exception as e:
            self.logger.error(f"HybridStrategy execution failed: {e}")
            return StrategyOutput(
                signals=signals,
                position_adjustments={},
                risk_adjustments={},
                metadata={"strategy": "HybridStrategy", "error": str(e)}
            )
    
    def _analyze_news_sentiment(self, symbol: str, context: StrategyContext) -> Dict[str, Any]:
        """Analyze news sentiment for a symbol."""
        news_data = context.metadata.get("news_data", [])
        
        if not news_data:
            return {
                "signal": 0.0,
                "confidence": 0.0,
                "strength": 0.0,
                "valid": False,
                "reason": "no_news",
                "conditions": ["No news data available"]
            }
        
        # Get symbol-specific news
        symbol_news = self._get_symbol_news(symbol, news_data)
        if not symbol_news:
            return {
                "signal": 0.0,
                "confidence": 0.0,
                "strength": 0.0,
                "valid": False,
                "reason": "no_symbol_news",
                "conditions": [f"No news found for {symbol}"]
            }
        
        # Calculate sentiment
        total_sentiment = 0.0
        total_weight = 0.0
        
        for article in symbol_news:
            sentiment = article.get("sentiment", 0.0)
            weight = article.get("relevance", 1.0)
            
            total_sentiment += sentiment * weight
            total_weight += weight
        
        if total_weight == 0:
            return {
                "signal": 0.0,
                "confidence": 0.0,
                "strength": 0.0,
                "valid": False,
                "reason": "no_weight",
                "conditions": ["News articles have no weight"]
            }
        
        avg_sentiment = total_sentiment / total_weight
        signal_strength = abs(avg_sentiment)
        
        direction = "bullish" if avg_sentiment > 0 else "bearish" if avg_sentiment < 0 else "neutral"
        return {
            "signal": avg_sentiment,
            "confidence": min(0.9, signal_strength),
            "strength": signal_strength,
            "valid": True,
            "article_count": len(symbol_news),
            "direction": direction,
            "conditions": [f"News sentiment: {direction}", f"Articles: {len(symbol_news)}", f"Avg sentiment: {avg_sentiment:.3f}"]
        }
    
    def _analyze_technicals(self, symbol: str, context: StrategyContext) -> Dict[str, Any]:
        """Analyze technical indicators for a symbol."""
        # Get technical indicators
        indicators = self._get_symbol_indicators(symbol, context)
        if not indicators:
            return {
                "signal": 0.0,
                "confidence": 0.0,
                "strength": 0.0,
                "valid": False,
                "reason": "no_indicators",
                "conditions": ["No technical indicators available"]
            }
        
        # RSI Analysis
        rsi = indicators["rsi"]
        rsi_signal = 0.0
        if rsi < 30:
            rsi_signal = 1.0
        elif rsi > 70:
            rsi_signal = -1.0
        elif 40 <= rsi <= 60:
            rsi_signal = 0.0
        else:
            rsi_signal = 0.3 if rsi < 50 else -0.3
        
        # MACD Analysis
        macd = indicators["macd"]
        macd_signal_line = indicators["macd_signal"]
        macd_signal = 0.0
        if macd > macd_signal_line:
            macd_signal = 1.0
        elif macd < macd_signal_line:
            macd_signal = -1.0
        else:
            macd_signal = 0.0
        
        # SMA Analysis
        current_price = indicators["current_price"]
        sma_20 = indicators["sma_20"]
        sma_50 = indicators["sma_50"]
        sma_signal = 0.0
        
        if sma_20 > 0 and sma_50 > 0:
            if current_price > sma_20 > sma_50:
                sma_signal = 1.0
            elif current_price < sma_20 < sma_50:
                sma_signal = -1.0
            else:
                sma_signal = 0.3 if current_price > sma_20 else -0.3 if current_price < sma_20 else 0.0
        
        # Calculate weighted technical signal
        technical_signal = (rsi_signal * 0.3 + macd_signal * 0.4 + sma_signal * 0.3)
        technical_strength = (abs(rsi_signal) + abs(macd_signal) + abs(sma_signal)) / 3
        
        # Natural confidence based on indicator strength
        confidence = min(0.9, technical_strength)
        
        return {
            "signal": technical_signal,
            "confidence": confidence,
            "strength": technical_strength,
            "valid": True,
            "rsi": rsi,
            "macd": macd,
            "sma_signal": sma_signal,
            "conditions": [f"RSI: {rsi:.1f}", f"MACD: {macd:.4f}", f"SMA: {sma_signal:.1f}"]
        }
    
    def _combine_analyses(self, news_analysis: Dict[str, Any], 
                         technical_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Combine news and technical analyses."""
        # Check if both analyses are valid
        news_valid = news_analysis.get("valid", False)
        technical_valid = technical_analysis.get("valid", False)
        
        if not news_valid and not technical_valid:
            return {
                "signal": 0.0,
                "confidence": 0.0,
                "strength": 0.0,
                "valid": False,
                "reason": "no_valid_analyses",
                "conditions": ["No valid news or technical analysis"]
            }
        
        # Weight the signals
        news_signal = news_analysis.get("signal", 0.0)
        technical_signal = technical_analysis.get("signal", 0.0)
        
        # Calculate weighted average
        total_weight = 0.0
        combined_signal = 0.0
        
        if news_valid:
            combined_signal += news_signal * self.news_weight
            total_weight += self.news_weight
        
        if technical_valid:
            combined_signal += technical_signal * self.technical_weight
            total_weight += self.technical_weight
        
        if total_weight > 0:
            combined_signal /= total_weight
        
        # Check for confluence/agreement
        if news_valid and technical_valid:
            signal_agreement = 1.0 - abs(news_signal - technical_signal) / 2.0  # 0 = conflict, 1 = agreement
            
            if signal_agreement > 0.7:  # Strong agreement
                combined_signal *= 1.2  # Boost signal
                confidence_bonus = self.agreement_bonus
            elif signal_agreement < 0.3:  # Strong conflict
                combined_signal *= 0.5  # Reduce signal
                confidence_bonus = -self.agreement_bonus
            else:
                confidence_bonus = 0.0
        else:
            signal_agreement = 0.5  # Neutral
            confidence_bonus = 0.0
        
        # Calculate combined confidence
        news_confidence = news_analysis.get("confidence", 0.0) if news_valid else 0.0
        technical_confidence = technical_analysis.get("confidence", 0.0) if technical_valid else 0.0
        
        combined_confidence = (
            (news_confidence * self.news_weight + technical_confidence * self.technical_weight) / total_weight
            if total_weight > 0 else 0.0
        )
        
        # Apply agreement bonus (no artificial floor)
        combined_confidence = min(0.95, combined_confidence + confidence_bonus)
        
        # Calculate combined strength
        news_strength = news_analysis.get("strength", 0.0) if news_valid else 0.0
        technical_strength = technical_analysis.get("strength", 0.0) if technical_valid else 0.0
        
        combined_strength = (
            (news_strength * self.news_weight + technical_strength * self.technical_weight) / total_weight
            if total_weight > 0 else 0.0
        )
        
        return {
            "signal": combined_signal,
            "confidence": combined_confidence,
            "strength": combined_strength,
            "valid": True,
            "news_valid": news_valid,
            "technical_valid": technical_valid,
            "signal_agreement": signal_agreement,
            "news_signal": news_signal,
            "technical_signal": technical_signal,
            "news_confidence": news_confidence,
            "technical_confidence": technical_confidence,
            "conditions": [
                f"News: {news_analysis.get('direction', 'neutral')}" if news_valid else "News: N/A",
                f"Technical: {'bullish' if technical_signal > 0 else 'bearish' if technical_signal < 0 else 'neutral'}" if technical_valid else "Technical: N/A",
                f"Agreement: {signal_agreement:.2f}"
            ]
        }
    
    def _get_symbol_news(self, symbol: str, news_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get relevant news for a specific symbol."""
        symbol_news = []
        
        for article in news_data:
            title = article.get("title", "").lower()
            content = article.get("content", "").lower()
            
            # Check if article mentions symbol
            symbol_keywords = [symbol.lower(), symbol.replace("-", "").lower()]
            if symbol == "BTC":
                symbol_keywords.extend(["bitcoin", "btc"])
            elif symbol == "ETH":
                symbol_keywords.extend(["ethereum", "eth"])
            
            if any(keyword in title or keyword in content for keyword in symbol_keywords):
                symbol_news.append(article)
        
        return symbol_news
    
    def _get_symbol_indicators(self, symbol: str, context: StrategyContext) -> Optional[Dict[str, float]]:
        """Get technical indicators for a symbol."""
        market_data = context.market_data
        symbol_data = market_data.get(symbol, {})
        
        if not symbol_data:
            return None
        
        indicators = symbol_data.get("indicators", {})
        if not indicators:
            return None
        
        return {
            "rsi": indicators.get("rsi", 50.0),
            "macd": indicators.get("macd", 0.0),
            "macd_signal": indicators.get("macd_signal", 0.0),
            "sma_20": indicators.get("sma_20", 0.0),
            "sma_50": indicators.get("sma_50", 0.0),
            "current_price": symbol_data.get("price", 0.0)
        }
    
    def _generate_hybrid_signal(self, symbol: str, combined_analysis: Dict[str, Any], 
                              context: StrategyContext) -> Optional[Signal]:
        """Generate hybrid trading signal."""
        combined_signal = combined_analysis["signal"]
        confidence = combined_analysis["confidence"]
        strength = combined_analysis["strength"]
        conditions = combined_analysis["conditions"]
        
        # Check confluence requirement
        if self.require_confluence:
            news_valid = combined_analysis.get("news_valid", False)
            technical_valid = combined_analysis.get("technical_valid", False)
            signal_agreement = combined_analysis.get("signal_agreement", 0.5)
            
            # Require at least one factor to be valid with good agreement
            if not (news_valid or technical_valid):
                return None
            
            # If both valid, require minimum agreement score
            if news_valid and technical_valid and signal_agreement < self.min_confluence_score:
                return None
        
        # Determine signal direction (require stronger signals for quality)
        if combined_signal > 0.4:
            direction = SignalDirection.BUY
            urgency = Urgency.HIGH if combined_signal > 0.7 else Urgency.MEDIUM
            reason = f"Hybrid BUY signal: {'; '.join(conditions)}"
        elif combined_signal < -0.4:
            direction = SignalDirection.SELL
            urgency = Urgency.HIGH if combined_signal < -0.7 else Urgency.MEDIUM
            reason = f"Hybrid SELL signal: {'; '.join(conditions)}"
        else:
            # Weak or conflicting signals - no trade
            return None
        
        # ============================================================
        # ENTRY FILTERS - Apply after direction determined
        # ============================================================
        
        # 1. Momentum filter - don't chase >5% moves
        if not self._check_momentum_filter(symbol, context, direction):
            return None
        
        # 2. Trend alignment - only trade with trend
        if not self._check_trend_alignment(symbol, context, direction):
            return None
        
        # 3. Signal confirmation - need 2+ confirming signals
        # Build technical analysis dict from combined_analysis
        tech_valid = combined_analysis.get("technical_valid", False)
        tech_analysis = {
            "valid": tech_valid,
            "rsi": combined_analysis.get("technical_confidence", 50) * 100 if tech_valid else 50,
            "macd": combined_analysis.get("technical_signal", 0) * 100,
            "macd_signal": 0,
            "sma_signal": combined_analysis.get("technical_signal", 0)
        }
        if not self._check_signal_confirmation(tech_analysis):
            return None
        
        # 4. Cooldown - minimum time between trades
        current_timestamp = context.metadata.get("current_timestamp")
        if current_timestamp and not self._check_cooldown(symbol, current_timestamp):
            return None
        
        # Track trade time for cooldown
        if current_timestamp:
            self._update_last_trade_time(symbol, current_timestamp)
        
        # ============================================================
        
        # Adjust confidence based on agreement
        if combined_analysis.get("signal_agreement", 0.5) > 0.7:
            confidence = min(0.95, confidence * 1.1)  # Boost for strong agreement
        elif combined_analysis.get("signal_agreement", 0.5) < 0.3:
            confidence = max(0.1, confidence * 0.8)  # Reduce for conflict
        
        # Adjust confidence based on market regime
        if context.market_regime == MarketRegime.VOLATILE:
            confidence *= 0.8  # Reduce confidence in volatile markets
        elif context.market_regime == MarketRegime.RISK_ON and direction == SignalDirection.BUY:
            confidence *= 1.1  # Boost confidence for buys in risk-on markets
        elif context.market_regime == MarketRegime.RISK_OFF and direction == SignalDirection.SELL:
            confidence *= 1.1  # Boost confidence for sells in risk-off markets
        
        # Create signal
        signal = self.create_signal(
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            reason=reason,
            urgency=urgency,
            signal_type=SignalType.NEWS,  # Hybrid signals are classified as NEWS
            hybrid_score=combined_signal,
            hybrid_strength=strength,
            news_valid=combined_analysis.get("news_valid", False),
            technical_valid=combined_analysis.get("technical_valid", False),
            signal_agreement=combined_analysis.get("signal_agreement", 0.5),
            news_signal=combined_analysis.get("news_signal", 0.0),
            technical_signal=combined_analysis.get("technical_signal", 0.0),
            strategy_specific={
                "stop_loss": self.hybrid_stop_loss,
                "take_profit": self.hybrid_take_profit,
                "news_weight": self.news_weight,
                "technical_weight": self.technical_weight
            }
        )
        
        return signal
    
    def get_risk_parameters(self, context: StrategyContext) -> Dict[str, Any]:
        """Get risk parameters specific to hybrid strategy."""
        base_params = super().get_risk_parameters(context)
        
        # Hybrid-specific risk adjustments
        news_volatility = context.metadata.get("news_volatility", 0.02)
        technical_volatility = context.metadata.get("volatility", 0.02)
        
        # Adjust risk based on combined volatility
        combined_volatility = (news_volatility + technical_volatility) / 2
        
        if combined_volatility > 0.05:  # High combined volatility
            base_params["stop_loss"] *= 1.3  # Wider stops
            base_params["take_profit"] *= 0.7  # Tighter targets
        elif combined_volatility < 0.01:  # Low combined volatility
            base_params["stop_loss"] *= 0.8  # Tighter stops
            base_params["take_profit"] *= 1.2  # Wider targets
        
        return base_params
    
    def _check_momentum_filter(self, symbol: str, context: StrategyContext, direction: SignalDirection) -> bool:
        """Check if price moved too much recently (avoid chasing >5% moves)."""
        symbol_data = context.market_data.get(symbol, {})
        indicators = symbol_data.get("indicators", {})
        
        # Use ATR% as momentum proxy
        atr_pct = indicators.get("atr_pct", 0.02)
        
        # If ATR too high, market is volatile - avoid entry
        if atr_pct > self.max_momentum_pct * 1.5:
            self.logger.debug(f"Momentum filter blocked {symbol}: ATR {atr_pct*100:.1f}% too high")
            return False
        
        return True
    
    def _check_trend_alignment(self, symbol: str, context: StrategyContext, direction: SignalDirection) -> bool:
        """Check if signal direction aligns with trend. LONG only in uptrend, SHORT only in downtrend."""
        indicators = self._get_symbol_indicators(symbol, context)
        if not indicators:
            return True
        
        sma_20 = indicators.get("sma_20", 0)
        sma_50 = indicators.get("sma_50", 0)
        current_price = indicators.get("current_price", 0)
        
        if sma_20 == 0 or sma_50 == 0 or current_price == 0:
            return True
        
        # Determine trend
        if sma_20 > sma_50 and current_price > sma_20:
            trend = "uptrend"
        elif sma_20 < sma_50 and current_price < sma_20:
            trend = "downtrend"
        else:
            trend = "mixed"
        
        # Check alignment
        if direction == SignalDirection.BUY and trend == "downtrend":
            self.logger.debug(f"Trend filter blocked {symbol} BUY: in downtrend")
            return False
        elif direction == SignalDirection.SELL and trend == "uptrend":
            self.logger.debug(f"Trend filter blocked {symbol} SELL: in uptrend")
            return False
        
        return True
    
    def _check_signal_confirmation(self, technical_analysis: Dict[str, Any]) -> bool:
        """Check if at least 2 technical signals confirm (RSI, MACD, SMA)."""
        if not technical_analysis.get("valid", False):
            return False
        
        signal_count = 0
        
        # RSI confirmation
        rsi = technical_analysis.get("rsi", 50)
        if rsi < 30 or rsi > 70:
            signal_count += 1
        
        # MACD confirmation
        macd = technical_analysis.get("macd", 0)
        macd_signal = technical_analysis.get("macd_signal", 0)
        if abs(macd) > abs(macd_signal) and abs(macd) > 50:  # Strong MACD
            signal_count += 1
        
        # SMA confirmation
        sma_signal = technical_analysis.get("sma_signal", 0)
        if abs(sma_signal) >= 0.5:
            signal_count += 1
        
        if signal_count >= self.min_signal_count:
            return True
        else:
            self.logger.debug(f"Confirmation filter: only {signal_count}/3 signals")
            return False
    
    def _check_cooldown(self, symbol: str, current_timestamp) -> bool:
        """Check if enough time passed since last trade."""
        last_trade = self.last_trade_time.get(symbol)
        if last_trade is None:
            return True
        
        # Check if enough bars have passed (assuming hourly data)
        if hasattr(current_timestamp, 'to_pydatetime'):
            current_timestamp = current_timestamp.to_pydatetime()
        if hasattr(last_trade, 'to_pydatetime'):
            last_trade = last_trade.to_pydatetime()
        
        # Calculate bars difference (assuming 1h timeframe)
        time_diff = (current_timestamp - last_trade).total_seconds() / 3600  # hours
        if time_diff < self.trade_cooldown_bars:
            return False
        
        return True
    
    def _update_last_trade_time(self, symbol: str, timestamp):
        """Update last trade time for cooldown tracking."""
        self.last_trade_time[symbol] = timestamp
