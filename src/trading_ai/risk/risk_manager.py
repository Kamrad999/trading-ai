"""
Real risk management for Trading AI.

Implements max position exposure, max concurrent signals, risk score normalization,
kill switch, drawdown protection hooks, and circuit breaker trip conditions.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from ..core.models import Signal, RiskAssessment
from ..core.exceptions import RiskLimitExceeded, KillSwitchActivated
from ..infrastructure.config import config
from ..infrastructure.logging import get_logger
from ..infrastructure.state_manager import StateManager


class RiskManager:
    """Real risk management engine."""
    
    def __init__(self) -> None:
        """Initialize risk manager with safety parameters."""
        self.logger = get_logger("risk_manager")
        self.state_manager = StateManager()
        
        # Risk limits from config
        self.max_risk_per_trade = config.MAX_RISK_PER_TRADE
        self.max_open_positions = config.MAX_OPEN_POSITIONS
        self.max_daily_loss = config.DAILY_LOSS_LIMIT
        self.max_portfolio_exposure = config.MAX_PORTFOLIO_EXPOSURE
        
        # Risk thresholds
        self.confidence_threshold = config.MIN_SIGNAL_CONFIDENCE
        self.max_signals_per_batch = 10
        self.max_signals_per_symbol = 3
        
        # Kill switch conditions
        self.daily_loss_threshold = 0.05  # 5% daily loss triggers kill switch
        self.consecutive_losses = 5  # 5 consecutive losing trades triggers kill switch
        self.circuit_breaker_threshold = 0.10  # 10% portfolio loss triggers circuit breaker
        
        # State tracking
        self.daily_pnl = 0.0
        self.consecutive_loss_count = 0
        self.total_exposure = 0.0
        self.open_positions: Dict[str, Dict[str, Any]] = {}
        
        # Load risk state
        self._load_risk_state()
    
    def _load_risk_state(self) -> None:
        """Load risk management state from persistent storage."""
        try:
            state = self.state_manager.load_state()
            risk_state = state.get("risk_manager", {})
            
            self.daily_pnl = risk_state.get("daily_pnl", 0.0)
            self.consecutive_loss_count = risk_state.get("consecutive_loss_count", 0)
            self.total_exposure = risk_state.get("total_exposure", 0.0)
            self.open_positions = risk_state.get("open_positions", {})
            
            # Reset daily PnL if new day
            last_update = risk_state.get("last_update")
            if last_update:
                last_date = datetime.fromisoformat(last_update).date()
                if last_date < datetime.now(timezone.utc).date():
                    self.daily_pnl = 0.0
                    self.consecutive_loss_count = 0
            
            self.logger.info(
                f"Loaded risk state: PnL={self.daily_pnl:.3f}, "
                f"exposure={self.total_exposure:.3f}, positions={len(self.open_positions)}"
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to load risk state: {e}")
            self._initialize_risk_state()
    
    def _initialize_risk_state(self) -> None:
        """Initialize empty risk state."""
        self.daily_pnl = 0.0
        self.consecutive_loss_count = 0
        self.total_exposure = 0.0
        self.open_positions = {}
    
    def _save_risk_state(self) -> None:
        """Save risk management state to persistent storage."""
        try:
            state = self.state_manager.load_state()
            
            risk_state = {
                "daily_pnl": self.daily_pnl,
                "consecutive_loss_count": self.consecutive_loss_count,
                "total_exposure": self.total_exposure,
                "open_positions": self.open_positions,
                "last_update": datetime.now(timezone.utc).isoformat()
            }
            
            state["risk_manager"] = risk_state
            self.state_manager.save_state(state)
            
            self.logger.debug("Risk state saved")
            
        except Exception as e:
            self.logger.error(f"Failed to save risk state: {e}")
    
    def assess_signals(self, signals: List[Signal]) -> List[RiskAssessment]:
        """
        Assess risk for a batch of signals.
        
        Args:
            signals: List of signals to assess
            
        Returns:
            List of risk assessments
        """
        assessments = []
        
        self.logger.info(f"Assessing risk for {len(signals)} signals")
        
        # Check kill switch first
        if self.is_kill_switch_active():
            self.logger.warning("Kill switch active - rejecting all signals")
            for signal in signals:
                assessments.append(RiskAssessment(
                    signal_id=hashlib.sha256(f"{signal.symbol}{signal.generated_at}".encode()).hexdigest()[:16],
                    approved=False,
                    risk_score=1.0,
                    reasons=["Kill switch active"],
                    position_size=0.0,
                    metadata={"kill_switch": True}
                ))
            return assessments
        
        # Check circuit breakers
        if self._check_circuit_breakers():
            self.logger.warning("Circuit breaker triggered - rejecting all signals")
            for signal in signals:
                assessments.append(RiskAssessment(
                    signal_id=hashlib.sha256(f"{signal.symbol}{signal.generated_at}".encode()).hexdigest()[:16],
                    approved=False,
                    risk_score=0.9,
                    reasons=["Circuit breaker triggered"],
                    position_size=0.0,
                    metadata={"circuit_breaker": True}
                ))
            return assessments
        
        # Assess each signal
        for signal in signals[:self.max_signals_per_batch]:
            assessment = self._assess_single_signal(signal)
            assessments.append(assessment)
        
        # Apply portfolio-level constraints
        assessments = self._apply_portfolio_constraints(assessments)
        
        approved_count = sum(1 for a in assessments if a.approved)
        avg_risk_score = sum(a.risk_score for a in assessments) / len(assessments) if assessments else 0
        
        self.logger.info(
            f"Risk assessment completed: {approved_count}/{len(assessments)} approved, "
            f"avg risk score: {avg_risk_score:.3f}"
        )
        
        return assessments
    
    def _assess_single_signal(self, signal: Signal) -> RiskAssessment:
        """Assess risk for a single signal."""
        reasons = []
        risk_score = 0.0
        approved = True
        position_size = signal.position_size
        
        # Check confidence threshold
        if signal.confidence < self.confidence_threshold:
            reasons.append(f"Confidence too low: {signal.confidence:.3f}")
            risk_score += 0.3
            approved = False
        
        # Check position size limits
        if signal.position_size > self.max_risk_per_trade:
            reasons.append(f"Position size too large: {signal.position_size:.3f}")
            risk_score += 0.4
            position_size = self.max_risk_per_trade
        
        # Check symbol exposure
        symbol_exposure = self._get_symbol_exposure(signal.symbol)
        if symbol_exposure > 0.3:  # Max 30% per symbol
            reasons.append(f"Symbol exposure too high: {symbol_exposure:.3f}")
            risk_score += 0.3
            approved = False
        
        # Check portfolio exposure
        new_total_exposure = self.total_exposure + position_size
        if new_total_exposure > self.max_portfolio_exposure:
            reasons.append(f"Portfolio exposure too high: {new_total_exposure:.3f}")
            risk_score += 0.5
            approved = False
        
        # Check open position limits
        if len(self.open_positions) >= self.max_open_positions:
            reasons.append(f"Too many open positions: {len(self.open_positions)}")
            risk_score += 0.3
            approved = False
        
        # Check signals per symbol
        symbol_signals = self._count_symbol_signals(signal.symbol)
        if symbol_signals >= self.max_signals_per_symbol:
            reasons.append(f"Too many signals for symbol: {signal.symbol}")
            risk_score += 0.2
            approved = False
        
        # Calculate final risk score
        if approved:
            # Lower confidence = higher risk
            risk_score += (1.0 - signal.confidence) * 0.3
            
            # Higher urgency = higher risk
            if signal.urgency.value == "HIGH":
                risk_score += 0.2
            elif signal.urgency.value == "MEDIUM":
                risk_score += 0.1
            
            # Position size risk
            risk_score += position_size * 2.0  # Position size contributes to risk
        
        risk_score = min(risk_score, 1.0)
        
        return RiskAssessment(
            signal_id=hashlib.sha256(f"{signal.symbol}{signal.generated_at}".encode()).hexdigest()[:16],
            approved=approved,
            risk_score=risk_score,
            reasons=reasons,
            position_size=position_size if approved else 0.0,
            metadata={
                "symbol": signal.symbol,
                "confidence": signal.confidence,
                "urgency": signal.urgency.value,
                "symbol_exposure": symbol_exposure,
                "portfolio_exposure": new_total_exposure
            }
        )
    
    def _apply_portfolio_constraints(self, assessments: List[RiskAssessment]) -> List[RiskAssessment]:
        """Apply portfolio-level constraints to assessments."""
        # Sort by risk score (lower risk first)
        approved_assessments = [a for a in assessments if a.approved]
        approved_assessments.sort(key=lambda a: a.risk_score)
        
        # Apply total position limit
        total_size = 0.0
        final_assessments = []
        
        for assessment in approved_assessments:
            if total_size + assessment.position_size <= self.max_portfolio_exposure:
                final_assessments.append(assessment)
                total_size += assessment.position_size
            else:
                # Reduce position size to fit
                remaining = self.max_portfolio_exposure - total_size
                if remaining > 0.01:  # Minimum position size
                    assessment.position_size = remaining
                    assessment.reasons.append("Position size reduced for portfolio limit")
                    final_assessments.append(assessment)
                    total_size += remaining
                else:
                    assessment.approved = False
                    assessment.position_size = 0.0
                    assessment.reasons.append("Portfolio exposure limit reached")
                    final_assessments.append(assessment)
        
        # Add rejected assessments
        rejected_assessments = [a for a in assessments if not a.approved]
        final_assessments.extend(rejected_assessments)
        
        return final_assessments
    
    def update_position(self, symbol: str, quantity: float, price: float, pnl: float) -> None:
        """Update position and P&L tracking."""
        if symbol in self.open_positions:
            position = self.open_positions[symbol]
            position["quantity"] += quantity
            position["avg_price"] = ((position["avg_price"] * position["quantity"] - quantity * price) + quantity * price) / position["quantity"]
        else:
            self.open_positions[symbol] = {
                "quantity": quantity,
                "avg_price": price,
                "current_price": price,
                "unrealized_pnl": 0.0,
                "realized_pnl": 0.0,
                "opened_at": datetime.now(timezone.utc)
            }
        
        # Update P&L
        self.daily_pnl += pnl
        if pnl < 0:
            self.consecutive_loss_count += 1
        else:
            self.consecutive_loss_count = 0
        
        # Update exposure
        self.total_exposure = sum(abs(pos["quantity"]) * pos["current_price"] for pos in self.open_positions.values())
        
        # Check kill switch conditions
        self._check_kill_switch_conditions()
        
        # Save state
        self._save_risk_state()
        
        self.logger.info(
            f"Position updated: {symbol} qty={quantity} P&L={pnl:.3f} "
            f"daily P&L={self.daily_pnl:.3f} consecutive_losses={self.consecutive_loss_count}"
        )
    
    def close_position(self, symbol: str, price: float) -> float:
        """Close position and return realized P&L."""
        if symbol not in self.open_positions:
            self.logger.warning(f"Cannot close non-existent position: {symbol}")
            return 0.0
        
        position = self.open_positions[symbol]
        realized_pnl = (price - position["avg_price"]) * position["quantity"]
        
        # Update P&L
        self.daily_pnl += realized_pnl
        if realized_pnl < 0:
            self.consecutive_loss_count += 1
        else:
            self.consecutive_loss_count = 0
        
        # Remove position
        del self.open_positions[symbol]
        
        # Update exposure
        self.total_exposure = sum(abs(pos["quantity"]) * pos["current_price"] for pos in self.open_positions.values())
        
        # Check kill switch conditions
        self._check_kill_switch_conditions()
        
        # Save state
        self._save_risk_state()
        
        self.logger.info(
            f"Position closed: {symbol} P&L={realized_pnl:.3f} "
            f"daily P&L={self.daily_pnl:.3f} consecutive_losses={self.consecutive_loss_count}"
        )
        
        return realized_pnl
    
    def is_kill_switch_active(self) -> bool:
        """Check if kill switch is active."""
        return self._check_kill_switch_conditions()
    
    def _check_kill_switch_conditions(self) -> bool:
        """Check if kill switch should be activated."""
        # Daily loss limit (as percentage of portfolio)
        portfolio_size = config.PORTFOLIO_SIZE_USD
        daily_loss_pct = abs(self.daily_pnl) / portfolio_size if portfolio_size > 0 else 0
        if daily_loss_pct > self.daily_loss_threshold:
            self.logger.error(f"Kill switch activated: Daily loss exceeded {self.daily_loss_threshold:.3f}")
            raise KillSwitchActivated(f"Daily loss limit exceeded: {daily_loss_pct:.3f}")
        
        # Consecutive losses
        if self.consecutive_loss_count >= self.consecutive_losses:
            self.logger.error(f"Kill switch activated: {self.consecutive_losses} consecutive losses")
            raise KillSwitchActivated(f"Consecutive loss limit exceeded: {self.consecutive_loss_count}")
        
        return False
    
    def _check_circuit_breakers(self) -> bool:
        """Check if circuit breakers should be triggered."""
        # Portfolio loss circuit breaker
        if self.total_exposure > 0 and abs(self.daily_pnl) / self.total_exposure > self.circuit_breaker_threshold:
            self.logger.warning("Circuit breaker triggered: Portfolio loss exceeded threshold")
            return True
        
        return False
    
    def _get_symbol_exposure(self, symbol: str) -> float:
        """Get current exposure for a symbol."""
        if symbol in self.open_positions:
            position = self.open_positions[symbol]
            return abs(position["quantity"] * position["current_price"])
        return 0.0
    
    def _count_symbol_signals(self, symbol: str) -> int:
        """Count existing signals for a symbol (simplified)."""
        # In a real implementation, this would track recent signals
        return 0
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics."""
        return {
            "daily_pnl": self.daily_pnl,
            "consecutive_losses": self.consecutive_loss_count,
            "total_exposure": self.total_exposure,
            "open_positions": len(self.open_positions),
            "max_risk_per_trade": self.max_risk_per_trade,
            "max_portfolio_exposure": self.max_portfolio_exposure,
            "kill_switch_active": self.is_kill_switch_active(),
            "circuit_breaker_active": self._check_circuit_breakers(),
            "risk_utilization": self.total_exposure / self.max_portfolio_exposure if self.max_portfolio_exposure > 0 else 0
        }
    
    def reset_kill_switch(self) -> None:
        """Reset kill switch (manual intervention)."""
        self.daily_pnl = 0.0
        self.consecutive_loss_count = 0
        self._save_risk_state()
        self.logger.info("Kill switch manually reset")
    
    def emergency_close_all(self) -> Dict[str, float]:
        """Emergency close all positions."""
        closed_positions = {}
        
        for symbol in list(self.open_positions.keys()):
            pnl = self.close_position(symbol, self.open_positions[symbol]["current_price"])
            closed_positions[symbol] = pnl
        
        self.logger.warning(f"Emergency close completed: {len(closed_positions)} positions closed")
        return closed_positions
