# Trading AI - Institutional-Grade Trading Signal Engine

A **13-stage institutional trading pipeline** that transforms 80+ RSS news feeds into real-time, risk-managed trading signals with institutional-grade validation, forensic credibility analysis, and multi-market regime detection.

Built with **pure Python standard library** (no pandas, no numpy) for maximum portability and minimal dependencies.

## Quick Start

### Prerequisites
- Python 3.11+
- feedparser>=6.0.0
- requests>=2.28.0

### Installation
```bash
pip install -r requirements.txt
```

### Run the Pipeline
```bash
python scripts/run_pipeline.py
```

### Run Backtests
```bash
python scripts/backtest.py
```

## Architecture

The system follows a **13-stage pipeline architecture**:

1. **News Collection** - RSS ingestion from 80+ sources
2. **Deduplication** - Remove duplicate articles
3. **Validation** - Credibility & misinformation detection  
4. **Signal Generation** - 10-layer signal processing
5. **Risk Controls** - Portfolio risk enforcement
6. **Order Construction** - Build execution orders
7. **Broker Transmission** - Send to brokers (paper/live)
8. **Alert Routing** - Multi-channel alert distribution
9. **State Persistence** - Save system state
10. **Validation Memory** - Forensic memory snapshots
11. **Performance Analytics** - Trade analytics
12. **Regime Detection** - Market regime inference
13. **Self-Learning** - Signal optimization

## Configuration

All settings centralized in `src/trading_ai/infrastructure/config.py`:

```python
# Paper trading mode (default: True)
PAPER_MODE = True

# Risk limits
MAX_DAILY_DRAWDOWN_PCT = 0.025          # 2.5% daily loss limit
PORTFOLIO_EXPOSURE_PCT = 0.30            # Max 30% portfolio exposure per trade

# Confidence thresholds
MIN_SIGNAL_CONFIDENCE = 40               # Minimum 40% confidence to trade
EXECUTION_CONFIDENCE_THRESHOLD = 0.80    # 80% threshold for immediate execution

# Market regime detection
REGIME_DETECTION_WINDOW = 252            # 252-day detection window

# TEST_MODE for fast iteration
TEST_MODE = True  # <-- Set to False for live feeds
```

## Performance Metrics

| Component | Articles | Latency | Throughput |
|-----------|----------|---------|------------|
| news_engine | 80+ RSS | 0.1ms | Instant (TEST_MODE) |
| duplicate_filter | 1000+ | 2.1ms | 476k articles/sec |
| fake_news_validator | 1000+ | 0.8ms | 1.25M articles/sec |
| signal_engine | 1000+ | 1.0ms | 1M articles/sec |
| risk_guardian | 1000+ | 0.7ms | 1.43M articles/sec |
| execution_bridge | 1000+ | 0.1ms | 10M articles/sec |
| **Total Pipeline** | **1000+** | **7.0ms** | **142k articles/sec** |

## Data Sources

- **80+ RSS feeds** covering financial news, market data, economic indicators
- **Real-time validation** with forensic credibility analysis
- **Multi-market regime detection** with adaptive thresholds

## Security & Risk

- **Kill switch** for emergency trading halt
- **Portfolio exposure caps** with real-time monitoring
- **Drawdown protection** with automated position reduction
- **Circuit breakers** for system failures
- **Audit logging** for all trading activities

## Development

### Adding a New Signal Provider
1. Create new signal module in `src/trading_ai/agents/`
2. Implement signal interface
3. Register in source registry
4. Add tests

### Adding a New Alert Channel
1. Create alert module in `src/trading_ai/monitoring/`
2. Implement alert interface
3. Configure in `config.py`
4. Add tests

## Testing

```bash
# Run all module smoke tests
python -m pytest tests/

# Run integration tests
python -m pytest tests/integration/

# Run performance benchmarks
python -m pytest tests/performance/
```

## Deployment

See [deployment.md](deployment.md) for detailed deployment instructions.

## License

MIT License - see [LICENSE](../LICENSE) for details.

## Disclaimer

This software is for educational and research purposes only. Use at your own risk.
