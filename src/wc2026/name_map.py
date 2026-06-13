"""Full team name → 3-letter code mapping for openfootball worldcup.json."""
from __future__ import annotations

NAME_TO_CODE: dict[str, str] = {
    'Algeria':               'ALG',
    'Argentina':             'ARG',
    'Australia':             'AUS',
    'Austria':               'AUT',
    'Belgium':               'BEL',
    'Bosnia & Herzegovina':  'BIH',
    'Brazil':                'BRA',
    'Canada':                'CAN',
    'Cape Verde':            'CPV',
    'Colombia':              'COL',
    'Croatia':               'CRO',
    'Curaçao':               'CUW',
    'Czech Republic':        'CZE',
    'DR Congo':              'COD',
    'Ecuador':               'ECU',
    'Egypt':                 'EGY',
    'England':               'ENG',
    'France':                'FRA',
    'Germany':               'GER',
    'Ghana':                 'GHA',
    'Haiti':                 'HAI',
    'Iran':                  'IRN',
    'Iraq':                  'IRQ',
    'Ivory Coast':           'CIV',
    'Japan':                 'JPN',
    'Jordan':                'JOR',
    'Mexico':                'MEX',
    'Morocco':               'MAR',
    'Netherlands':           'NED',
    'New Zealand':           'NZL',
    'Norway':                'NOR',
    'Panama':                'PAN',
    'Paraguay':              'PAR',
    'Portugal':              'POR',
    'Qatar':                 'QAT',
    'Saudi Arabia':          'KSA',
    'Scotland':              'SCO',
    'Senegal':               'SEN',
    'South Africa':          'RSA',
    'South Korea':           'KOR',
    'Spain':                 'ESP',
    'Sweden':                'SWE',
    'Switzerland':           'SUI',
    'Tunisia':               'TUN',
    'Turkey':                'TUR',
    'USA':                   'USA',
    'Uruguay':               'URU',
    'Uzbekistan':            'UZB',
}

CODE_TO_NAME: dict[str, str] = {v: k for k, v in NAME_TO_CODE.items()}


def to_code(name: str) -> str:
    """Convert full team name to 3-letter code. Raises ValueError if unknown."""
    if name in NAME_TO_CODE:
        return NAME_TO_CODE[name]
    # Already a code
    if len(name) == 3 and name.isupper():
        return name
    raise ValueError(f"Unknown team name: {name!r}")
