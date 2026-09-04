import numpy as np
import pandas as pd

SEED = 42
N = 80_000
ASSETS = ['INDEX_A', 'INDEX_B', 'FX_A', 'METAL_A', 'ENERGY_A', 'BOND_A']


def make_demo_prices():
    rng = np.random.default_rng(SEED)
    dates = pd.date_range('2015-01-01', periods=N, freq='15min', tz='UTC')
    # Synthetic regime process: persistent trend regimes alternate with range regimes.
    regime = np.where((np.arange(N) // 3_000) % 3 == 0, 1, np.where((np.arange(N) // 3_000) % 3 == 1, -1, 0))
    out = {}
    loadings = np.array([1.0, 1.2, 0.7, 0.9, 1.4, 0.5])
    for i, asset in enumerate(ASSETS):
        noise = rng.normal(0, 0.0008 * loadings[i], N)
        common = rng.normal(0, 0.00025, N)
        drift = regime * (0.00012 + i * 0.000006) + common
        r = drift + noise
        # occasional jumps to test stop/volatility behavior
        jumps = rng.random(N) < 0.00025
        r[jumps] += rng.normal(0, 0.006 * loadings[i], jumps.sum())
        out[asset] = 100 * np.exp(np.cumsum(r))
    return pd.DataFrame(out, index=dates)


def signal_frame(px, fast=32, slow=160, zwin=80):
    ret = px.pct_change()
    vol = ret.rolling(zwin).std() * np.sqrt(96 * 252)
    trend = np.sign(px.rolling(fast).mean() - px.rolling(slow).mean())
    breakout = np.where(px > px.rolling(slow).max().shift(1), 1,
                        np.where(px < px.rolling(slow).min().shift(1), -1, 0))
    mr_z = (px - px.rolling(zwin).mean()) / px.rolling(zwin).std()
    meanrev = -np.sign(mr_z.where(mr_z.abs() > 1.5, 0))
    return {'trend': trend, 'breakout': pd.DataFrame(breakout, index=px.index, columns=px.columns),
            'meanrev': meanrev, 'vol': vol}


def backtest(px, sig, vol, spread_bps=2.0, slip_bps=1.0, fee_bps=0.5,
             max_hold=384, train_end=None, test_start=None, test_end=None):
    # Signals are shifted one bar: execution occurs after signal formation.
    s = sig.shift(1).fillna(0)
    r = px.pct_change().fillna(0)
    # volatility targeting, capped; position is direction times 10% annualized risk target / asset vol
    w = s * (0.10 / vol.replace(0, np.nan)).clip(upper=2.0).fillna(0)
    w = w.clip(-1.0, 1.0)
    turnover = w.diff().abs().fillna(w.abs())
    costs = turnover * ((spread_bps + 2 * slip_bps + fee_bps) / 10_000)
    pnl = (w * r) - costs
    if test_start is not None:
        mask = pnl.index >= test_start
        if test_end is not None:
            mask &= pnl.index <= test_end
        pnl = pnl.loc[mask]
        turnover = turnover.loc[mask]
    port = pnl.mean(axis=1)
    eq = (1 + port).cumprod()
    dd = eq / eq.cummax() - 1
    ann = 96 * 252
    sharpe = np.sqrt(ann) * port.mean() / port.std() if port.std() else np.nan
    return {
        'total_return': eq.iloc[-1] - 1,
        'annualized_return': eq.iloc[-1] ** (ann / len(port)) - 1,
        'sharpe': sharpe,
        'max_drawdown': dd.min(),
        'avg_turnover': turnover.mean().mean() * ann,
        'positive_bars': (port > 0).mean(),
        'bars': len(port),
    }


def main():
    px = make_demo_prices()
    sf = signal_frame(px)
    split = px.index[int(len(px) * 0.70)]
    test_end = px.index[-1]
    rows = []
    for model in ['trend', 'breakout', 'meanrev']:
        for costs in [(2.0, 1.0, 0.5), (5.0, 3.0, 1.0), (10.0, 6.0, 2.0)]:
            m = backtest(px, sf[model], sf['vol'], spread_bps=costs[0], slip_bps=costs[1], fee_bps=costs[2], test_start=split, test_end=test_end)
            rows.append({'model': model, 'cost_case': f'spread{costs[0]}_slip{costs[1]}_fee{costs[2]}', **m})
    result = pd.DataFrame(rows)
    result.to_csv('round1_results.csv', index=False)
    print(result.to_string(index=False, float_format=lambda x: f'{x:,.4f}'))
    print(f'\nSynthetic data: {len(px):,} bars, {len(ASSETS)} assets, OOS starts {split.date()}')


if __name__ == '__main__':
    main()
