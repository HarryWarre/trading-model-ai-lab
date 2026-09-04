"""Point-in-time market data loader and validation for Research 001."""
import pandas as pd


REQUIRED = {'symbol', 'timestamp_utc', 'open', 'high', 'low', 'close'}


def load_bars_csv(path):
    df = pd.read_csv(path)
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f'missing required columns: {sorted(missing)}')
    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'], utc=True)
    return df.sort_values(['symbol', 'timestamp_utc']).reset_index(drop=True)


def validate_bars(df):
    errors = []
    if df.empty:
        errors.append('empty dataset')
        return errors
    if df[['symbol', 'timestamp_utc']].duplicated().any():
        errors.append('duplicate symbol/timestamp keys')
    if not df['timestamp_utc'].is_monotonic_increasing:
        errors.append('timestamps are not globally sorted')
    if (df[['open', 'high', 'low', 'close']] <= 0).any().any():
        errors.append('non-positive OHLC value')
    if (df['high'] < df[['open', 'close']].max(axis=1)).any():
        errors.append('high below open/close')
    if (df['low'] > df[['open', 'close']].min(axis=1)).any():
        errors.append('low above open/close')
    if {'bid', 'ask'} <= set(df.columns):
        if (df['bid'] > df['ask']).any():
            errors.append('bid above ask')
        if (df['ask'] <= 0).any():
            errors.append('non-positive ask')
    return errors
