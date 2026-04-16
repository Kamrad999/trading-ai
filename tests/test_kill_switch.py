"""
Real tests for kill switch functionality.

Tests kill switch activation, daily loss limits, consecutive losses,
circuit breaker triggers, and emergency position closing.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trading_ai.risk.risk_manager import RiskManager
from trading_ai.core.models import Signal, SignalDirection, Urgency
from trading_ai.core.exceptions import KillSwitchActivated, RiskLimitExceeded


class TestKillSwitch:
    """Real kill switch tests."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.risk_manager = RiskManager()
    
    def test_risk_manager_initialization(self):
        """Test RiskManager initializes correctly."""
        assert self.risk_manager is not None
        assert self.risk_manager.daily_pnl == 0.0
        assert self.risk_manager.consecutive_loss_count == 0
        assert self.risk_manager.total_exposure == 0.0
        assert len(self.risk_manager.open_positions) == 0
    
    def test_daily_loss_limit_trigger(self):
        """Test kill switch triggers on daily loss limit."""
        # Set daily loss beyond limit (5% of $25,000 portfolio = $1,250)
        self.risk_manager.daily_pnl = -1300.0  # -5.2% of portfolio
        
        # Should trigger kill switch
        with pytest.raises(KillSwitchActivated) as exc_info:
            self.risk_manager._check_kill_switch_conditions()
        
        assert "Daily loss limit exceeded" in str(exc_info.value)
    
    def test_consecutive_losses_trigger(self):
        """Test kill switch triggers on consecutive losses."""
        # Set consecutive losses beyond limit (5)
        self.risk_manager.consecutive_loss_count = 6
        
        # Should trigger kill switch
        with pytest.raises(KillSwitchActivated) as exc_info:
            self.risk_manager._check_kill_switch_conditions()
        
        assert "Consecutive loss limit exceeded" in str(exc_info.value)
    
    def test_consecutive_losses_reset_on_profit(self):
        """Test consecutive losses reset on profitable trade."""
        # Set consecutive losses
        self.risk_manager.consecutive_loss_count = 3
        
        # Update with profit
        self.risk_manager.update_position("TEST", 100, 100.0, 100.0)  # $100 profit (under 5% threshold)
        
        # Should reset consecutive losses
        assert self.risk_manager.consecutive_loss_count == 0
    
    def test_consecutive_losses_increment_on_loss(self):
        """Test consecutive losses increment on losing trade."""
        # Set consecutive losses
        self.risk_manager.consecutive_loss_count = 2
        
        # Update with loss
        self.risk_manager.update_position("TEST", 100, 100.0, -50.0)  # $50 loss (under 5% threshold)
        
        # Should increment consecutive losses
        assert self.risk_manager.consecutive_loss_count == 3
    
    def test_is_kill_switch_active(self):
        """Test kill switch active status."""
        # Initially should not be active
        assert self.risk_manager.is_kill_switch_active() is False
        
        # Set daily loss beyond limit
        self.risk_manager.daily_pnl = -0.06
        
        # Should be active
        assert self.risk_manager.is_kill_switch_active() is True
    
    def test_circuit_breaker_trigger(self):
        """Test circuit breaker triggers on portfolio loss."""
        # Set exposure and loss to trigger circuit breaker (10%)
        self.risk_manager.total_exposure = 10000.0
        self.risk_manager.daily_pnl = -1500.0  # -15% of exposure
        
        # Should trigger circuit breaker
        assert self.risk_manager._check_circuit_breakers() is True
    
    def test_circuit_breaker_no_trigger(self):
        """Test circuit breaker doesn't trigger below threshold."""
        # Set exposure and loss below threshold
        self.risk_manager.total_exposure = 10000.0
        self.risk_manager.daily_pnl = -500.0  # -5% of exposure
        
        # Should not trigger circuit breaker
        assert self.risk_manager._check_circuit_breakers() is False
    
    def test_assess_signals_with_kill_switch_active(self):
        """Test signal assessment when kill switch is active."""
        # Activate kill switch
        self.risk_manager.daily_pnl = -0.06
        
        # Create test signal
        signal = Signal(
            direction=SignalDirection.BUY,
            confidence=0.8,
            urgency=Urgency.HIGH,
            market_regime="RISK_ON",
            position_size=0.02,
            execution_priority=1,
            symbol="AAPL",
            article_id="test123",
            generated_at=datetime.now(timezone.utc),
            metadata={}
        )
        
        # Assess signals
        assessments = self.risk_manager.assess_signals([signal])
        
        # Should reject all signals
        assert len(assessments) == 1
        assert assessments[0].approved is False
        assert "Kill switch active" in assessments[0].reasons
        assert assessments[0].risk_score == 1.0
    
    def test_assess_signals_with_circuit_breaker_active(self):
        """Test signal assessment when circuit breaker is active."""
        # Trigger circuit breaker
        self.risk_manager.total_exposure = 10000.0
        self.risk_manager.daily_pnl = -1500.0
        
        # Create test signal
        signal = Signal(
            direction=SignalDirection.BUY,
            confidence=0.8,
            urgency=Urgency.HIGH,
            market_regime="RISK_ON",
            position_size=0.02,
            execution_priority=1,
            symbol="AAPL",
            article_id="test123",
            generated_at=datetime.now(timezone.utc),
            metadata={}
        )
        
        # Assess signals
        assessments = self.risk_manager.assess_signals([signal])
        
        # Should reject all signals
        assert len(assessments) == 1
        assert assessments[0].approved is False
        assert "Circuit breaker triggered" in assessments[0].reasons
        assert assessments[0].risk_score == 0.9
    
    def test_assess_signals_confidence_threshold(self):
        """Test signal assessment with confidence threshold."""
        # Create low confidence signal
        signal = Signal(
            direction=SignalDirection.BUY,
            confidence=0.1,  # Below threshold (0.3)
            urgency=Urgency.LOW,
            market_regime="NEUTRAL",
            position_size=0.01,
            execution_priority=4,
            symbol="AAPL",
            article_id="test123",
            generated_at=datetime.now(timezone.utc),
            metadata={}
        )
        
        # Assess signals
        assessments = self.risk_manager.assess_signals([signal])
        
        # Should reject due to low confidence
        assert len(assessments) == 1
        assert assessments[0].approved is False
        assert "Confidence too low" in assessments[0].reasons
    
    def test_assess_signals_position_size_limit(self):
        """Test signal assessment with position size limit."""
        # Create signal with large position size
        signal = Signal(
            direction=SignalDirection.BUY,
            confidence=0.8,
            urgency=Urgency.HIGH,
            market_regime="RISK_ON",
            position_size=0.05,  # Above max (0.02)
            execution_priority=1,
            symbol="AAPL",
            article_id="test123",
            generated_at=datetime.now(timezone.utc),
            metadata={}
        )
        
        # Assess signals
        assessments = self.risk_manager.assess_signals([signal])
        
        # Should reduce position size
        assert len(assessments) == 1
        assert assessments[0].position_size == 0.02  # Reduced to max
        assert "Position size too large" in assessments[0].reasons
    
    def test_assess_signals_portfolio_exposure_limit(self):
        """Test signal assessment with portfolio exposure limit."""
        # Set high existing exposure
        self.risk_manager.total_exposure = 0.94  # Near limit (0.95)
        
        # Create signal
        signal = Signal(
            direction=SignalDirection.BUY,
            confidence=0.8,
            urgency=Urgency.HIGH,
            market_regime="RISK_ON",
            position_size=0.05,  # Would exceed limit
            execution_priority=1,
            symbol="AAPL",
            article_id="test123",
            generated_at=datetime.now(timezone.utc),
            metadata={}
        )
        
        # Assess signals
        assessments = self.risk_manager.assess_signals([signal])
        
        # Should reject due to portfolio exposure limit
        assert len(assessments) == 1
        assert assessments[0].approved is False
        assert "Portfolio exposure too high" in assessments[0].reasons
    
    def test_update_position_new_position(self):
        """Test updating a new position."""
        # Update new position
        self.risk_manager.update_position("AAPL", 100, 150.0, 100.0)
        
        # Should add position
        assert "AAPL" in self.risk_manager.open_positions
        assert self.risk_manager.open_positions["AAPL"]["quantity"] == 100
        assert self.risk_manager.open_positions["AAPL"]["avg_price"] == 150.0
        assert self.risk_manager.daily_pnl == 100.0
        assert self.risk_manager.total_exposure == 15000.0  # 100 * 150
    
    def test_update_existing_position(self):
        """Test updating an existing position."""
        # Add initial position
        self.risk_manager.update_position("AAPL", 100, 150.0, 0.0)
        
        # Update position (add more shares)
        self.risk_manager.update_position("AAPL", 50, 155.0, 50.0)
        
        # Should update position correctly
        position = self.risk_manager.open_positions["AAPL"]
        assert position["quantity"] == 150  # 100 + 50
        assert position["avg_price"] == 151.67  # Weighted average
        assert self.risk_manager.daily_pnl == 50.0  # Only the new P&L
    
    def test_close_position(self):
        """Test closing a position."""
        # Add position
        self.risk_manager.update_position("AAPL", 100, 150.0, 0.0)
        
        # Close position
        realized_pnl = self.risk_manager.close_position("AAPL", 152.0)
        
        # Should calculate P&L correctly and remove position
        assert realized_pnl == 200.0  # (152 - 150) * 100
        assert "AAPL" not in self.risk_manager.open_positions
        assert self.risk_manager.total_exposure == 0.0
        assert self.risk_manager.daily_pnl == 200.0  # (152-150)*100
    
    def test_close_nonexistent_position(self):
        """Test closing a non-existent position."""
        realized_pnl = self.risk_manager.close_position("NONEXISTENT", 100.0)
        
        # Should return 0 and not error
        assert realized_pnl == 0.0
        assert "NONEXISTENT" not in self.risk_manager.open_positions
    
    def test_emergency_close_all(self):
        """Test emergency closing all positions."""
        # Add multiple positions
        self.risk_manager.update_position("AAPL", 100, 150.0, 0.0)
        self.risk_manager.update_position("GOOGL", 50, 2000.0, 0.0)
        
        # Set current prices
        self.risk_manager.open_positions["AAPL"]["current_price"] = 160.0
        self.risk_manager.open_positions["GOOGL"]["current_price"] = 2100.0
        
        # Emergency close all
        closed_positions = self.risk_manager.emergency_close_all()
        
        # Should close all positions
        assert len(closed_positions) == 2
        assert "AAPL" in closed_positions
        assert "GOOGL" in closed_positions
        assert len(self.risk_manager.open_positions) == 0
        assert self.risk_manager.total_exposure == 0.0
    
    def test_reset_kill_switch(self):
        """Test manual kill switch reset."""
        # Activate kill switch
        self.risk_manager.daily_pnl = -0.06
        self.risk_manager.consecutive_loss_count = 5
        
        # Reset kill switch
        self.risk_manager.reset_kill_switch()
        
        # Should reset all metrics
        assert self.risk_manager.daily_pnl == 0.0
        assert self.risk_manager.consecutive_loss_count == 0
    
    def test_get_risk_metrics(self):
        """Test getting risk metrics."""
        # Add some data
        self.risk_manager.update_position("AAPL", 100, 150.0, 500.0)
        
        metrics = self.risk_manager.get_risk_metrics()
        
        assert "daily_pnl" in metrics
        assert "consecutive_losses" in metrics
        assert "total_exposure" in metrics
        assert "open_positions" in metrics
        assert "max_risk_per_trade" in metrics
        assert "kill_switch_active" in metrics
        assert "circuit_breaker_active" in metrics
        assert "risk_utilization" in metrics
        
        assert metrics["daily_pnl"] == 500.0
        assert metrics["open_positions"] == 1
        assert metrics["risk_utilization"] == 15000.0 / 0.95  # exposure / max_exposure
    
    def test_state_persistence(self):
        """Test state persistence across instances."""
        # Update position in first instance
        self.risk_manager.update_position("AAPL", 100, 150.0, 500.0)
        
        # Create new instance (should load state)
        new_risk_manager = RiskManager()
        
        # Should have persisted state
        assert new_risk_manager.daily_pnl == 500.0
        assert "AAPL" in new_risk_manager.open_positions
        assert new_risk_manager.total_exposure == 15000.0
    
    def test_daily_pnl_reset_new_day(self):
        """Test daily P&L resets on new day."""
        # Set P&L for yesterday
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        
        # Mock the state with old date
        with patch.object(self.risk_manager.state_manager, 'load_state') as mock_load:
            mock_load.return_value = {
                "risk_manager": {
                    "daily_pnl": 1000.0,
                    "consecutive_loss_count": 3,
                    "total_exposure": 15000.0,
                    "open_positions": {},
                    "last_update": yesterday.isoformat()
                }
            }
            
            # Reload state
            self.risk_manager._load_risk_state()
        
        # Should reset daily P&L and consecutive losses
        assert self.risk_manager.daily_pnl == 0.0
        assert self.risk_manager.consecutive_loss_count == 0
        # But should keep other state
        assert self.risk_manager.total_exposure == 15000.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
