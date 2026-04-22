#!/usr/bin/env python
"""Debug P&L fix - check signal generation and price updates."""

import logging
logging.basicConfig(level=logging.INFO)

from datetime import datetime, timezone, timedelta
from src.trading_ai.backtest.backtest_engine import BacktestEngine, BacktestConfig
from src.trading_ai.strategies.hybrid_strategy import HybridStrategy

config = BacktestConfig(
    symbols=['BTC'],
    timeframe='1h',
    start_date=datetime.now(timezone.utc) - timedelta(days=1),
    end_date=datetime.now(timezone.utc),
    initial_cash=100000.0
)

engine = BacktestEngine(config=config)
engine._load_historical_data()

# Get one timestamp and check
df = list(engine.price_data.values())[0]
print(f'DataFrame shape: {df.shape}')
print(f'Columns: {list(df.columns)}')
print(f'Index type: {type(df.index[0])}')

# Create context at a middle timestamp
timestamp = df.index[30]
print(f'\nTesting timestamp: {timestamp}')

context = engine._create_strategy_context(timestamp)
print(f'\nContext market_data keys: {list(context.market_data.keys())}')

if 'BTC' in context.market_data:
    btc_data = context.market_data['BTC']
    print(f'\nBTC data keys: {list(btc_data.keys())}')
    if 'indicators' in btc_data:
        print(f'\nBTC indicators: {btc_data["indicators"]}')
    print(f'Price: {btc_data.get("price")}')

# Test strategy directly
strategy = HybridStrategy(min_confidence=0.35, require_confluence=True)
output = strategy.execute(context)
print(f'\nSignals generated: {len(output.signals)}')
for s in output.signals:
    print(f'  Signal: {s.symbol} {s.direction} conf={s.confidence:.3f}')
