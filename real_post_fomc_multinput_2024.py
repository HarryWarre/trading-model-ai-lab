"""Research 041: timing-safe post-FOMC reaction on the frozen 15-asset panel."""
from __future__ import annotations

import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd

ASSETS = ["AUDUSD","BCOUSD","EURJPY","EURUSD","GBPUSD","GRXEUR","NSXUSD","NZDUSD","SPXUSD","UKXGBP","USDCAD","USDCHF","USDJPY","XAGUSD","XAUUSD"]
PIP = {a: (0.01 if a in {"USDJPY","EURJPY"} else 0.0001) for a in ASSETS}
PIP.update({"XAUUSD":0.01,"XAGUSD":0.001,"BCOUSD":0.01,"SPXUSD":0.1,"NSXUSD":0.1,"GRXEUR":0.1,"UKXGBP":0.1})
FAMILY = {a:("equity" if a in {"SPXUSD","NSXUSD","GRXEUR","UKXGBP"} else "fx" if a not in {"XAUUSD","XAGUSD","BCOUSD"} else "metal" if a != "BCOUSD" else "energy") for a in ASSETS}
PANEL_SHA = "e632e54adb79e027e991bb335a917e9a7a30e16c6ddf33b0daecc9ceeae5d05c"
SEED = 41041

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20), b""): h.update(b)
    return h.hexdigest()

def load_panel(path: Path) -> pd.DataFrame:
    if sha256(path) != PANEL_SHA: raise ValueError("panel SHA-256 mismatch")
    x=pd.read_csv(path); need={"timestamp",*ASSETS}
    if not need.issubset(x.columns): raise ValueError("panel schema mismatch")
    x["timestamp"]=pd.to_datetime(x.timestamp, utc=True, errors="raise")
    if x.timestamp.duplicated().any(): raise ValueError("duplicate timestamps")
    x=x.set_index("timestamp").sort_index()[ASSETS]
    for a in ASSETS: x[a]=pd.to_numeric(x[a],errors="coerce")
    return x

def load_events(path: Path) -> pd.DataFrame:
    x=pd.read_csv(path)
    x["release_timestamp_utc"]=pd.to_datetime(x.release_timestamp_utc,utc=True,errors="raise")
    req={"event_id","release_timestamp_utc","source_url"}
    if not req.issubset(x.columns) or len(x)!=8 or x.event_id.duplicated().any(): raise ValueError("event schema/count mismatch")
    if not x.source_url.str.startswith("https://www.federalreserve.gov/").all(): raise ValueError("unverified event source")
    return x.sort_values("release_timestamp_utc").reset_index(drop=True)

def quote(s: pd.Series, t: pd.Timestamp) -> tuple[float,pd.Timestamp]:
    z=s.loc[t:].dropna()
    if z.empty or z.index[0]-t>pd.Timedelta(minutes=10): raise ValueError("stale or missing quote")
    return float(z.iloc[0]), z.index[0]

def prevol(s: pd.Series, t: pd.Timestamp) -> float:
    z=s.loc[(s.index>=t-pd.Timedelta(days=20))&(s.index<t)].dropna()
    r=np.log(z).diff().dropna(); r=r.loc[r.index.to_series().diff()<=pd.Timedelta(minutes=10)]
    if len(r)<100: raise ValueError("insufficient volatility history")
    v=float(r.std(ddof=1));
    if not np.isfinite(v) or v<=0: raise ValueError("invalid volatility")
    return v

def vix_value(path: Path, t: pd.Timestamp) -> float:
    x=pd.read_csv(path); x["observation_date"]=pd.to_datetime(x.observation_date,utc=True)
    x["VIXCLS"]=pd.to_numeric(x.VIXCLS,errors="coerce"); x=x.dropna().sort_values("observation_date")
    z=x.loc[x.observation_date < t.normalize()]
    if z.empty: raise ValueError("missing lagged VIX")
    return float(z.iloc[-1].VIXCLS)

def build_rows(prices, events, vix_path):
    rows=[]
    for e in events.itertuples(index=False):
        t0=e.release_timestamp_utc; t1=t0+pd.Timedelta(minutes=5); te=t0+pd.Timedelta(minutes=60); v=vix_value(vix_path,t0)
        for a in ASSETS:
            try:
                p0,q0=quote(prices[a],t0); p1,q1=quote(prices[a],t1); pe,qe=quote(prices[a],te); vol=prevol(prices[a],t0)
            except ValueError: continue
            r0=float(np.log(p1/p0)); rf=float(np.log(pe/p1))
            rows.append({"event_id":e.event_id,"release_timestamp_utc":t0,"asset":a,"p0":p0,"p1":p1,"pe":pe,"q0":q0,"q1":q1,"qe":qe,"initial_log_return":r0,"future_log_return":rf,"pre_event_vol":vol,"vix":v})
    out=pd.DataFrame(rows)
    if out.empty: raise ValueError("no valid event/asset rows")
    return out

def ridge_signal(train, row):
    if len(train)<3: return np.sign(row.initial_log_return)
    cols=["initial_z","vix_z"]
    mu=train[cols].mean(); sd=train[cols].std(ddof=0).replace(0,1.0)
    X=((train[cols]-mu)/sd).to_numpy(); y=train.future_log_return.to_numpy()
    X=np.c_[np.ones(len(X)),X]; lam=1.0
    beta=np.linalg.solve(X.T@X+lam*np.eye(X.shape[1]), X.T@y)
    xx=np.r_[1, ((row[cols]-mu)/sd).to_numpy()]
    return np.sign(float(xx@beta))

def strategy(rows, kind, equal_weight=False):
    x=rows.copy(); x["initial_z"]=x.initial_log_return/x.pre_event_vol
    x["vix_z"]=x.vix
    signals=[]
    for ev, g in x.groupby("event_id",sort=True):
        prior=x.loc[x.release_timestamp_utc < g.release_timestamp_utc.iloc[0]]
        for idx,row in g.iterrows():
            sig=np.sign(row.initial_log_return) if kind=="price_only" else ridge_signal(prior, row)
            signals.append((idx,sig))
    x["signal"]=0.0
    for idx,sig in signals: x.loc[idx,"signal"]=sig
    x=x[x.signal!=0].copy()
    x["invvol"]=1/x.pre_event_vol
    if equal_weight:
        x["weight"]=x.groupby("event_id").asset.transform(lambda z:1.0/len(z))
    else:
        x["weight"]=x.groupby("event_id").invvol.transform(lambda z:z/z.sum())
    x["gross"]=x.weight*x.signal*x.future_log_return
    x["cost_1x"]=x.weight*4*x.asset.map(PIP)/x.p1
    return x

def summarize(x, mult):
    e=x.assign(net=x.gross-mult*x.cost_1x).groupby("event_id",as_index=False).agg(net=("net","sum"),gross=("gross","sum"),cost=("cost_1x","sum"),trades=("asset","count"))
    draws=np.random.default_rng(SEED).choice(e.net.to_numpy(),size=(10000,len(e)),replace=True).mean(axis=1)
    return {"events":int(len(e)),"round_trips":int(len(x)),"trade_legs":int(2*len(x)),"net_return":float(np.expm1(e.net.sum())),"mean_event_log_return":float(e.net.mean()),"positive_events":int((e.net>0).sum()),"bootstrap_p_mean_positive":float((draws>0).mean()),"bootstrap_ci95":[float(np.quantile(draws,.025)),float(np.quantile(draws,.975))],"event_table":e}

def run(panel,events,vix,out):
    prices=load_panel(panel); ev=load_events(events); rows=build_rows(prices,ev,vix); out.mkdir(parents=True,exist_ok=True)
    rows.to_csv(out/"research041_rows.csv",index=False)
    summaries={}
    for kind, equal_weight in (("price_only",False),("price_only_equal_weight",True),("expanding_ridge",False)):
        base_kind="expanding_ridge" if kind=="expanding_ridge" else "price_only"
        x=strategy(rows,base_kind,equal_weight=equal_weight); costs=[]
        for m in (0.,1.,2.,4.):
            s=summarize(x,m); s["event_table"].to_csv(out/f"research041_{kind}_events_{int(m)}x.csv",index=False); del s["event_table"]; s["cost_multiplier"]=m; costs.append(s)
        pd.DataFrame(costs).to_csv(out/f"research041_{kind}_costs.csv",index=False); summaries[kind]=costs
    one=[]
    base=strategy(rows,"price_only",equal_weight=False)
    for fam in sorted(set(FAMILY.values())):
        z=base[base.asset.map(FAMILY)!=fam]
        e=z.assign(net=z.gross-z.cost_1x).groupby("event_id").net.sum()
        one.append({"omitted_family":fam,"assets_remaining":int(z.asset.nunique()),"net_return_1x":float(np.expm1(e.sum())),"positive_events":int((e>0).sum())})
    pd.DataFrame(one).to_csv(out/"research041_price_only_family_leave_one_out.csv",index=False)
    summary={"panel_sha256":sha256(panel),"events_sha256":sha256(events),"vix_sha256":sha256(vix),"panel_assets":15,"valid_rows":len(rows),"models":summaries,"decision":"research_only_exploratory","note":"2024 panel already used; no untouched holdout"}
    (out/"research041_summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True))
    return summary

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--panel",type=Path,required=True); p.add_argument("--events",type=Path,required=True); p.add_argument("--vix",type=Path,required=True); p.add_argument("--output-dir",type=Path,required=True); a=p.parse_args(); print(json.dumps(run(a.panel,a.events,a.vix,a.output_dir),indent=2,default=str))

