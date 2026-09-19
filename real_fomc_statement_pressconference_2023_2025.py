"""Research 047: statement-to-press-conference return forecast, preregistered in issue #64."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
from real_fomc_crossfamily_jumps import ASSETS, FAMILIES, load_data, sha256

PIP = {a: (0.01 if a in {"USDJPY","EURJPY"} else 0.0001) for a in ASSETS}
PIP.update({"XAUUSD":0.01,"XAGUSD":0.001,"SPXUSD":0.1,"NSXUSD":0.1})
FEATURES = ["statement_z","family_loo_z","global_family_z","log_prevol","vix","statement_vix"]
ALPHA, WARMUP, DRAWS, SEED = 10.0, 8, 10000, 20260919

def load_vix(path: Path) -> pd.DataFrame:
    x=pd.read_csv(path)
    if {"observation_date","VIXCLS"}-set(x): raise ValueError("VIX schema")
    x["observation_date"]=pd.to_datetime(x.observation_date,utc=True,errors="raise")
    x["VIXCLS"]=pd.to_numeric(x.VIXCLS,errors="coerce")
    x=x.dropna().sort_values("observation_date")
    if x.observation_date.duplicated().any(): raise ValueError("duplicate VIX date")
    return x

def prior_vix(vix: pd.DataFrame,t: pd.Timestamp)->float:
    z=vix.loc[vix.observation_date<t.normalize(),"VIXCLS"]
    if z.empty: raise ValueError("no lagged VIX")
    return float(z.iloc[-1])

def exact(prices:pd.DataFrame,asset:str,t:pd.Timestamp)->float:
    if t not in prices.index: raise ValueError("timestamp absent")
    x=prices.at[t,asset]
    if not np.isfinite(x) or x<=0: raise ValueError("quote absent")
    return float(x)

def prevol(prices:pd.DataFrame,asset:str,t:pd.Timestamp)->float:
    z=prices.loc[(prices.index>=t-pd.Timedelta(days=20))&(prices.index<t),asset].dropna()
    r=np.log(z).diff().dropna()
    r=r.loc[r.index.to_series().diff()<=pd.Timedelta(minutes=10)]
    if len(r)<500: raise ValueError("insufficient prevol")
    v=float(r.std(ddof=1))
    if not np.isfinite(v) or v<=0: raise ValueError("invalid prevol")
    return v

def rows(prices:pd.DataFrame,events:pd.DataFrame,vix:pd.DataFrame)->tuple[pd.DataFrame,pd.DataFrame]:
    family={a:f for f,m in FAMILIES.items() for a in m}
    out=[]; coverage=[]
    for e in events.itertuples(index=False):
        t=e.release_timestamp_utc; tmp=[]
        for a in ASSETS:
            try:
                p0=exact(prices,a,t-pd.Timedelta(minutes=10))
                p1=exact(prices,a,t+pd.Timedelta(minutes=20))
                p2=exact(prices,a,t+pd.Timedelta(minutes=90))
                vol=prevol(prices,a,t); vv=prior_vix(vix,t)
            except ValueError: continue
            tmp.append({"event_id":e.event_id,"release_timestamp_utc":t,"year":t.year,
                        "asset":a,"family":family[a],"statement_return":float(np.log(p1/p0)),
                        "press_return":float(np.log(p2/p1)),"entry_price":p1,
                        "prevol":vol,"vix":vv,"cost_1x":4*PIP[a]/p1})
        fams=len(set(x["family"] for x in tmp)); eligible=len(tmp)>=8 and fams==3
        coverage.append({"event_id":e.event_id,"year":t.year,"assets":len(tmp),"families":fams,"eligible":eligible})
        if eligible: out.extend(tmp)
    x=pd.DataFrame(out); cov=pd.DataFrame(coverage)
    if cov.eligible.sum()<WARMUP+10: raise ValueError("fewer than 18 eligible events")
    x["statement_z"]=x.statement_return/x.prevol
    fammean=x.groupby(["event_id","family"]).statement_z.transform("sum")
    famn=x.groupby(["event_id","family"]).statement_z.transform("count")
    x["family_loo_z"]=(fammean-x.statement_z)/(famn-1)
    family_event=x.groupby(["event_id","family"]).statement_z.mean().groupby("event_id").mean()
    x["global_family_z"]=x.event_id.map(family_event)
    x["log_prevol"]=np.log(x.prevol)
    x["statement_vix"]=x.statement_z*x.vix
    x["target_z"]=x.press_return/x.prevol
    if not np.isfinite(x[FEATURES+["target_z"]].to_numpy()).all(): raise ValueError("invalid features")
    return x,cov

def ridge_fit(train:pd.DataFrame):
    mu=train[FEATURES].mean(); sd=train[FEATURES].std(ddof=0).replace(0,1)
    X=((train[FEATURES]-mu)/sd).to_numpy(); X=np.c_[np.ones(len(X)),X]
    y=train.target_z.to_numpy(); penalty=np.eye(X.shape[1])*ALPHA; penalty[0,0]=0
    beta=np.linalg.solve(X.T@X+penalty,X.T@y)
    residual=y-X@beta
    return mu,sd,beta,float(np.median(np.abs(residual)))

def model_signals(x:pd.DataFrame,eligible_order:list[str])->pd.Series:
    signal=pd.Series(0.0,index=x.index)
    for pos,event_id in enumerate(eligible_order):
        if pos<WARMUP: continue
        test=x[x.event_id==event_id]; cutoff=test.release_timestamp_utc.iloc[0]
        train=x[x.release_timestamp_utc<cutoff]
        if train.event_id.nunique()<WARMUP: raise ValueError("walk-forward warmup leak")
        mu,sd,beta,mad=ridge_fit(train)
        X=((test[FEATURES]-mu)/sd).to_numpy(); pred=np.c_[np.ones(len(X)),X]@beta
        raw=pred*test.prevol.to_numpy()
        threshold=test.cost_1x.to_numpy()+0.5*mad*test.prevol.to_numpy()
        signal.loc[test.index]=np.where(np.abs(raw)>threshold,np.sign(raw),0)
    return signal

def strategy_rows(x:pd.DataFrame,kind:str,eligible_order:list[str])->pd.DataFrame:
    z=x[x.event_id.isin(eligible_order[WARMUP:])].copy()
    if kind=="continuation": z["signal"]=np.sign(z.statement_return)
    elif kind=="reversal": z["signal"]=-np.sign(z.statement_return)
    elif kind=="long": z["signal"]=1.0
    elif kind=="ridge": z["signal"]=model_signals(x,eligible_order).reindex(z.index)
    else: raise ValueError(kind)
    z=z[z.signal!=0].copy()
    z["invvol"]=1/z.prevol
    z["weight"]=z.groupby("event_id").invvol.transform(lambda q:q/q.sum())
    z["gross"]=z.weight*z.signal*z.press_return
    z["cost"]=z.weight*z.cost_1x
    return z

def event_returns(z:pd.DataFrame,mult:float,all_events:list[str])->pd.DataFrame:
    e=z.assign(net=z.gross-mult*z.cost).groupby("event_id",as_index=False).agg(
        gross=("gross","sum"),cost_1x=("cost","sum"),net=("net","sum"),
        round_trips=("asset","count"))
    return pd.DataFrame({"event_id":all_events}).merge(e,on="event_id",how="left").fillna(0)

def block_probability(values:np.ndarray)->tuple[float,list[float]]:
    n=len(values); rng=np.random.default_rng(SEED)
    starts=rng.integers(n,size=(DRAWS,int(np.ceil(n/2))))
    idx=np.stack([starts,(starts+1)%n],axis=-1).reshape(DRAWS,-1)[:,:n]
    means=values[idx].mean(axis=1)
    return float((means>0).mean()),[float(x) for x in np.quantile(means,[.025,.975])]

def summarize(e:pd.DataFrame)->dict:
    p,ci=block_probability(e.net.to_numpy())
    return {"events":len(e),"round_trips":int(e.round_trips.sum()),"trade_legs":int(2*e.round_trips.sum()),
            "net_return":float(np.expm1(e.net.sum())),"gross_return":float(np.expm1(e.gross.sum())),
            "positive_events":int((e.net>0).sum()),"block_p_mean_positive":p,"block_ci95_mean_log":ci}

def run(panel:Path,manifest:Path,events_file:Path,vix_file:Path,out:Path)->dict:
    prices,events,_=load_data(panel,manifest,events_file); vix=load_vix(vix_file)
    x,cov=rows(prices,events,vix); order=cov.loc[cov.eligible,"event_id"].tolist()
    evaluation=order[WARMUP:]; out.mkdir(parents=True,exist_ok=True)
    cov.to_csv(out/"research047_coverage.csv",index=False)
    x.to_csv(out/"research047_rows.csv",index=False)
    models={}; event_tables={}
    for kind in ("continuation","reversal","long","ridge"):
        z=strategy_rows(x,kind,order); z.to_csv(out/f"research047_{kind}_trades.csv",index=False)
        costs=[]
        for mult in (0,1,2,4):
            e=event_returns(z,mult,evaluation); e.to_csv(out/f"research047_{kind}_events_{mult}x.csv",index=False)
            costs.append({"cost_multiplier":mult,**summarize(e)})
            if mult==1: event_tables[kind]=e
        models[kind]=costs
    baseline=max(("continuation","reversal","long"),key=lambda k:event_tables[k].net.mean())
    paired=event_tables["ridge"].net.to_numpy()-event_tables[baseline].net.to_numpy()
    paired_p,paired_ci=block_probability(paired)
    rz=strategy_rows(x,"ridge",order)
    loo=[]; families=sorted(FAMILIES)
    for f in families:
        q=rz[rz.family!=f].copy()
        q["weight"]=q.groupby("event_id").invvol.transform(lambda v:v/v.sum())
        q["gross"]=q.weight*q.signal*q.press_return; q["cost"]=q.weight*q.cost_1x
        e=event_returns(q,1,evaluation)
        loo.append({"excluded_family":f,"net_return":float(np.expm1(e.net.sum()))})
    pd.DataFrame(loo).to_csv(out/"research047_ridge_family_leave_one_out.csv",index=False)
    asset_loo=[]
    for asset in ASSETS:
        q=rz[rz.asset!=asset].copy()
        q["weight"]=q.groupby("event_id").invvol.transform(lambda v:v/v.sum())
        q["gross"]=q.weight*q.signal*q.press_return; q["cost"]=q.weight*q.cost_1x
        e=event_returns(q,1,evaluation)
        asset_loo.append({"excluded_asset":asset,"net_return":float(np.expm1(e.net.sum()))})
    pd.DataFrame(asset_loo).to_csv(out/"research047_ridge_asset_leave_one_out.csv",index=False)
    attribution=rz.assign(net=lambda d:d.gross-d.cost).groupby(
        ["family","asset"],as_index=False).agg(round_trips=("asset","size"),
                                               gross_log=("gross","sum"),cost_log=("cost","sum"),
                                               net_log=("net","sum"))
    attribution.to_csv(out/"research047_ridge_asset_attribution.csv",index=False)
    primary=event_tables["ridge"].merge(x[["event_id","year","vix"]].drop_duplicates("event_id"),on="event_id")
    primary["phase"]=np.where(np.arange(len(primary))<len(primary)/2,"first","second")
    warm_vix=x[x.event_id.isin(order[:WARMUP])].drop_duplicates("event_id").vix.median()
    primary["vix_regime"]=np.where(primary.vix>warm_vix,"high","low")
    year=primary.groupby("year",as_index=False).net.sum(); phase=primary.groupby("phase",as_index=False).net.sum()
    regime=primary.groupby("vix_regime",as_index=False).net.sum()
    year.to_csv(out/"research047_ridge_years.csv",index=False); phase.to_csv(out/"research047_ridge_phases.csv",index=False)
    regime.to_csv(out/"research047_ridge_vix_regimes.csv",index=False)
    m1=next(v for v in models["ridge"] if v["cost_multiplier"]==1)
    m2=next(v for v in models["ridge"] if v["cost_multiplier"]==2)
    baseline_1={k:next(v for v in models[k] if v["cost_multiplier"]==1)["net_return"] for k in ("continuation","reversal","long")}
    gates={"net_1x_positive":m1["net_return"]>0,
           "beats_all_baselines_1x":m1["net_return"]>max(baseline_1.values()),
           "paired_block_p_at_least_95pct":paired_p>=.95,
           "both_evaluation_years_positive":len(year)==2 and bool((year.net>0).all()),
           "all_family_loo_positive":bool((pd.DataFrame(loo).net_return>0).all()),
           "net_2x_positive":m2["net_return"]>0,
           "at_least_10_events":len(evaluation)>=10}
    result={"panel_sha256":sha256(panel),"manifest_sha256":sha256(manifest),
            "events_sha256":sha256(events_file),"vix_sha256":sha256(vix_file),
            "eligible_events":len(order),"warmup_events":WARMUP,"evaluation_events":len(evaluation),
            "strongest_baseline_1x":baseline,"models":models,
            "paired_ridge_minus_strongest_baseline_block_p":paired_p,
            "paired_ci95_mean_log":paired_ci,"gates":gates,"passed_all_gates":all(gates.values()),
            "ridge_active_round_trips":int(len(rz)),
            "ridge_possible_asset_events":int(len(x[x.event_id.isin(evaluation)])),
            "ridge_abstention_rate":float(1-len(rz)/len(x[x.event_id.isin(evaluation)])),
            "ridge_direction_hit_rate":float((rz.signal*rz.press_return>0).mean()),
            "ridge_zero_trade_events":int((event_tables["ridge"].round_trips==0).sum()),
            "all_asset_loo_positive":bool((pd.DataFrame(asset_loo).net_return>0).all()),
            "decision":"research_only_failed_inference_and_year_stability_no_untouched_holdout",
            "fixed_roundtrip_cost_pips":4}
    (out/"research047_summary.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for arg in ("panel","manifest","events","vix","output"):
        p.add_argument("--"+arg,type=Path,required=True)
    a=p.parse_args(); print(json.dumps(run(a.panel,a.manifest,a.events,a.vix,a.output),indent=2,sort_keys=True))
