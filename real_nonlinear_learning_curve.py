"""Research 033: locked learning-curve audit of Research 031 predictions."""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from real_histdata_2024_confirmation import stationary_indices

SAMPLES=1000; BLOCK=10; SEED=33046

def decision_table(path='real_nonlinear_fx_2024_2025_audit.csv'):
    x=pd.read_csv(path,parse_dates=['decision']).sort_values(['decision','currency'])
    rows=[]
    for date,g in x.groupby('decision',sort=True):
        winner=g.loc[g.prediction.idxmax(),'realized_five_session_return']
        loser=g.loc[g.prediction.idxmin(),'realized_five_session_return']
        rows.append({'decision':date,'train_rows':int(g.train_rows.iloc[0]),
                     'rank_correlation':spearmanr(g.prediction,g.realized_five_session_return).statistic,
                     'winner_minus_loser':winner-loser})
    d=pd.DataFrame(rows).sort_values('decision').reset_index(drop=True)
    d['quartile']=pd.qcut(np.arange(len(d)),4,labels=[1,2,3,4])
    d['rolling20_rank']=d.rank_correlation.rolling(20).median()
    d['rolling20_spread']=d.winner_minus_loser.rolling(20).mean()
    return d

def evaluate():
    d=decision_table()
    q=(d.groupby('quartile',observed=True).agg(decisions=('decision','size'),train_rows_min=('train_rows','min'),train_rows_max=('train_rows','max'),median_rank=('rank_correlation','median'),mean_spread=('winner_minus_loser','mean')).reset_index())
    cut=len(d)//2; first=d.winner_minus_loser.iloc[:cut].to_numpy(); second=d.winner_minus_loser.iloc[-cut:].to_numpy()
    i1=stationary_indices(cut,SAMPLES,BLOCK,SEED); i2=stationary_indices(cut,SAMPLES,BLOCK,SEED+1)
    improvement=second[i2].mean(1)-first[i1].mean(1)
    final=q.iloc[-1]
    summary=pd.DataFrame([{'first_half_mean_spread':first.mean(),'second_half_mean_spread':second.mean(),'second_minus_first':second.mean()-first.mean(),'bootstrap_probability_improvement':float((improvement>0).mean()),'final_quartile_median_rank':final.median_rank,'final_quartile_mean_spread':final.mean_spread,'hypothesis_supported':bool(final.median_rank>0 and final.mean_spread>0 and second.mean()>first.mean() and (improvement>0).mean()>=.9),'bootstrap_samples':SAMPLES}])
    return summary,q,d

if __name__=='__main__':
    for name,frame in zip(['summary','quartiles','rolling'],evaluate()):
        frame.to_csv(f'real_nonlinear_learning_curve_{name}.csv',index=False); print(name,frame.to_string(index=False))
