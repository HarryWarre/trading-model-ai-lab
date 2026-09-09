"""Research 034: reproducible 15-asset VIX Ridge run."""
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

H, LOOKBACK, TOP_BOTTOM, ALPHA = 5, 20, 3, 10.0
FX = {"EURUSD","GBPUSD","AUDUSD","NZDUSD","USDJPY","USDCHF","USDCAD","EURJPY"}

def run(prices, vix):
    prices = prices.ffill().dropna()
    vix = vix.reindex(prices.index).ffill()
    ret = np.log(prices).diff()
    assets = list(prices.columns)
    fees = {a: (.00044 if a in FX else .0015 if a in {"XAUUSD","SPXUSD","NSXUSD","GRXEUR","UKXGBP"} else .0025) for a in assets}
    out = []
    for i in range(60, len(prices)-H, H):
        X, y = [], []
        for j in range(LOOKBACK, i-H, H):
            mom = np.log(prices.iloc[j]/prices.iloc[j-LOOKBACK])
            vol = ret.iloc[j-LOOKBACK:j].std()
            breadth = ret.iloc[j-5:j].mean().mean()
            vx, dvx = float(vix.iloc[j]), float(vix.iloc[j]-vix.iloc[j-5])
            for a in assets:
                X.append([mom[a], vol[a], mom[a]/vol[a] if vol[a] else 0,
                          breadth, vx, dvx, mom[a]*dvx])
                y.append(np.log(prices.iloc[j+H][a]/prices.iloc[j][a]))
        X, y = np.asarray(X), np.asarray(y)
        mu, sd = X.mean(0), X.std(0)
        sd[sd == 0] = 1
        model = Ridge(alpha=ALPHA).fit((X-mu)/sd, y)
        mom = np.log(prices.iloc[i]/prices.iloc[i-LOOKBACK])
        vol = ret.iloc[i-LOOKBACK:i].std()
        breadth = ret.iloc[i-5:i].mean().mean()
        vx, dvx = float(vix.iloc[i]), float(vix.iloc[i]-vix.iloc[i-5])
        pred = {}
        for a in assets:
            z = np.array([mom[a], vol[a], mom[a]/vol[a] if vol[a] else 0,
                          breadth, vx, dvx, mom[a]*dvx])
            pred[a] = model.predict(((z-mu)/sd).reshape(1,-1))[0]
        order = sorted(pred, key=pred.get)
        weights = pd.Series(0.0, index=assets)
        weights[order[:TOP_BOTTOM]] = -1/(2*TOP_BOTTOM)
        weights[order[-TOP_BOTTOM:]] = 1/(2*TOP_BOTTOM)
        path = ret.iloc[i+1:i+1+H].mul(weights, axis=1).sum(axis=1)
        fee = sum(abs(weights[a])*fees[a] for a in assets)
        path.iloc[0] -= fee
        path.iloc[-1] -= fee
        out.extend(zip(path.index, path.to_numpy()))
    return pd.Series(dict(out)).sort_index()
