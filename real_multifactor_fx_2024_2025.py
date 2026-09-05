"""Research 030: preregistered multi-input FX forecast (price, carry, value, VIX)."""
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge
import real_currency_momentum_2024_2025 as base
import real_monthly_rate_lag_audit as lag
import real_reer_value_2025 as reer
import real_carry_crash_risk as crash
from real_histdata_2024_confirmation import stationary_indices

CURRENCIES=base.CURRENCIES; H=5; FORM=21; ALPHA=10.; MIN_TRAIN=100; ANN=252
FEATURES=['momentum','carry','value','stress','momentum_stress','carry_stress','value_stress']

def metrics(x):
    x=pd.Series(x).dropna(); eq=np.exp(x.cumsum()); sd=x.std()
    return {'observations':len(x),'total_return':eq.iloc[-1]-1,'annualized_mean':x.mean()*ANN,
            'sharpe':np.sqrt(ANN)*x.mean()/sd if sd>0 else np.nan,
            'max_drawdown':(eq/eq.cummax()-1).min()}

def data():
    o=base.build_opens(); p=base.currency_prices(o); rates=base.currency_rate_differentials(lag.load_rates(3),o.index)
    _,v=reer.load_reer(); vv=v.reindex(o.index.tz_localize(None),method='ffill').set_axis(o.index)
    vx=crash.align_vix(o.index); stress=(vx.lagged_vix>vx.threshold_75).astype(float)
    f=pd.DataFrame(index=o.index)
    for c in CURRENCIES:
        spot=np.log(p[c]/p[c].shift(FORM)); carry=rates[c]
        f[(c,'momentum')]=spot+carry.rolling(FORM).sum().shift(1)/365*21
        f[(c,'carry')]=carry; f[(c,'value')]=vv[c]; f[(c,'stress')]=stress
        f[(c,'momentum_stress')]=f[(c,'momentum')]*stress
        f[(c,'carry_stress')]=carry*stress; f[(c,'value_stress')]=vv[c]*stress
    return o,rates,f

def target(o,rates):
    p=base.currency_prices(o); days=((o.index.to_series().shift(-1)-o.index.to_series()).dt.total_seconds()/86400)
    y=pd.DataFrame(index=o.index,columns=CURRENCIES,dtype=float)
    for c in CURRENCIES: y[c]=np.log(p[c].shift(-H)/p[c]) + rates[c].rolling(H).sum().shift(-H+1)*days.rolling(H).sum().shift(-H+1)/365
    return y

def run_model(o,rates,f,features=FEATURES,offset=0,currencies=CURRENCIES):
    y=target(o,rates); out=pd.Series(0.,index=o.index); audit=[]
    for pos in range(FORM+offset,len(o)-H,H):
        train_end=pos-H; dates=np.arange(FORM,train_end,H)
        rows=[]; ys=[]
        for i in dates:
            for c in currencies:
                vals=f.loc[f.index[i],[(c,z) for z in features]]
                if i>=FORM and pd.notna(y.iloc[i][c]) and vals.notna().all(): rows.append((i,c)); ys.append(y.iloc[i][c])
        if len(rows)<MIN_TRAIN: continue
        X=np.array([f.loc[f.index[i],[(c,z) for z in features]].to_numpy(float) for i,c in rows]); mu=X.mean(0); sd=X.std(0); sd[sd==0]=1
        X=(X-mu)/sd; dummies=np.eye(len(CURRENCIES))[[CURRENCIES.index(c) for _,c in rows]]
        model=Ridge(alpha=ALPHA).fit(np.c_[X,dummies],ys)
        cur=[]
        for c in currencies:
            z=(f.loc[f.index[pos],[(c,z) for z in features]].to_numpy(float)-mu)/sd
            cur.append((c,model.predict(np.r_[z,np.eye(len(CURRENCIES))[CURRENCIES.index(c)]].reshape(1,-1))[0]))
        cur=sorted(cur,key=lambda z:(z[1],z[0])); w={c:0. for c in CURRENCIES}; w[cur[0][0]]=-.5; w[cur[-1][0]]=.5
        for j in range(pos+1,min(pos+1+H,len(o)-1)):
            gross=sum(w[c]*(np.log(base.currency_prices(o).iloc[j+1][c]/base.currency_prices(o).iloc[j][c])+rates.iloc[j][c]*(o.index[j+1]-o.index[j]).total_seconds()/86400/365) for c in currencies)
            # 4.4 pip synthetic spread on entry and exit, scaled by each leg's price.
            fee=sum(abs(w[c])*4.4*(.01 if c=='JPY' else .0001)/base.currency_prices(o).iloc[j][c] for c in currencies)
            out.iloc[j]=gross-fee if j==pos+1 or j==min(pos+H,len(o)-2) else gross
        audit.append({'decision':o.index[pos],'winner':cur[-1][0],'loser':cur[0][0],'train_rows':len(rows)})
    return out[out!=0],pd.DataFrame(audit)

def baseline(o,rates,f,offset=0):
    s=f.xs('momentum',level=1,axis=1); out=pd.Series(0.,index=o.index); p=base.currency_prices(o)
    for pos in range(FORM+offset,len(o)-H,H):
        z=s.iloc[pos].dropna(); order=z.sort_values();
        if len(order)<2: continue
        w={c:0 for c in CURRENCIES}; w[order.index[0]]=-.5; w[order.index[-1]]=.5
        for j in range(pos+1,min(pos+1+H,len(o)-1)): out.iloc[j]=sum(w[c]*(np.log(p.iloc[j+1][c]/p.iloc[j][c])+rates.iloc[j][c]*(o.index[j+1]-o.index[j]).total_seconds()/86400/365) for c in CURRENCIES)
    return out[out!=0]

def cost_net(gross,o):
    # conservative synthetic 4.4 pip per unit turnover, applied to both legs
    return gross.copy() # cost is applied through fixed 4.4 pip equivalent below

def main():
    o,r,f=data(); results=[]
    for name,fs in [('price_only',['momentum']),('price_carry',['momentum','carry']),('price_carry_value',['momentum','carry','value']),('full',FEATURES)]:
        g,a=run_model(o,r,f,fs); b=base.baseline if False else None
        # 1,000 fixed-seed draws keeps this runnable in the constrained lab worker;
        # the primary point estimate and all time splits remain unchanged.
        idx=stationary_indices(len(g),1000,10,30030)
        results.append({'model':name,**metrics(g),'mean_positive_bootstrap':float((g.to_numpy()[idx].mean(1)>0).mean()),'bootstrap_samples':1000,'decisions':len(a)})
        a.to_csv(f'real_multifactor_fx_2024_2025_{name}_audit.csv',index=False)
    full,_=run_model(o,r,f); price=baseline(o,r,f)
    pd.DataFrame(results).to_csv('real_multifactor_fx_2024_2025_results.csv',index=False)
    n=min(len(full),len(price)); fi=full.iloc[:n].to_numpy(); pi=price.reindex(full.index).fillna(0).iloc[:n].to_numpy(); idx=stationary_indices(n,1000,10,30031)
    pd.DataFrame([{'comparison':'full_minus_price','paired_bootstrap_probability_positive':float(((fi[idx]-pi[idx]).mean(1)>0).mean()),'bootstrap_samples':1000}]).to_csv('real_multifactor_fx_2024_2025_paired.csv',index=False)
    pd.DataFrame([{'data_status':'reused_histdata_2024_2025','sessions':len(o),'features':','.join(FEATURES),'ridge_alpha':ALPHA,'min_train_rows':MIN_TRAIN,'cost_note':'synthetic 4.4 pip; BID-only; no executable capacity'}]).to_csv('real_multifactor_fx_2024_2025_coverage.csv',index=False)
    print(pd.DataFrame(results).to_string(index=False))
if __name__=='__main__': main()
