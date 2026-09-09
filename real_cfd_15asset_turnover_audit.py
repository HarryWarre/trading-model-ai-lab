"""Research 035: audit turnover-based costs for the frozen 15-asset Ridge+VIX model.

This deliberately reuses the Research 034 feature design. The only change is
economic accounting: costs are charged when weights change, with one final
liquidation, rather than at arbitrary five-day block boundaries.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

H, LOOKBACK, TOP_BOTTOM, ALPHA, START = 5, 20, 3, 10.0, 60
FX = {"EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDJPY", "USDCHF", "USDCAD", "EURJPY"}

def fees(prices):
    base = {a: (.00044 if a in FX else .0015 if a in {"XAUUSD", "SPXUSD", "NSXUSD", "GRXEUR", "UKXGBP"} else .0025) for a in prices}
    return pd.DataFrame({a: base[a] / prices[a] for a in prices}, index=prices.index)

def metrics(log_returns):
    x = log_returns.dropna(); equity = np.exp(x.cumsum())
    return {"observations": len(x), "net_return": equity.iloc[-1]-1, "annualized_mean": x.mean()*252,
            "sharpe": np.sqrt(252)*x.mean()/x.std() if x.std() else np.nan,
            "max_drawdown": (equity/equity.cummax()-1).min()}

def model(prices, vix):
    prices = prices.ffill().dropna(); assets = list(prices.columns)
    vix = vix.reindex(prices.index).ffill(); returns = np.log(prices).diff()
    positions = pd.DataFrame(0.0, index=prices.index, columns=assets); decisions = []
    for i in range(START, len(prices)-H, H):
        X, y = [], []
        for j in range(LOOKBACK, i-H, H):
            mom = np.log(prices.iloc[j]/prices.iloc[j-LOOKBACK]); vol = returns.iloc[j-LOOKBACK:j].std()
            breadth = returns.iloc[j-5:j].mean().mean(); vx = float(vix.iloc[j]); dvx = float(vix.iloc[j]-vix.iloc[j-5])
            for a in assets:
                X.append([mom[a],vol[a],mom[a]/vol[a] if vol[a] else 0.0,breadth,vx,dvx,mom[a]*dvx])
                y.append(np.log(prices.iloc[j+H][a]/prices.iloc[j][a]))
        X=np.asarray(X); y=np.asarray(y); mean, sd=X.mean(0),X.std(0); sd[sd==0]=1
        reg=Ridge(alpha=ALPHA).fit((X-mean)/sd,y)
        mom=np.log(prices.iloc[i]/prices.iloc[i-LOOKBACK]); vol=returns.iloc[i-LOOKBACK:i].std()
        breadth=returns.iloc[i-5:i].mean().mean(); vx=float(vix.iloc[i]); dvx=float(vix.iloc[i]-vix.iloc[i-5])
        pred={}
        for a in assets:
            z=np.array([mom[a],vol[a],mom[a]/vol[a] if vol[a] else 0.0,breadth,vx,dvx,mom[a]*dvx])
            pred[a]=reg.predict(((z-mean)/sd).reshape(1,-1))[0]
        order=sorted(pred,key=pred.get); w=pd.Series(0.0,index=assets)
        w[order[:TOP_BOTTOM]]=-1/(2*TOP_BOTTOM); w[order[-TOP_BOTTOM:]]=1/(2*TOP_BOTTOM)
        positions.iloc[i+1:min(i+1+H,len(prices))]=w.to_numpy()
        decisions.append({"decision":prices.index[i],"lowest":order[0],"highest":order[-1]})
    return positions,(positions*returns).sum(axis=1),pd.DataFrame(decisions)

def run():
    prices=pd.read_csv("cfd_daily_prices_15_2024.csv",parse_dates=["ts"]).set_index("ts")
    vix=pd.read_csv("vixcls.csv",parse_dates=["observation_date"]).set_index("observation_date").iloc[:,0]
    w,gross,decisions=model(prices,vix); px=prices.ffill().dropna().reindex(w.index); fee=fees(px)
    turnover=w.diff().abs(); turnover.iloc[0]=w.iloc[0].abs(); cost=(turnover*fee).sum(axis=1)
    last=w.index[w.abs().sum(axis=1).gt(0)][-1]; cost.loc[last]+=(w.loc[last].abs()*fee.loc[last]).sum()
    valid=w.abs().sum(axis=1).gt(0); corrected=(gross-cost)[valid]; old=gross.copy()
    for d in decisions["decision"]:
        start=w.index.get_indexer([d],method="nearest")[0]+1; active=w.iloc[start]; block=w.index[start:min(start+H,len(w))]
        if len(block):
            block_fee=(active.abs()*fee.loc[block[0]]).sum(); old.loc[block[0]]-=block_fee; old.loc[block[-1]]-=block_fee
    old=old[valid]; annual_turnover=turnover[valid].sum().sum()/(len(corrected)/252)
    summary=pd.DataFrame([
        {"model":"prior_block_fee_approximation",**metrics(old),"charged_cost_log":float((gross[valid]-old).sum()),"annual_turnover":annual_turnover},
        {"model":"corrected_turnover_cost",**metrics(corrected),"charged_cost_log":float(cost[valid].sum()),"annual_turnover":annual_turnover}])
    daily=pd.DataFrame({"gross_log_return":gross[valid],"prior_net_log_return":old,"corrected_net_log_return":corrected,"turnover_cost_log":cost[valid],"gross_turnover":turnover[valid].sum(axis=1)})
    return summary,daily,decisions,vix.reindex(daily.index).ffill()

def robustness(daily,vix):
    rows=[]
    for multiple in (0.,1.,2.,4.):
        rows.append({"check":f"cost_{multiple:g}x",**metrics(daily["gross_log_return"]-multiple*daily["turnover_cost_log"])})
    rng=np.random.default_rng(35035); x=daily["corrected_net_log_return"].to_numpy()
    draws=x[rng.integers(0,len(x),size=(5000,len(x)))].mean(axis=1)*252
    rows.append({"check":"iid_bootstrap_5000","mean_positive_probability":float((draws>0).mean()),"annualized_mean_ci_low":float(np.quantile(draws,.025)),"annualized_mean_ci_high":float(np.quantile(draws,.975))})
    q75=vix.quantile(.75)
    regimes=pd.DataFrame([{"regime":"low_or_equal_vix_q75","days":int((vix<=q75).sum()),**metrics(daily.loc[vix<=q75,"corrected_net_log_return"])},{"regime":"high_vix","days":int((vix>q75).sum()),**metrics(daily.loc[vix>q75,"corrected_net_log_return"])}])
    chunks=np.array_split(daily.index,4)
    phases=pd.DataFrame([{"phase":i+1,"start":part[0],"end":part[-1],**metrics(daily.loc[part,"corrected_net_log_return"])} for i,part in enumerate(chunks)])
    return pd.DataFrame(rows),regimes,phases

if __name__=="__main__":
    s,d,a,v=run(); r,g,p=robustness(d,v)
    s.to_csv("real_cfd_15asset_turnover_audit_results.csv",index=False); d.to_csv("real_cfd_15asset_turnover_audit_daily.csv"); a.to_csv("real_cfd_15asset_turnover_audit_decisions.csv",index=False)
    r.to_csv("real_cfd_15asset_turnover_audit_robustness.csv",index=False); g.to_csv("real_cfd_15asset_turnover_audit_regimes.csv",index=False); p.to_csv("real_cfd_15asset_turnover_audit_phases.csv",index=False)
