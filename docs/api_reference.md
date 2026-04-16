# API Reference

## Core Modules

### trading_ai.core.orchestrator

Main pipeline orchestrator that coordinates all 13 stages.

```python
class PipelineOrchestrator:
    """Main pipeline orchestrator"""
    
    def __init__(self, config: Config):
        """Initialize orchestrator with configuration"""
        
    def run_pipeline(self, dry_run: bool = True) -> PipelineResult:
        """Execute the complete trading pipeline"""
        
    def get_system_status(self) -> SystemStatus:
        """Get current system health status"""
        
    def activate_kill_switch(self) -> None:
        """Emergency halt of all trading"""
```

### trading_ai.core.models

Data models used throughout the system.

```python
@dataclass
class Article:
    """News article data structure"""
    title: str
    content: str
    source: str
    timestamp: datetime
    url: str
    metadata: Dict[str, Any]

@dataclass
class Signal:
    """Trading signal data structure"""
    direction: str  # BUY/SELL/HOLD
    confidence: float
    urgency: str
    market_regime: str
    position_size: float
    execution_priority: int
    metadata: Dict[str, Any]

@dataclass
class Order:
    """Order data structure"""
    symbol: str
    side: str
    quantity: int
    order_type: str
    time_in_force: str
    metadata: Dict[str, Any]

@dataclass
class Position:
    """Position data structure"""
    symbol: str
    quantity: int
    avg_price: float
    current_price: float
    unrealized_pnl: float
    metadata: Dict[str, Any]
```

### trading_ai.core.exceptions

Exception hierarchy for error handling.

```python
class TradingError(Exception):
    """Base class for all trading errors"""

class RiskLimitExceeded(TradingError):
    """Risk limits exceeded"""

class BrokerError(TradingError):
    """Broker API failure"""

class ValidationError(TradingError):
    """News validation failure"""

class ConfigurationError(TradingError):
    """Configuration error"""
```

## Agent Modules

### trading_ai.agents.news_collector

Handles RSS news ingestion and processing.

```python
class NewsCollector:
    """News collection and processing"""
    
    def __init__(self, config: Config):
        """Initialize news collector"""
        
    def fetch_news(self, sources: List[str]) -> List[Article]:
        """Fetch news from RSS sources"""
        
    def validate_sources(self, sources: List[str]) -> bool:
        """Validate RSS source availability"""
        
    def get_source_status(self) -> Dict[str, SourceStatus]:
        """Get status of all RSS sources"""
```

### trading_ai.agents.signal_generator

Generates trading signals from news.

```python
class SignalGenerator:
    """Signal generation from news"""
    
    def __init__(self, config: Config):
        """Initialize signal generator"""
        
    def generate_signals(self, articles: List[Article]) -> List[Signal]:
        """Generate trading signals from articles"""
        
    def get_signal_confidence(self, signal: Signal) -> float:
        """Calculate signal confidence score"""
        
    def apply_market_regime(self, signals: List[Signal], regime: str) -> List[Signal]:
        """Apply market regime adjustments"""
```

### trading_ai.agents.regime_detector

Detects market regimes for adaptive trading.

```python
class RegimeDetector:
    """Market regime detection"""
    
    def __init__(self, config: Config):
        """Initialize regime detector"""
        
    def detect_regime(self, market_data: MarketData) -> str:
        """Detect current market regime"""
        
    def get_regime_confidence(self, regime: str) -> float:
        """Get confidence in regime detection"""
        
    def update_regime_history(self, regime: str) -> None:
        """Update regime detection history"""
```

### trading_ai.agents.optimizer

Self-learning optimization engine.

```python
class SignalOptimizer:
    """Signal optimization engine"""
    
    def __init__(self, config: Config):
        """Initialize optimizer"""
        
    def optimize_parameters(self, performance_data: PerformanceData) -> Dict[str, float]:
        """Optimize signal parameters"""
        
    def update_learning_model(self, feedback: FeedbackData) -> None:
        """Update learning model with feedback"""
        
    def get_optimization_status(self) -> OptimizationStatus:
        """Get current optimization status"""
```

## Execution Modules

### trading_ai.execution.order_manager

Manages order construction and execution.

```python
class OrderManager:
    """Order management and execution"""
    
    def __init__(self, config: Config):
        """Initialize order manager"""
        
    def build_orders(self, signals: List[Signal]) -> List[Order]:
        """Build orders from signals"""
        
    def validate_order(self, order: Order) -> bool:
        """Validate order before execution"""
        
    def calculate_position_size(self, signal: Signal, portfolio: Portfolio) -> float:
        """Calculate optimal position size"""
```

### trading_ai.execution.position_tracker

Tracks positions and P&L.

```python
class PositionTracker:
    """Position tracking and P&L calculation"""
    
    def __init__(self, config: Config):
        """Initialize position tracker"""
        
    def update_positions(self, executions: List[Execution]) -> None:
        """Update positions from executions"""
        
    def get_portfolio_value(self) -> float:
        """Get current portfolio value"""
        
    def calculate_pnl(self) -> Dict[str, float]:
        """Calculate P&L for all positions"""
```

### trading_ai.execution.execution_gateway

Broker integration gateway.

```python
class ExecutionGateway:
    """Broker execution gateway"""
    
    def __init__(self, broker_config: BrokerConfig):
        """Initialize execution gateway"""
        
    def send_order(self, order: Order) -> ExecutionResult:
        """Send order to broker"""
        
    def get_positions(self) -> List[Position]:
        """Get current positions"""
        
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        
    def get_account(self) -> Account:
        """Get account information"""
```

## Risk Modules

### trading_ai.risk.risk_manager

Central risk management system.

```python
class RiskManager:
    """Risk management system"""
    
    def __init__(self, config: Config):
        """Initialize risk manager"""
        
    def evaluate_risk(self, order: Order, portfolio: Portfolio) -> RiskAssessment:
        """Evaluate risk for order"""
        
    def check_limits(self, portfolio: Portfolio) -> List[RiskBreach]:
        """Check portfolio against risk limits"""
        
    def apply_risk_controls(self, orders: List[Order]) -> List[Order]:
        """Apply risk controls to orders"""
        
    def get_risk_metrics(self) -> RiskMetrics:
        """Get current risk metrics"""
```

### trading_ai.risk.position_sizer

Position sizing and allocation.

```python
class PositionSizer:
    """Position sizing and allocation"""
    
    def __init__(self, config: Config):
        """Initialize position sizer"""
        
    def calculate_position_size(self, signal: Signal, portfolio: Portfolio) -> float:
        """Calculate optimal position size"""
        
    def allocate_portfolio(self, signals: List[Signal]) -> PortfolioAllocation:
        """Allocate portfolio across signals"""
        
    def get_sizing_metrics(self) -> SizingMetrics:
        """Get position sizing metrics"""
```

### trading_ai.risk.exposure_monitor

Monitor portfolio exposure.

```python
class ExposureMonitor:
    """Portfolio exposure monitoring"""
    
    def __init__(self, config: Config):
        """Initialize exposure monitor"""
        
    def get_exposure_metrics(self) -> ExposureMetrics:
        """Get current exposure metrics"""
        
    def check_exposure_limits(self) -> List[ExposureBreach]:
        """Check exposure against limits"""
        
    def update_exposure(self, positions: List[Position]) -> None:
        """Update exposure calculations"""
```

## Monitoring Modules

### trading_ai.monitoring.performance_tracker

Performance analytics and tracking.

```python
class PerformanceTracker:
    """Performance tracking and analytics"""
    
    def __init__(self, config: Config):
        """Initialize performance tracker"""
        
    def track_execution(self, execution: Execution) -> None:
        """Track execution performance"""
        
    def calculate_metrics(self, period: str) -> PerformanceMetrics:
        """Calculate performance metrics"""
        
    def get_attribution(self) -> AttributionReport:
        """Get performance attribution"""
        
    def generate_report(self, period: str) -> PerformanceReport:
        """Generate performance report"""
```

### trading_ai.monitoring.alert_router

Alert routing and notification.

```python
class AlertRouter:
    """Alert routing and notification"""
    
    def __init__(self, config: Config):
        """Initialize alert router"""
        
    def send_alert(self, alert: Alert) -> bool:
        """Send alert to configured channels"""
        
    def send_batch(self, alerts: List[Alert]) -> List[bool]:
        """Send batch of alerts"""
        
    def get_alert_status(self) -> AlertStatus:
        """Get alert system status"""
        
    def configure_channels(self, channels: Dict[str, AlertChannel]) -> None:
        """Configure alert channels"""
```

### trading_ai.monitoring.system_monitor

System health monitoring.

```python
class SystemMonitor:
    """System health monitoring"""
    
    def __init__(self, config: Config):
        """Initialize system monitor"""
        
    def check_health(self) -> HealthStatus:
        """Check system health"""
        
    def get_metrics(self) -> SystemMetrics:
        """Get system metrics"""
        
    def monitor_pipeline(self) -> PipelineStatus:
        """Monitor pipeline health"""
        
    def check_dependencies(self) -> DependencyStatus:
        """Check external dependencies"""
```

## Validation Modules

### trading_ai.validation.news_validator

News credibility validation.

```python
class NewsValidator:
    """News credibility validation"""
    
    def __init__(self, config: Config):
        """Initialize news validator"""
        
    def validate_article(self, article: Article) -> ValidationResult:
        """Validate article credibility"""
        
    def get_source_reputation(self, source: str) -> float:
        """Get source reputation score"""
        
    def check_duplicates(self, article: Article) -> List[Article]:
        """Check for duplicate articles"""
        
    def update_validation_memory(self, article: Article, result: ValidationResult) -> None:
        """Update validation memory"""
```

### trading_ai.validation.duplicate_filter

Duplicate detection and filtering.

```python
class DuplicateFilter:
    """Duplicate detection and filtering"""
    
    def __init__(self, config: Config):
        """Initialize duplicate filter"""
        
    def filter_duplicates(self, articles: List[Article]) -> List[Article]:
        """Filter duplicate articles"""
        
    def find_similar(self, article: Article) -> List[Article]:
        """Find similar articles"""
        
    def update_similarity_cache(self, articles: List[Article]) -> None:
        """Update similarity cache"""
```

### trading_ai.validation.credibility_scorer

Source credibility scoring.

```python
class CredibilityScorer:
    """Source credibility scoring"""
    
    def __init__(self, config: Config):
        """Initialize credibility scorer"""
        
    def score_source(self, source: str) -> float:
        """Score source credibility"""
        
    def update_source_reputation(self, source: str, accuracy: float) -> None:
        """Update source reputation"""
        
    def get_credibility_report(self) -> CredibilityReport:
        """Get credibility report"""
```

## Infrastructure Modules

### trading_ai.infrastructure.config

Configuration management.

```python
class Config:
    """Configuration management"""
    
    def __init__(self, config_file: str = None):
        """Initialize configuration"""
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        
    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        
    def validate(self) -> bool:
        """Validate configuration"""
        
    def reload(self) -> None:
        """Reload configuration"""
```

### trading_ai.infrastructure.state_manager

State persistence and recovery.

```python
class StateManager:
    """State persistence and recovery"""
    
    def __init__(self, config: Config):
        """Initialize state manager"""
        
    def save_state(self, state: SystemState) -> None:
        """Save system state"""
        
    def load_state(self) -> SystemState:
        """Load system state"""
        
    def create_backup(self) -> str:
        """Create state backup"""
        
    def restore_backup(self, backup_id: str) -> None:
        """Restore from backup"""
```

### trading_ai.infrastructure.source_registry

RSS source registry and management.

```python
class SourceRegistry:
    """RSS source registry and management"""
    
    def __init__(self, config: Config):
        """Initialize source registry"""
        
    def register_source(self, source: RSSSource) -> None:
        """Register RSS source"""
        
    def get_sources(self) -> List[RSSSource]:
        """Get all registered sources"""
        
    def validate_sources(self) -> Dict[str, bool]:
        """Validate all sources"""
        
    def update_source_status(self, source: str, status: SourceStatus) -> None:
        """Update source status"""
```

### trading_ai.infrastructure.logging

Logging infrastructure.

```python
class TradingLogger:
    """Trading system logging"""
    
    def __init__(self, config: Config):
        """Initialize logger"""
        
    def log_trade(self, trade: Trade) -> None:
        """Log trade execution"""
        
    def log_signal(self, signal: Signal) -> None:
        """Log signal generation"""
        
    def log_error(self, error: Exception) -> None:
        """Log system error"""
        
    def log_performance(self, metrics: PerformanceMetrics) -> None:
        """Log performance metrics"""
```

## Configuration Reference

### Risk Configuration

```python
RISK_CONFIG = {
    'max_position_size_pct': 0.10,  # 10% max per position
    'portfolio_exposure_pct': 0.30,  # 30% max total exposure
    'max_daily_drawdown_pct': 0.025,  # 2.5% daily loss limit
    'max_total_drawdown_pct': 0.10,   # 10% total loss limit
    'min_signal_confidence': 40,      # Minimum confidence to trade
    'execution_confidence_threshold': 0.80  # High confidence for execution
}
```

### Broker Configuration

```python
BROKER_CONFIG = {
    'alpaca': {
        'api_key': 'your_api_key',
        'secret_key': 'your_secret_key',
        'base_url': 'https://api.alpaca.markets',
        'paper': True
    },
    'ibkr': {
        'host': '127.0.0.1',
        'port': 7497,
        'client_id': 1
    },
    'binance': {
        'api_key': 'your_api_key',
        'secret_key': 'your_secret_key',
        'testnet': True
    }
}
```

### Alert Configuration

```python
ALERT_CONFIG = {
    'email': {
        'enabled': True,
        'recipients': ['trader@example.com'],
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': 587
    },
    'webhook': {
        'enabled': True,
        'url': 'https://hooks.slack.com/your_webhook'
    },
    'sms': {
        'enabled': False,
        'provider': 'twilio',
        'phone_numbers': []
    }
}
```

## Error Handling

### Exception Hierarchy

```
TradingError
    RiskError
        RiskLimitExceeded
        ExposureLimitExceeded
        DrawdownExceeded
    BrokerError
        ConnectionError
        OrderError
        AuthenticationError
    ValidationError
        SourceValidationError
        ContentValidationError
        DuplicateError
    ConfigurationError
        MissingConfigError
        InvalidConfigError
    ExecutionError
        PipelineError
        SystemError
```

### Error Recovery

```python
class ErrorRecovery:
    """Error recovery mechanisms"""
    
    def retry_with_backoff(self, func: Callable, max_retries: int = 3) -> Any:
        """Retry function with exponential backoff"""
        
    def circuit_breaker(self, func: Callable, threshold: int = 5) -> Any:
        """Circuit breaker pattern"""
        
    def fallback_handler(self, error: Exception) -> Any:
        """Fallback error handler"""
        
    def error_logger(self, error: Exception, context: Dict[str, Any]) -> None:
        """Log error with context"""
```

## Performance Metrics

### Pipeline Metrics

```python
@dataclass
class PipelineMetrics:
    """Pipeline performance metrics"""
    total_latency_ms: float
    stage_latencies: Dict[str, float]
    throughput_articles_per_sec: float
    success_rate: float
    error_rate: float
    memory_usage_mb: float
    cpu_usage_pct: float
```

### Trading Metrics

```python
@dataclass
class TradingMetrics:
    """Trading performance metrics"""
    total_pnl: float
    win_rate: float
    profit_factor: float
    expectancy: float
    sharpe_ratio: float
    max_drawdown: float
    total_trades: int
    avg_trade_duration: float
```

### System Metrics

```python
@dataclass
class SystemMetrics:
    """System health metrics"""
    uptime_seconds: float
    memory_usage_mb: float
    cpu_usage_pct: float
    disk_usage_pct: float
    network_io_bytes: int
    active_connections: int
    error_count: int
    alert_count: int
```

## Testing Utilities

### Test Fixtures

```python
class TestFixtures:
    """Test data fixtures"""
    
    @staticmethod
    def sample_article() -> Article:
        """Sample article for testing"""
        
    @staticmethod
    def sample_signal() -> Signal:
        """Sample signal for testing"""
        
    @staticmethod
    def sample_order() -> Order:
        """Sample order for testing"""
        
    @staticmethod
    def sample_portfolio() -> Portfolio:
        """Sample portfolio for testing"""
```

### Mock Services

```python
class MockBroker:
    """Mock broker for testing"""
    
    def send_order(self, order: Order) -> ExecutionResult:
        """Mock order execution"""
        
    def get_positions(self) -> List[Position]:
        """Mock position retrieval"""

class MockNewsSource:
    """Mock news source for testing"""
    
    def fetch_articles(self) -> List[Article]:
        """Mock article fetching"""
```

## Utilities

### Data Processing

```python
class DataProcessor:
    """Data processing utilities"""
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text content"""
        
    @staticmethod
    def extract_entities(text: str) -> List[str]:
        """Extract named entities"""
        
    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """Calculate text similarity"""
```

### Time Utilities

```python
class TimeUtils:
    """Time and date utilities"""
    
    @staticmethod
    def is_market_open(timestamp: datetime, market: str) -> bool:
        """Check if market is open"""
        
    @staticmethod
    def get_trading_sessions(date: datetime) -> List[TradingSession]:
        """Get trading sessions for date"""
        
    @staticmethod
    def calculate_duration(start: datetime, end: datetime) -> float:
        """Calculate duration in seconds"""
```

### Math Utilities

```python
class MathUtils:
    """Mathematical utilities"""
    
    @staticmethod
    def calculate_returns(prices: List[float]) -> List[float]:
        """Calculate returns from price series"""
        
    @staticmethod
    def calculate_volatility(returns: List[float]) -> float:
        """Calculate volatility"""
        
    @staticmethod
    def calculate_correlation(x: List[float], y: List[float]) -> float:
        """Calculate correlation coefficient"""
```
