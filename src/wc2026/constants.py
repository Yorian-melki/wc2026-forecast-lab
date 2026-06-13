from collections import OrderedDict

GROUP_ORDER = list('ABCDEFGHIJKL')
BEST_THIRD_SLOT_ORDER = ['1A', '1B', '1D', '1E', '1G', '1I', '1K', '1L']
GROUP_MATCH_TEMPLATE = [
    ('1', '2'),
    ('3', '4'),
    ('1', '3'),
    ('4', '2'),
    ('4', '1'),
    ('2', '3'),
]

SLOT_FAMILIES = OrderedDict([
    ('1A', set('CEFHI')),
    ('1B', set('EFGIJ')),
    ('1D', set('BEFIJ')),
    ('1E', set('ABCDF')),
    ('1G', set('AEHIJ')),
    ('1I', set('CDFGH')),
    ('1K', set('DEIJL')),
    ('1L', set('EHIJK')),
])

R32_MATCHES = OrderedDict([
    ('M73', ('2A', '2B')),
    ('M74', ('1E', '3@1E')),
    ('M75', ('1F', '2C')),
    ('M76', ('1C', '2F')),
    ('M77', ('1I', '3@1I')),
    ('M78', ('2E', '2I')),
    ('M79', ('1A', '3@1A')),
    ('M80', ('1L', '3@1L')),
    ('M81', ('1D', '3@1D')),
    ('M82', ('1G', '3@1G')),
    ('M83', ('2K', '2L')),
    ('M84', ('1H', '2J')),
    ('M85', ('1B', '3@1B')),
    ('M86', ('1J', '2H')),
    ('M87', ('1K', '3@1K')),
    ('M88', ('2D', '2G')),
])

R16_MATCHES = OrderedDict([
    ('M89', ('M74', 'M77')),
    ('M90', ('M73', 'M75')),
    ('M91', ('M76', 'M78')),
    ('M92', ('M79', 'M80')),
    ('M93', ('M83', 'M84')),
    ('M94', ('M81', 'M82')),
    ('M95', ('M86', 'M88')),
    ('M96', ('M85', 'M87')),
])

QF_MATCHES = OrderedDict([
    ('M97', ('M89', 'M90')),
    ('M98', ('M93', 'M94')),
    ('M99', ('M91', 'M92')),
    ('M100', ('M95', 'M96')),
])

SF_MATCHES = OrderedDict([
    ('M101', ('M97', 'M98')),
    ('M102', ('M99', 'M100')),
])

FINAL_MATCH = ('M104', ('M101', 'M102'))
THIRD_PLACE_MATCH = ('M103', ('M101_loser', 'M102_loser'))

ROUND_ORDER = ['group', 'r32', 'r16', 'qf', 'sf', 'final', 'champion']
