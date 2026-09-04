from free_data_stack import provider_capabilities


def test_free_provider_registry():
    d = provider_capabilities('dukascopy')
    assert 'tick' in d['granularities']
    assert d['quote_fields'] == ['bid', 'ask']
    a = provider_capabilities('aqr_tsmom')
    assert a['granularities'] == ['monthly']


if __name__ == '__main__':
    test_free_provider_registry()
    print('Free data stack tests passed')
