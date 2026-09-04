import glob
import numpy as np
import pandas as pd


def load_pair(path):
    x = pd.read_csv(path)
    x['timestamp_utc'] = pd.to_datetime(x['Date'], utc=True)
    cols = ['open', 'high', 'low', 'close']
    x[cols] = x[cols] / 100000.0
    return x.sort_values('timestamp_utc').drop_duplicates('timestamp_utc').set_index('timestamp_utc')


def run(lookback, cost_pips=2.2):
    pairs = ['AUDUSD', 'EURUSD', 'GBPUSD', 'USDJPY']
    prices = pd.concat({p: load_pair(f'{p}_h4.csv')['close'] for p in pairs}, axis=1).dropna()
    r = np.log(prices).diff()
    vol = r.rolling(60).std() * np.sqrt(6 * 252)
    signal = np.sign(np.log(prices / prices.shift(lookback)))
    weights = (signal * (0.10 / vol.clip(lower=0.02))).clip(-1, 1).shift(1).fillna(0)
    turnover = weights.diff().abs().fillna(weights.abs())
    # Equal-weight the four instrument sleeves after per-asset vol scaling.
    gross = (weights * r).mean(axis=1)
    costs = (turnover * cost_pips * 0.0001 / prices).mean(axis=1)
    pnl = (gross - costs).dropna()
    split = int(len(pnl) * 0.70)
    oos = pnl.iloc[split:]
    equity = np.exp(oos.cumsum())
    dd = equity / equity.cummax() - 1
    ann = 6 * 252
    return {
        'lookback_h4': lookback,
        'oos_start': str(oos.index[0].date()),
        'oos_end': str(oos.index[-1].date()),
        'total_return': equity.iloc[-1] - 1,
        'annualized_return': equity.iloc[-1] ** (ann / len(oos)) - 1,
        'sharpe': np.sqrt(ann) * oos.mean() / oos.std(),
        'max_drawdown': dd.min(),
        'annualized_turnover': turnover.iloc[split:].mean().mean() * ann,
    }


if __name__ == '__main__':
    result = pd.DataFrame([run(lb) for lb in [6, 12, 30]])
    result.to_csv('real_fx_round2_results.csv', index=False)
    print(result.to_string(index=False, float_format=lambda x: f'{x:,.4f}'))
