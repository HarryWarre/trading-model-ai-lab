"""Research data-source registry.

The registry records provenance and limitations; it does not silently merge
feeds or treat broker data as a universal market price.
"""

PROVIDERS = {
    'dukascopy': {
        'asset_classes': ['fx', 'metals', 'indices', 'commodities', 'bonds', 'cfds'],
        'granularities': ['tick', 'minute', 'hour', 'daily', 'monthly'],
        'quote_fields': ['bid', 'ask'],
        'role': 'broker-specific reference and execution calibration',
    },
    'truefx': {
        'asset_classes': ['fx'],
        'granularities': ['tick'],
        'quote_fields': ['bid', 'ask'],
        'role': 'institutional top-of-book FX cross-check',
    },
    'aqr_tsmom': {
        'asset_classes': ['indices', 'fx', 'commodities', 'bonds'],
        'granularities': ['monthly'],
        'quote_fields': [],
        'role': 'academic benchmark factor replication',
    },
    'cftc_cot': {
        'asset_classes': ['futures'],
        'granularities': ['weekly'],
        'quote_fields': [],
        'role': 'positioning and hedging-pressure covariate',
    },
    'fred': {
        'asset_classes': ['rates', 'macro'],
        'granularities': ['daily', 'monthly'],
        'quote_fields': [],
        'role': 'macro and funding control variables',
    },
}


def provider_capabilities(name):
    if name not in PROVIDERS:
        raise KeyError(f'unknown provider: {name}')
    return PROVIDERS[name].copy()
