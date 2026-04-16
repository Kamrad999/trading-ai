# Deployment Guide

## System Requirements

### Hardware
- **CPU**: 4+ cores recommended
- **Memory**: 8GB+ RAM
- **Storage**: 50GB+ available space
- **Network**: Stable internet connection for RSS feeds

### Software
- Python 3.11+
- Docker (optional, for containerized deployment)
- Redis (optional, for distributed caching)

## Configuration

### Environment Variables
```bash
# Trading mode
TRADING_MODE=paper  # or 'live'

# Risk management
KILL_SWITCH=0  # Set to 1 to halt all trading
MAX_DAILY_LOSS=0.025  # 2.5% daily loss limit

# API Keys (for live trading)
ALPACA_API_KEY=your_api_key
ALPACA_SECRET_KEY=your_secret_key
IBKR_HOST=127.0.0.1
IBKR_PORT=7497
BINANCE_API_KEY=your_api_key
BINANCE_SECRET_KEY=your_secret_key

# Monitoring
WEBHOOK_URL=your_webhook_url
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
```

### Broker Configuration

#### Alpaca Markets
```python
ALPACA_CONFIG = {
    'api_key': os.getenv('ALPACA_API_KEY'),
    'secret_key': os.getenv('ALPACA_SECRET_KEY'),
    'base_url': 'https://api.alpaca.markets',
    'paper': True,  # Set to False for live
    'data_feed': 'sip'
}
```

#### Interactive Brokers (IBKR)
```python
IBKR_CONFIG = {
    'host': os.getenv('IBKR_HOST', '127.0.0.1'),
    'port': int(os.getenv('IBKR_PORT', '7497')),
    'client_id': 1,
    'timeout': 10
}
```

#### Binance
```python
BINANCE_CONFIG = {
    'api_key': os.getenv('BINANCE_API_KEY'),
    'secret_key': os.getenv('BINANCE_SECRET_KEY'),
    'testnet': True  # Set to False for live
}
```

## Deployment Modes

### Paper Trading (Recommended for Testing)
```python
PAPER_MODE = True
TEST_MODE = True
DRY_RUN = True
```

### Live Trading (Production)
```python
PAPER_MODE = False
TEST_MODE = False
DRY_RUN = False
KILL_SWITCH = 0  # Must be explicitly enabled
```

## Risk Management Configuration

### Portfolio Risk Limits
```python
# Position sizing
MAX_POSITION_SIZE_PCT = 0.10  # 10% max per position
PORTFOLIO_EXPOSURE_PCT = 0.30  # 30% max total exposure

# Drawdown protection
MAX_DAILY_DRAWDOWN_PCT = 0.025  # 2.5% daily loss limit
MAX_TOTAL_DRAWDOWN_PCT = 0.10   # 10% total loss limit

# Confidence thresholds
MIN_SIGNAL_CONFIDENCE = 40  # Minimum confidence to trade
EXECUTION_CONFIDENCE_THRESHOLD = 0.80  # High confidence for execution
```

### Market Session Windows (UTC)
```python
MARKET_SESSIONS = {
    'US_EQUITIES': {
        'open': '14:30',
        'close': '21:00',
        'timezone': 'UTC'
    },
    'FOREX': {
        'open': '00:00',
        'close': '23:59',
        'timezone': 'UTC'
    },
    'CRYPTO': {
        'open': '00:00',
        'close': '23:59',
        'timezone': 'UTC'
    }
}
```

## Monitoring & Alerts

### Alert Channels
```python
ALERT_CHANNELS = {
    'email': {
        'enabled': True,
        'recipients': ['trader@example.com']
    },
    'webhook': {
        'enabled': True,
        'url': os.getenv('WEBHOOK_URL')
    },
    'slack': {
        'enabled': False,
        'webhook_url': None
    }
}
```

### Health Checks
```python
HEALTH_CHECK_CONFIG = {
    'pipeline_timeout': 300,  # 5 minutes
    'broker_timeout': 30,     # 30 seconds
    'max_latency_ms': 1000,   # 1 second max latency
    'min_success_rate': 0.95  # 95% minimum success rate
}
```

## Deployment Steps

### 1. Environment Setup
```bash
# Clone repository
git clone <repository_url>
cd trading-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

### 3. Initial Testing
```bash
# Run smoke tests
python -m pytest tests/smoke/

# Run pipeline in paper mode
python scripts/run_pipeline.py --mode paper

# Verify all modules load
python scripts/verify_imports.py
```

### 4. Production Deployment
```bash
# Set production environment
export TRADING_MODE=live
export KILL_SWITCH=0

# Run with supervisor
python scripts/run_pipeline.py --mode live --daemon

# Or with Docker
docker-compose up -d
```

## Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY scripts/ ./scripts/
COPY config/ ./config/

CMD ["python", "scripts/run_pipeline.py"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  trading-ai:
    build: .
    environment:
      - TRADING_MODE=${TRADING_MODE}
      - KILL_SWITCH=${KILL_SWITCH}
      - ALPACA_API_KEY=${ALPACA_API_KEY}
      - ALPACA_SECRET_KEY=${ALPACA_SECRET_KEY}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped

  redis:
    image: redis:alpine
    restart: unless-stopped
```

## Monitoring & Maintenance

### Log Management
```python
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        }
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/trading.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5
        }
    },
    'loggers': {
        'trading_ai': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False
        }
    }
}
```

### Performance Monitoring
- Monitor pipeline latency (< 100ms target)
- Track success rates (> 95% target)
- Alert on drawdown breaches
- Monitor broker connectivity

### Backup & Recovery
- Daily state backups
- Configuration versioning
- Trade execution logs
- Performance analytics snapshots

## Emergency Procedures

### Kill Switch Activation
```bash
# Immediate halt
export KILL_SWITCH=1
# Or via API
curl -X POST http://localhost:8080/kill-switch
```

### Manual Position Closure
```python
# Emergency liquidation
from trading_ai.execution.order_manager import emergency_liquidation
emergency_liquidation()
```

### System Recovery
```bash
# Restore from backup
python scripts/restore_state.py --backup latest

# Verify system health
python scripts/health_check.py
```

## Troubleshooting

### Common Issues

#### Pipeline Stalls
- Check RSS feed connectivity
- Verify broker API status
- Monitor system resources

#### High Latency
- Optimize signal processing
- Check network connectivity
- Reduce concurrent operations

#### Risk Breaches
- Review position sizes
- Check market volatility
- Verify configuration settings

### Debug Mode
```python
# Enable debug logging
import logging
logging.getLogger('trading_ai').setLevel(logging.DEBUG)

# Run with verbose output
python scripts/run_pipeline.py --verbose --debug
```

## Security Considerations

### API Key Management
- Use environment variables
- Rotate keys regularly
- Monitor API usage
- Implement rate limiting

### Network Security
- Use HTTPS for all communications
- Implement firewall rules
- Monitor for unauthorized access
- Use VPN for broker connections

### Data Protection
- Encrypt sensitive data
- Implement access controls
- Regular security audits
- Backup encryption

## Compliance

### Regulatory Requirements
- Maintain audit trails
- Implement trade surveillance
- Report suspicious activities
- Data retention policies

### Best Practices
- Regular system reviews
- Documentation updates
- Staff training
- Incident response planning
