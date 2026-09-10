"""Research 037 intraday multi-input model for the Colab runner.

Input: prepared long panel with timestamp, asset, close.
Decision cadence: hourly UTC. Target: next 12 five-minute bars.
Model: expanding walk-forward HistGradientBoostingRegressor.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor


HORIZON = 12
RETRAIN_WEEKDAYS = 21
SEED = 37037


def metrics(x: pd.Series) -> dict:
    x = pd.Series(x).dropna()
    if x.empty:
        return {"observations": 0}
    equity = np.exp(x.cumsum())
    sd = x.std()
    return {
        "observations": int(len(x)),
        "total_return": float(equity.iloc[-1] - 1),
        "annualized_mean": float(x.mean() * 252 * 16),
        "sharpe": float(np.sqrt(252 * 16) * x.mean() / sd) if sd > 0 else None,
        "max_drawdown": float((equity / equity.cummax() - 1).min()),
    }


def load_panel() -> pd.DataFrame:
    root = Path(os.environ.get(
        "QUANT_DRIVE_ROOT", "/content/drive/MyDrive/trading-model-ai-lab"
    ))
    path = Path(os.environ.get(
        "QUANT_PANEL_OUTPUT", root / "data" / "prepared_intraday_panel.csv"
    ))
    if not path.exists():
        raise SystemExit(f"Prepared panel not found: {path}. Run prepare first.")
    panel = pd.read_csv(path, parse_dates=["timestamp"])
    required = {"timestamp", "asset", "close"}
    if not required.issubset(panel.columns):
        raise SystemExit(f"Prepared panel missing columns: {required - set(panel.columns)}")
    panel["timestamp"] = pd.to_datetime(panel["timestamp"], utc=True)
    panel["close"] = pd.to_numeric(panel["close"], errors="coerce")
    panel = panel.dropna(subset=["timestamp", "asset", "close"])
    return panel.pivot(index="timestamp", columns="asset", values="close").sort_index()


def load_vix(index: pd.DatetimeIndex) -> pd.Series:
    path_value = os.environ.get("QUANT_VIX_FILE", "").strip()
    if not path_value:
        return pd.Series(0.0, index=index, name="vix_missing")
    path = Path(path_value)
    if not path.exists():
        raise SystemExit(f"VIX file configured but missing: {path}")
    raw = pd.read_csv(path)
    date_col = "observation_date" if "observation_date" in raw else raw.columns[0]
    value_col = "VIXCLS" if "VIXCLS" in raw else raw.columns[1]
    raw[date_col] = pd.to_datetime(raw[date_col], utc=True, errors="coerce")
    values = pd.to_numeric(raw[value_col], errors="coerce")
    vix = pd.Series(values.to_numpy(), index=raw[date_col]).dropna()
    return vix.reindex(index.normalize(), method="ffill").set_axis(index)


def family_bps(asset: str) -> float:
    a = asset.upper()
    if "XAU" in a or "XAG" in a or "BCO" in a:
        return 2.0
    if any(k in a for k in ["SPX", "NSX", "GRX", "UKX"]):
        return 2.0
    return 1.0


def make_features(prices: pd.DataFrame, vix: pd.Series) -> tuple[pd.DataFrame, pd.Series]:
    ret = np.log(prices / prices.shift(1))
    rows = []
    for asset in prices.columns:
        f = pd.DataFrame(index=prices.index)
        f["r_5m"] = ret[asset]
        f["r_30m"] = np.log(prices[asset] / prices[asset].shift(6))
        f["r_120m"] = np.log(prices[asset] / prices[asset].shift(24))
        f["vol_60m"] = ret[asset].rolling(12).std()
        f["vol_120m"] = ret[asset].rolling(24).std()
        f["breadth"] = (ret.gt(0).sum(axis=1) / ret.notna().sum(axis=1)).replace(
            [np.inf, -np.inf], np.nan
        )
        f["hour_sin"] = np.sin(2 * np.pi * f.index.hour / 24)
        f["hour_cos"] = np.cos(2 * np.pi * f.index.hour / 24)
        f["vix"] = vix
        f["asset_code"] = float(list(prices.columns).index(asset))
        f["asset"] = asset
        f["target"] = np.log(prices[asset].shift(-HORIZON) / prices[asset])
        rows.append(f.reset_index(names="timestamp"))
    data = pd.concat(rows, ignore_index=True)
    return data.dropna(), ret


def main() -> None:
    root = Path(os.environ.get(
        "QUANT_DRIVE_ROOT", "/content/drive/MyDrive/trading-model-ai-lab"
    ))
    prices = load_panel()
    if prices.shape[1] < 15:
        raise SystemExit(f"Only {prices.shape[1]} assets available; minimum is 15.")
    vix = load_vix(prices.index)
    data, returns = make_features(prices, vix)
    decisions = sorted(
        t for t in prices.index
        if t.weekday() < 5 and 8 <= t.hour <= 23 and t.minute == 0
    )
    if len(decisions) < 30:
        raise SystemExit(f"Only {len(decisions)} hourly decisions available.")

    records = []
    last_train_date = None
    model = None
    feature_cols = [
        "r_5m", "r_30m", "r_120m", "vol_60m", "vol_120m",
        "breadth", "hour_sin", "hour_cos", "vix", "asset_code",
    ]
    previous_weights = {a: 0.0 for a in prices.columns}
    for decision in decisions:
        decision = pd.Timestamp(decision)
        train = data[data["timestamp"] < decision]
        if train.empty:
            continue
        weekdays = train["timestamp"].dt.normalize().dt.dayofweek.lt(5)
        train_days = train.loc[weekdays, "timestamp"].dt.normalize().nunique()
        if model is None or last_train_date is None or train_days % RETRAIN_WEEKDAYS == 0:
            if len(train) < 500:
                continue
            model = HistGradientBoostingRegressor(
                max_iter=50, max_depth=2, learning_rate=0.05,
                l2_regularization=1.0, random_state=SEED
            )
            model.fit(train[feature_cols], train["target"])
            last_train_date = decision

        current = data[data["timestamp"] == decision].copy()
        if current.empty:
            continue
        current["prediction"] = model.predict(current[feature_cols])
        current = current.sort_values(["prediction", "asset"])
        chosen = set(current.tail(3)["asset"]) | set(current.head(3)["asset"])
        weights = {a: 0.0 for a in prices.columns}
        for a in current.head(3)["asset"]:
            weights[a] = -1 / 6
        for a in current.tail(3)["asset"]:
            weights[a] = 1 / 6

        end = decision + pd.Timedelta(hours=1)
        path = prices.loc[(prices.index > decision) & (prices.index <= end), prices.columns]
        if len(path) < 2:
            continue
        gross = 0.0
        for asset, weight in weights.items():
            if weight == 0 or path[asset].dropna().shape[0] < 2:
                continue
            gross += weight * np.log(path[asset].dropna().iloc[-1] / path[asset].dropna().iloc[0])
        # Charge only for target-weight changes, including the initial opening trade.
        turnover = sum(abs(weights[a] - previous_weights[a]) for a in prices.columns)
        cost_bps = sum(
            family_bps(a) * abs(weights[a] - previous_weights[a])
            for a in prices.columns
        )
        net = gross - cost_bps / 10000
        previous_weights = weights.copy()
        records.append({
            "decision": decision.isoformat(),
            "gross_log_return": float(gross),
            "cost_log_return": float(cost_bps / 10000),
            "net_log_return": float(net),
            "cost_bps_weighted": float(cost_bps),
            "turnover": float(turnover),
            "assets_traded": int(len(chosen)),
            "trained_at": str(last_train_date),
        })

    result = pd.DataFrame(records)
    if result.empty:
        raise SystemExit("No out-of-sample decisions were produced.")
    root.mkdir(parents=True, exist_ok=True)
    result.to_csv(root / "intraday_model_decisions.csv", index=False)
    summary = {
        "model": "research_037_histgradientboosting",
        "assets": int(prices.shape[1]),
        "decisions": int(len(result)),
        "vix_used": bool(os.environ.get("QUANT_VIX_FILE")),
        **metrics(result["net_log_return"]),
    }
    (root / "intraday_model_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
