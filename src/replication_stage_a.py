"""Stage A academic TSMOM replication primitives."""
import numpy as np
import pandas as pd


def tsmom_returns(prices, lookback=12, target_vol=0.40, vol_window=12):
    """Monthly-style TSMOM returns from a price panel.

    The signal uses trailing own-asset return and is lagged before the next
    period return. Inputs must already be point-in-time and consistently
    rolled. No transaction costs are included here.
    """
    log_r = np.log(prices).diff()
    trailing = np.log(prices / prices.shift(lookback))
    sigma = log_r.rolling(vol_window).std() * np.sqrt(12)
    signal = np.sign(trailing).shift(1)
    scale = target_vol / sigma.clip(lower=1e-8)
    return signal * scale * log_r


def return_attribution(total_returns, spot_returns, roll_returns):
    """Align and return total/spot/roll attribution with residual."""
    total, spot, roll = [pd.DataFrame(x) for x in (total_returns, spot_returns, roll_returns)]
    total, spot, roll = total.align(spot, join='inner', axis=0)[0], spot.align(roll, join='inner', axis=0)[0], roll
    common = total.columns.intersection(spot.columns).intersection(roll.columns)
    total, spot, roll = total[common], spot[common], roll[common]
    residual = total - spot - roll
    parts = []
    for name, frame in [('total', total), ('spot', spot), ('roll', roll), ('residual', residual)]:
        frame = frame.copy()
        frame.columns = pd.MultiIndex.from_product([[name], frame.columns])
        parts.append(frame)
    return pd.concat(parts, axis=1).dropna()


def class_equal_weight(returns, asset_classes):
    """Equal-weight asset-class portfolios, then equal-weight classes."""
    class_returns = {}
    for cls in sorted(set(asset_classes.values())):
        cols = [c for c in returns.columns if asset_classes.get(c) == cls]
        if cols:
            class_returns[cls] = returns[cols].mean(axis=1)
    return pd.DataFrame(class_returns).mean(axis=1)
