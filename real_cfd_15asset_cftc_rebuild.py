"""Research 036: 15-asset Ridge+VIX+CFTC rebuild with turnover costs."""
from __future__ import annotations
import zipfile
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
H,LOOKBACK,TOP_BOTTOM,ALPHA,START=5,20,3,10.,60
FX={"EURUSD","GBPUSD","AUDUSD","NZDUSD","USDJPY","USDCHF","USDCAD","EURJPY"}
TFF={"EURUSD":"099741","GBPUSD":"096742","AUDUSD":"232741","NZDUSD":"112741","USDJPY":"097741","USDCAD":"090741","USDCHF":"092741"}
def _pressure(path,mapping,long_col,short_col):
    with zipfile.ZipFile(path) as zf: raw=pd.read_csv(zf.open(zf.namelist()[0]),low_memory=False)
    raw["Report_Date_as_YYYY-MM-DD"]=pd.to_datetime(raw["Report_Date_as_YYYY-MM-DD"]); raw["code"]=raw["CFTC_Contract_Market_Code"].astype(str).str.strip().str.zfill(6)
    result={}
    for asset,code in mapping.items():
        x=raw.loc[raw.code.eq(code),["Report_Date_as_YYYY-MM-DD","Open_Interest_All",long_col,short_col]].copy()
        x["net_oi"]=(pd.to_numeric(x[long_col],errors="coerce")-pd.to_numeric(x[short_col],errors="coerce"))/pd.to_numeric(x["Open_Interest_All"],errors="coerce"); x=x.sort_values("Report_Date_as_YYYY-MM-DD")
        z=(x.net_oi-x.net_oi.expanding(min_periods=8).mean())/x.net_oi.expanding(min_periods=8).std().replace(0,np.nan)
        result[asset]=pd.Series(z.to_numpy(),index=x["Report_Date_as_YYYY-MM-DD"]+pd.Timedelta(days=3))
    return result
def cot_features(index,assets):
    signals=_pressure("cftc_tff_2024.zip",TFF,"Lev_Money_Positions_Long_All","Lev_Money_Positions_Short_All")
    signals.update(_pressure("cftc_disagg_2024.zip",{"XAUUSD":"088691"},"M_Money_Positions_Long_All","M_Money_Positions_Short_All"))
    out=pd.DataFrame(0.,index=index,columns=assets)
    for asset,s in signals.items(): out[asset]=s.reindex(index,method="ffill").fillna(0.)
    out[[a for a in ("USDJPY","USDCHF","USDCAD") if a in out]]*=-1
    return out
def fees(prices):
    base={a:(.00044 if a in FX else .0015 if a in {"XAUUSD","SPXUSD","NSXUSD","GRXEUR","UKXGBP"} else .0025) for a in prices}
    return pd.DataFrame({a:base[a]/prices[a] for a in prices},index=prices.index)
def metrics(x):
    x=x.dropna(); e=np.exp(x.cumsum())
    return {"observations":len(x),"net_return":e.iloc[-1]-1,"annualized_mean":x.mean()*252,"sharpe":np.sqrt(252)*x.mean()/x.std() if x.std() else np.nan,"max_drawdown":(e/e.cummax()-1).min()}
def run():
    prices=pd.read_csv("cfd_daily_prices_15_2024.csv",parse_dates=["ts"]).set_index("ts").ffill().dropna()
    vix=pd.read_csv("vixcls.csv",parse_dates=["observation_date"]).set_index("observation_date").iloc[:,0].reindex(prices.index).ffill()
    assets,returns,cot=list(prices),np.log(prices).diff(),cot_features(prices.index,list(prices)); weights=pd.DataFrame(0.,index=prices.index,columns=assets); decisions=[]
    for i in range(START,len(prices)-H,H):
        X=[];y=[]
        for j in range(LOOKBACK,i-H,H):
            mom,vol=np.log(prices.iloc[j]/prices.iloc[j-LOOKBACK]),returns.iloc[j-LOOKBACK:j].std(); breadth,vx,dvx=returns.iloc[j-5:j].mean().mean(),float(vix.iloc[j]),float(vix.iloc[j]-vix.iloc[j-5])
            for a in assets: X.append([mom[a],vol[a],mom[a]/vol[a] if vol[a] else 0.,breadth,vx,dvx,mom[a]*dvx,cot.iloc[j][a]]);y.append(np.log(prices.iloc[j+H][a]/prices.iloc[j][a]))
        X,y=np.asarray(X),np.asarray(y);mean,sd=X.mean(0),X.std(0);sd[sd==0]=1;reg=Ridge(alpha=ALPHA).fit((X-mean)/sd,y)
        mom,vol=np.log(prices.iloc[i]/prices.iloc[i-LOOKBACK]),returns.iloc[i-LOOKBACK:i].std();breadth,vx,dvx=returns.iloc[i-5:i].mean().mean(),float(vix.iloc[i]),float(vix.iloc[i]-vix.iloc[i-5]);pred={}
        for a in assets:
            z=np.array([mom[a],vol[a],mom[a]/vol[a] if vol[a] else 0.,breadth,vx,dvx,mom[a]*dvx,cot.iloc[i][a]]);pred[a]=reg.predict(((z-mean)/sd).reshape(1,-1))[0]
        order=sorted(pred,key=pred.get);w=pd.Series(0.,index=assets);w[order[:TOP_BOTTOM]]=-1/(2*TOP_BOTTOM);w[order[-TOP_BOTTOM:]]=1/(2*TOP_BOTTOM);weights.iloc[i+1:min(i+1+H,len(prices))]=w.to_numpy();decisions.append({"decision":prices.index[i],"lowest":order[0],"highest":order[-1],"cftc_nonzero_features":int(cot.iloc[i].ne(0).sum())})
    gross=(weights*returns).sum(axis=1);valid=weights.abs().sum(axis=1).gt(0);turnover=weights.diff().abs();turnover.iloc[0]=weights.iloc[0].abs();cost=(turnover*fees(prices)).sum(axis=1);last=weights.index[valid][-1];cost.loc[last]+=(weights.loc[last].abs()*fees(prices).loc[last]).sum();net=(gross-cost)[valid]
    daily=pd.DataFrame({"gross_log_return":gross[valid],"net_log_return":net,"turnover_cost_log":cost[valid],"gross_turnover":turnover[valid].sum(axis=1)})
    summary=pd.DataFrame([{"model":"ridge_vix_cftc_rebuilt",**metrics(net),"charged_cost_log":float(cost[valid].sum()),"annual_turnover":float(turnover[valid].sum().sum()/(len(net)/252)),"cftc_nonzero_assets":int(cot.ne(0).any().sum()),"decisions":len(decisions)}])
    return summary,daily,pd.DataFrame(decisions),vix.reindex(daily.index)
def robustness(daily,vix):
    rows=[{"check":f"cost_{m:g}x",**metrics(daily.gross_log_return-m*daily.turnover_cost_log)} for m in (0.,1.,2.,4.)]
    rng=np.random.default_rng(36036);x=daily.net_log_return.to_numpy();draws=x[rng.integers(0,len(x),(5000,len(x)))].mean(1)*252;rows.append({"check":"iid_bootstrap_5000","mean_positive_probability":float((draws>0).mean()),"annualized_mean_ci_low":float(np.quantile(draws,.025)),"annualized_mean_ci_high":float(np.quantile(draws,.975))});q=vix.quantile(.75)
    regime=pd.DataFrame([{"regime":"low_or_equal_vix_q75","days":int((vix<=q).sum()),**metrics(daily.loc[vix<=q,"net_log_return"])},{"regime":"high_vix","days":int((vix>q).sum()),**metrics(daily.loc[vix>q,"net_log_return"])}]);parts=np.array_split(daily.index,4);phases=pd.DataFrame([{"phase":n+1,"start":p[0],"end":p[-1],**metrics(daily.loc[p,"net_log_return"])} for n,p in enumerate(parts)])
    return pd.DataFrame(rows),regime,phases
if __name__=="__main__":
    s,d,a,v=run();r,g,p=robustness(d,v);s.to_csv("real_cfd_15asset_cftc_rebuild_results.csv",index=False);d.to_csv("real_cfd_15asset_cftc_rebuild_daily.csv");a.to_csv("real_cfd_15asset_cftc_rebuild_decisions.csv",index=False);r.to_csv("real_cfd_15asset_cftc_rebuild_robustness.csv",index=False);g.to_csv("real_cfd_15asset_cftc_rebuild_regimes.csv",index=False);p.to_csv("real_cfd_15asset_cftc_rebuild_phases.csv",index=False)
