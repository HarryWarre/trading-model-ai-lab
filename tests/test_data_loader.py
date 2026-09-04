import pandas as pd
from data_loader import validate_bars


def test_valid_bars():
    df = pd.DataFrame({
        'symbol': ['A', 'A'],
        'timestamp_utc': pd.to_datetime(['2020-01-01', '2020-01-02'], utc=True),
        'open': [10, 11], 'high': [12, 13], 'low': [9, 10], 'close': [11, 12],
        'bid': [10.9, 11.9], 'ask': [11.1, 12.1],
    })
    assert validate_bars(df) == []


def test_invalid_bars_are_flagged():
    df = pd.DataFrame({
        'symbol': ['A', 'A'],
        'timestamp_utc': pd.to_datetime(['2020-01-02', '2020-01-01'], utc=True),
        'open': [10, 11], 'high': [9, 13], 'low': [9, 10], 'close': [11, 12],
        'bid': [12, 11], 'ask': [11, 10],
    })
    errors = validate_bars(df)
    assert 'timestamps are not globally sorted' in errors
    assert 'high below open/close' in errors
    assert 'bid above ask' in errors


if __name__ == '__main__':
    test_valid_bars()
    test_invalid_bars_are_flagged()
    print('Data loader tests passed')
