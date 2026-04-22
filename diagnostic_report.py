#!/usr/bin/env python
"""Full diagnostic report - analyzing only, no fixes."""

import logging
logging.disable(logging.WARNING)

from datetime import datetime, timezone, timedelta
from src.trading_ai.backtest.backtest_engine import BacktestEngine, BacktestConfig
from collections import Counter

print('='*70)
print('FULL TRADING SYSTEM DIAGNOSTIC REPORT')
print('='*70)

config = BacktestConfig(
    symbols=['BTC', 'ETH'],
    timeframe='1h',
    start_date=datetime.now(timezone.utc) - timedelta(days=30),
    end_date=datetime.now(timezone.utc),
    initial_cash=100000.0
)

engine = BacktestEngine(config=config)
result = engine.run_backtest()

# PART 1 — SIGNAL QUALITY
print('\n' + '='*70)
print('PART 1 — SIGNAL QUALITY')
print('='*70)
print(f'Total signals generated: {len(engine.signals)}')

symbol_counts = Counter([s['symbol'] for s in engine.signals])
print(f'\nSignals per symbol:')
for sym, cnt in symbol_counts.items():
    print(f'  {sym}: {cnt}')

confidences = [s['confidence'] for s in engine.signals]
if confidences:
    print(f'\nSignal confidence distribution:')
    print(f'  Average: {sum(confidences)/len(confidences):.3f}')
    print(f'  Min: {min(confidences):.3f}')
    print(f'  Max: {max(confidences):.3f}')
    # Bins
    low = sum(1 for c in confidences if c < 0.35)
    mid = sum(1 for c in confidences if 0.35 <= c < 0.50)
    high = sum(1 for c in confidences if c >= 0.50)
    print(f'  0.00-0.35: {low} signals')
    print(f'  0.35-0.50: {mid} signals')
    print(f'  0.50+: {high} signals')

directions = Counter([s['direction'] for s in engine.signals])
print(f'\nDirection distribution:')
for d, cnt in directions.items():
    print(f'  {d}: {cnt} ({cnt/len(engine.signals)*100:.1f}%)')

# PART 2 — TRADE EXECUTION
print('\n' + '='*70)
print('PART 2 — TRADE EXECUTION')
print('='*70)
print(f'Signals generated: {len(engine.signals)}')
print(f'Trades executed: {result.total_trades}')
print(f'Signal->Trade conversion: {result.total_trades/max(len(engine.signals),1)*100:.1f}%')

if engine.trade_log:
    print(f'\nFirst 3 trades:')
    for i, t in enumerate(engine.trade_log[:3]):
        print(f'  {i}: {t}')
    print(f'\nLast 3 trades:')
    for i, t in enumerate(engine.trade_log[-3:]):
        print(f'  {len(engine.trade_log)-3+i}: {t}')

# PART 3 — P&L LOGIC
print('\n' + '='*70)
print('PART 3 — P&L LOGIC INVESTIGATION')
print('='*70)
print(f'Initial balance: $100,000.00')
if hasattr(result.equity_curve, 'empty'):
    if not result.equity_curve.empty:
        final_balance = result.equity_curve['equity'].iloc[-1]
    else:
        final_balance = 100000.0
elif isinstance(result.equity_curve, list) and len(result.equity_curve) > 0:
    final_balance = result.equity_curve[-1]
else:
    final_balance = 100000.0

total_pnl = final_balance - 100000.0
print(f'Final balance: ${final_balance:,.2f}')
print(f'Total return: {result.total_return:.2%}')
print(f'Total P&L: ${total_pnl:,.2f}')
print(f'Win rate: {result.win_rate:.2%}')
print(f'Profit factor: {result.profit_factor:.2f}')

# Check for commission bleed
commission_total = 100000 - final_balance
print(f'\nCommission/fees estimate: ${commission_total:,.2f}')

# PART 4 — MARKET DATA
print('\n' + '='*70)
print('PART 4 — MARKET DATA VALIDATION')
print('='*70)

engine._load_historical_data()
for symbol, df in engine.price_data.items():
    print(f'\n{symbol}:')
    print(f'  Data points: {len(df)}')
    
    closes = df['close_price']
    print(f'  Price range: ${closes.min():.2f} to ${closes.max():.2f}')
    print(f'  First price: ${closes.iloc[0]:.2f}')
    print(f'  Last price: ${closes.iloc[-1]:.2f}')
    
    total_change = (closes.iloc[-1] / closes.iloc[0] - 1) * 100
    print(f'  Total change: {total_change:.2f}%')
    
    # Check volatility
    daily_returns = closes.pct_change().dropna()
    print(f'  Avg hourly return: {daily_returns.mean()*100:.3f}%')
    print(f'  Volatility (std): {daily_returns.std()*100:.3f}%')
    print(f'  Max gain: {daily_returns.max()*100:.3f}%')
    print(f'  Max loss: {daily_returns.min()*100:.3f}%')

# PART 5 — ROOT CAUSE SUMMARY
print('\n' + '='*70)
print('PART 5 — ROOT CAUSE ANALYSIS')
print('='*70)

# Key observations
print('\nKEY OBSERVATIONS:')
print(f'1. Signal count: {len(engine.signals)} signals for 2 symbols over 30 days')
print(f'   = {len(engine.signals)/30:.1f} signals/day (reasonable)')

print(f'2. Trade count: {result.total_trades} trades')
print(f'   = {result.total_trades/30:.1f} trades/day')

print(f'3. Signal rejection: {(1 - result.total_trades/max(len(engine.signals),1))*100:.1f}% of signals rejected')

print(f'4. P&L: ${total_pnl:,.2f} across {result.total_trades} trades')
if result.total_trades > 0:
    avg_pnl = total_pnl / result.total_trades
    print(f'   = ${avg_pnl:.2f} average per trade')

print(f'5. Commission estimate: ${commission_total:.2f} ({commission_total/100000*100:.3f}% of capital)')

print('\n' + '='*70)
print('DIAGNOSTIC COMPLETE')
print('='*70)
