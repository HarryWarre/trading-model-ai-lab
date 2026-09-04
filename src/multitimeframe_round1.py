import sys
import pandas as pd
import numpy as np
sys.path.insert(0, '.')
from round1_backtest import make_demo_prices, signal_frame, backtest

TIMEFRAMES = {'15m': '15min', '1h': '1h', '4h': '4h'}
COSTS = [(2.0, 1.0, 0.5), (5.0, 3.0, 1.0), (10.0, 6.0, 2.0)]

def run():
    base = make_demo_prices()
    rows = []
    for label, rule in TIMEFRAMES.items():
        px = base.resample(rule).last().dropna()
        sf = signal_frame(px)
        split = px.index[int(len(px) * 0.70)]
        bars_per_year = {'15m': 96, '1h': 24, '4h': 6}[label] * 252
        for model in ['trend', 'breakout', 'meanrev']:
            for spread, slip, fee in COSTS:
                m = backtest(px, sf[model], sf['vol'], spread_bps=spread, slip_bps=slip,
                             fee_bps=fee, test_start=split, test_end=px.index[-1])
                # Recompute annualized return using the actual timeframe.
                m['annualized_return'] = (1 + m['total_return']) ** (bars_per_year / m['bars']) - 1
                m['timeframe'] = label
                m['model'] = model
                m['cost_case'] = f'spread{spread}_slip{slip}_fee{fee}'
                rows.append(m)
    result = pd.DataFrame(rows)[['timeframe', 'model', 'cost_case', 'total_return',
                                 'annualized_return', 'sharpe', 'max_drawdown',
                                 'avg_turnover', 'positive_bars', 'bars']]
    result.to_csv('multitimeframe_round1_results.csv', index=False)
    print(result.to_string(index=False, float_format=lambda x: f'{x:,.4f}'))

if __name__ == '__main__':
    run()
