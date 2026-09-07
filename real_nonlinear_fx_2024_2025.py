"""Research 031: preregistered nonlinear multi-input currency forecast."""
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
import real_multifactor_fx_2024_2025 as linear
from real_histdata_2024_confirmation import stationary_indices

TREES=50; DEPTH=2; LEARNING_RATE=.05; SEED=31044

def run_model(o,rates,f,offset=0,currencies=linear.CURRENCIES,cost_multiplier=1.0):
    y=linear.target(o,rates); p=linear.base.currency_prices(o)
    out=pd.Series(0.,index=o.index); audit=[]
    for pos in range(linear.FORM+offset,len(o)-linear.H,linear.H):
        rows=[]; ys=[]
        for i in np.arange(linear.FORM,pos-linear.H,linear.H):
            for c in currencies:
                vals=f.loc[f.index[i],[(c,z) for z in linear.FEATURES]]
                if pd.notna(y.iloc[i][c]) and vals.notna().all(): rows.append((i,c)); ys.append(y.iloc[i][c])
        if len(rows)<linear.MIN_TRAIN: continue
        X=np.array([f.loc[f.index[i],[(c,z) for z in linear.FEATURES]].to_numpy(float) for i,c in rows])
        model=GradientBoostingRegressor(n_estimators=TREES,max_depth=DEPTH,learning_rate=LEARNING_RATE,random_state=SEED,loss='squared_error').fit(X,ys)
        pred=[]
        for c in currencies:
            z=f.loc[f.index[pos],[(c,q) for q in linear.FEATURES]].to_numpy(float).reshape(1,-1)
            pred.append((c,model.predict(z)[0]))
        pred=sorted(pred,key=lambda z:(z[1],z[0])); w={c:0. for c in linear.CURRENCIES}; w[pred[0][0]]=-.5; w[pred[-1][0]]=.5
        end=min(pos+1+linear.H,len(o)-1)
        for j in range(pos+1,end):
            gross=sum(w[c]*(np.log(p.iloc[j+1][c]/p.iloc[j][c])+rates.iloc[j][c]*(o.index[j+1]-o.index[j]).total_seconds()/86400/365) for c in currencies)
            fee=sum(linear.trade_fee(c,w[c],o.iloc[j]) for c in currencies)*cost_multiplier
            out.iloc[j]=gross-fee if j==pos+1 or j==end-1 else gross
        for c,prediction in pred:
            audit.append({'decision':o.index[pos],'currency':c,'prediction':prediction,
                          'realized_five_session_return':y.iloc[pos][c],
                          'winner':pred[-1][0],'loser':pred[0][0],
                          'train_rows':len(rows)})
    return out[out!=0],pd.DataFrame(audit)

def bootstrap_prob(x,seed):
    idx=stationary_indices(len(x),1000,10,seed)
    return float((x.to_numpy()[idx].mean(1)>0).mean())

def main():
    o,r,f=linear.data(); net,audit=run_model(o,r,f)
    rows=[{'model':'nonlinear_full',**linear.metrics(net),'bootstrap_probability_positive':bootstrap_prob(net,SEED),'bootstrap_samples':1000,'decisions':audit.decision.nunique()}]
    annual=pd.DataFrame([{'year':int(y),**linear.metrics(s)} for y,s in net.groupby(net.index.year)])
    pd.DataFrame(rows).to_csv('real_nonlinear_fx_2024_2025_results.csv',index=False)
    annual.to_csv('real_nonlinear_fx_2024_2025_annual.csv',index=False); audit.to_csv('real_nonlinear_fx_2024_2025_audit.csv',index=False)
    net.rename('net_log_return').to_csv('real_nonlinear_fx_2024_2025_returns.csv')
    print(pd.DataFrame(rows).to_string(index=False)); print(annual.to_string(index=False))
if __name__=='__main__': main()
