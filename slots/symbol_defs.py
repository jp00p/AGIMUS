from .slots_symbol import *

basic_symbols = [
    SlotsSymbol(
        name="Janeway",
        effect_where="adjacent",
        effect_which="coffee",
        effect_name="alter_payout",
        effect_args={"new_payout": 2},
    ),
    SlotsSymbol(
        name="Picard",
        effect_where="adjacent",
        effect_which="combadge",
        effect_name="alter_payout",
        effect_args={"new_payout": 1},
    ),
    SlotsSymbol(
        name="Riker",
        effect_where="adjacent",
        effect_which="pants",
        effect_name="destroy",
    ),
    SlotsSymbol(name="Kirk"),
    SlotsSymbol(name="Coffee"),
    SlotsSymbol(name="Burnham"),
    SlotsSymbol(name="Pike"),
    SlotsSymbol(name="Sisko"),
    SlotsSymbol(name="Kevin"),
    SlotsSymbol(name="Combadge"),
    SlotsSymbol(name="Fedora"),
    SlotsSymbol(name="Pants"),
    SlotsSymbol(name="Baseball Glove"),
]


all_symbols = basic_symbols
