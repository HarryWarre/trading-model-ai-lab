"""Cross-asset H4 partial-adjustment TSMOM for four FX pairs and XAUUSD."""
import numpy as np
import pandas as pd

FX = ["AUDUSD", "EURUSD", "GBPUSD", "USDJPY"]
ASSETS = FX + ["XAUUSD"]
LOOKBACKS = [6, 12, 30]
SPEEDS = [1.0, 0.5, 0.25, 0.10]
ANN = 6 * 252


def load_prices():
    out = {}
    for asset in ASSETS:
        x = pd.read_csv(f"{asset}_h4.csv")
        x["timestamp_utc"] = pd.to_datetime(x["Date"], utc=True)
        scale = 100.0 if asset == "XAUUSD" else (1000.0 if asset.endswith("JPY") else 100000.0)
        x["close"] = x["close"] / scale
        x = x.sort_values("timestamp_utc").drop_duplicates("timestamp_utc")
        out[asset] = x.set_index("timestamp_utc")["close"]
    return pd.concat(out, axis=1).dropna()


def partial_adjust(target, speed):
    values = target.to_numpy(dtype=float)
    position = np.empty_like(values)
    current = np.zeros(values.shape[1], dtype=float)
    for i in range(len(values)):
        available = np.isfinite(values[i])
        current[available] += speed * (values[i, available] - current[available])
        position[i] = current
    return pd.DataFrame(position, index=target.index, columns=target.columns).shift(1).fillna(0.0)


def cost_series(turnover, prices):
    parts = []
    for asset in prices.columns:
        if asset == "XAUUSD":
            parts.append(turnover[asset] * 5.0e-4)
        else:
            pip = 0.01 if asset.endswith("JPY") else 0.0001
            parts.append(turnover[asset] * 2.2 * pip / prices[asset])
    return sum(parts) / len(parts)


def run():
    prices = load_prices()
    returns = np.log(prices).diff()
    vol = returns.rolling(60).std() * np.sqrt(ANN)
    split = int(len(prices) * 0.70)
    rows = []
    for lookback in LOOKBACKS:
        target = (np.sign(np.log(prices / prices.shift(lookback)))
                  * (0.10 / vol.clip(lower=0.02))).clip(-1, 1)
        for speed in SPEEDS:
            weights = partial_adjust(target, speed)
            turnover = weights.diff().abs().fillna(weights.abs())
            gross = (weights * returns).mean(axis=1)
            net = gross - cost_series(turnover, prices)
            oos = net.iloc[split:].dropna()
            equity = np.exp(oos.cumsum())
            dd = equity / equity.cummax() - 1.0
            yearly = oos.groupby(oos.index.year).sum().map(np.exp).sub(1.0)
            rows.append({
                "lookback_h4": lookback,
                "adjustment_speed": speed,
                "oos_start": str(oos.index[0].date()),
                "oos_end": str(oos.index[-1].date()),
                "observations": len(oos),
                "net_total_return": equity.iloc[-1] - 1.0,
                "net_annualized_return": equity.iloc[-1] ** (ANN / len(oos)) - 1.0,
                "net_sharpe": np.sqrt(ANN) * oos.mean() / oos.std(),
                "net_max_drawdown": dd.min(),
                "annualized_turnover": turnover.iloc[split:].mean().mean() * ANN,
                "positive_calendar_year_fraction": (yearly > 0).mean(),
            })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    out = run()
    out.to_csv("real_multasset_partial_adjustment_results.csv", index=False)
    print(out.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
