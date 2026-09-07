"""Research 032: locked prediction-skill audit for Research 031."""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from real_histdata_2024_confirmation import stationary_indices

SAMPLES=1000; BLOCK=10; SEED=32045

def evaluate(path='real_nonlinear_fx_2024_2025_audit.csv'):
    x=pd.read_csv(path,parse_dates=['decision']).dropna(subset=['prediction','realized_five_session_return'])
    # Expanding historical mean benchmark, available strictly before each decision.
    x=x.sort_values(['decision','currency']); benchmark=[]
    history=[]
    for date,g in x.groupby('decision',sort=True):
        benchmark.extend([np.mean(history) if history else 0.0]*len(g)); history.extend(g.realized_five_session_return.tolist())
    x['benchmark']=benchmark
    sse=((x.realized_five_session_return-x.prediction)**2).sum(); sst=((x.realized_five_session_return-x.benchmark)**2).sum()
    pooled_r2=1-sse/sst
    decisions=[]
    for date,g in x.groupby('decision'):
        rho=spearmanr(g.prediction,g.realized_five_session_return).statistic
        winner=g.loc[g.prediction.idxmax(),'realized_five_session_return']; loser=g.loc[g.prediction.idxmin(),'realized_five_session_return']
        decisions.append({'decision':date,'rank_correlation':rho,'realized_winner_minus_loser':winner-loser})
    d=pd.DataFrame(decisions).set_index('decision'); vals=d.realized_winner_minus_loser.to_numpy()
    idx=stationary_indices(len(vals),SAMPLES,BLOCK,SEED); means=vals[idx].mean(1)
    annual=[]
    for year,g in d.groupby(d.index.year): annual.append({'year':year,'decisions':len(g),'mean_spread':g.realized_winner_minus_loser.mean(),'median_rank_correlation':g.rank_correlation.median()})
    summary=pd.DataFrame([{'observations':len(x),'decisions':len(d),'pooled_oos_r2':pooled_r2,'median_rank_correlation':d.rank_correlation.median(),'mean_winner_minus_loser':d.realized_winner_minus_loser.mean(),'bootstrap_probability_spread_positive':float((means>0).mean()),'bootstrap_samples':SAMPLES,'both_year_spreads_positive':all(z['mean_spread']>0 for z in annual)}])
    return summary,pd.DataFrame(annual),d.reset_index()

if __name__=='__main__':
    names=['summary','annual','decisions']
    for n,frame in zip(names,evaluate()):
        frame.to_csv(f'real_nonlinear_forecast_audit_{n}.csv',index=False); print(n,frame.to_string(index=False))
