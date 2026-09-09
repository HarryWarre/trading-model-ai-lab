"""Research 034 checkpoint: fail-closed coverage audit for 16 CFD proxies."""
from pathlib import Path
from hashlib import sha256
import pandas as pd

UNIVERSE={
 'EURUSD':['DAT_ASCII_EURUSD_M1_2024.csv','DAT_ASCII_EURUSD_M1_2025.csv'],
 'GBPUSD':['DAT_ASCII_GBPUSD_M1_2024.csv','DAT_ASCII_GBPUSD_M1_2025.csv'],
 'AUDUSD':['DAT_ASCII_AUDUSD_M1_2024.csv','DAT_ASCII_AUDUSD_M1_2025.csv'],
 'NZDUSD':['DAT_ASCII_NZDUSD_M1_2024.csv','DAT_ASCII_NZDUSD_M1_2025.csv'],
 'USDJPY':['DAT_ASCII_USDJPY_M1_2024.csv','DAT_ASCII_USDJPY_M1_2025.csv'],
 'USDCHF':['DAT_ASCII_USDCHF_M1_2024.csv','DAT_ASCII_USDCHF_M1_2025.csv'],
 'USDCAD':['DAT_ASCII_USDCAD_M1_2024.csv','DAT_ASCII_USDCAD_M1_2025.csv'],
 'EURJPY':['DAT_ASCII_EURJPY_M1_2024.csv','DAT_ASCII_EURJPY_M1_2025.csv'],
 'XAUUSD':['DAT_ASCII_XAUUSD_M1_2024.csv'], 'XAGUSD':['DAT_ASCII_XAGUSD_M1_2024.csv'],
 'SPXUSD':['DAT_ASCII_SPXUSD_M1_2024.csv'], 'NAS100USD':['DAT_ASCII_NAS100USD_M1_2024.csv'],
 'GER40':['DAT_ASCII_GER40_M1_2024.csv'], 'UK100':['DAT_ASCII_UK100_M1_2024.csv'],
 'WTIUSD':['DAT_ASCII_WTIUSD_M1_2024.csv'], 'BRENTUSD':['DAT_ASCII_BRENTUSD_M1_2024.csv']}

def audit():
 rows=[]
 for asset,paths in UNIVERSE.items():
  existing=[]; valid=[]; errors=[]
  for name in paths:
   p=Path(name)
   if not p.exists(): continue
   existing.append(name)
   try:
    if p.stat().st_size<100: raise ValueError('file too small')
    sample=pd.read_csv(p,sep=';',header=None,nrows=3)
    if sample.shape[1]<5: raise ValueError('unexpected column count')
    valid.append(name)
   except Exception as e: errors.append(f'{name}: {e}')
  rows.append({'asset':asset,'requested_files':len(paths),'existing_files':len(existing),'valid_files':len(valid),'status':'available' if valid else 'blocked','files':'|'.join(valid),'sha256':'|'.join(sha256(Path(x).read_bytes()).hexdigest() for x in valid),'errors':'|'.join(errors)})
 return pd.DataFrame(rows)

if __name__=='__main__':
 out=audit(); out.to_csv('real_cfd_universe_coverage.csv',index=False); print(out.to_string(index=False)); print('available',int((out.status=='available').sum()),'of',len(out))
