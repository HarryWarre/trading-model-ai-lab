import pandas as pd
import numpy as np


def load(path):
    x = pd.read_csv(path)
    x['timestamp_utc'] = pd.to_datetime(x['Date'], utc=True)
    # Provider stores EURUSD with 5 decimal places shifted by 1e5.
    for c in ['open', 'high', 'low', 'close']:
        x[c] = x[c] / 100000.0
    x = x.sort_values('timestamp_utc').drop_duplicates('timestamp_utc')
    return x.set_index('timestamp_utc')[['open', 'high', 'low', 'close', 'tick_volume']]


def run_one(x, lookback, vol_window=60, target_vol=0.10, cost_pips=2.2):
    close = x['close']
    r = np.log(close).diff()
    trailing = np.log(close / close.shift(lookback))
    vol = r.rolling(vol_window).std() * np.sqrt(6 * 252)
    pos = (np.sign(trailing) * (target_vol / vol.clip(lower=0.02))).clip(-1, 1).shift(1).fillna(0)
    turnover = pos.diff().abs().fillna(pos.abs())
    cost = turnover * cost_pips * 0.0001 / close
    pnl = pos * r - cost
    split = int(len(pnl) * 0.70)
    oos = pnl.iloc[split:].dropna()
    equity = np.exp(oos.cumsum())
    dd = equity / equity.cummax() - 1
    ann = 6 * 252
    return {
        'lookback_bars': lookback,
        'cost_pips_roundtrip': cost_pips,
        'oos_start': str(oos.index[0].date()),
        'oos_end': str(oos.index[-1].date()),
        'bars': len(oos),
        'total_return': float(equity.iloc[-1] - 1),
        'annualized_return': float(equity.iloc[-1] ** (ann / len(oos)) - 1),
        'sharpe': float(np.sqrt(ann) * oos.mean() / oos.std()),
        'max_drawdown': float(dd.min()),
        'trades_proxy': int((turnover.iloc[split:] > 0.05).sum()),
    }


def main():
    x = load('eurusd_h4.csv')
    results = pd.DataFrame([run_one(x, lb) for lb in [6, 12, 30]])
    results.to_csv('real_eurusd_h4_round1_results.csv', index=False)
    print('DATA', x.index[0], x.index[-1], len(x), 'bars')
    print(results.to_string(index=False, float_format=lambda v: f'{v:,.4f}'))


if __name__ == '__main__':
    main()
