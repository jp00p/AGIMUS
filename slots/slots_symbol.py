from common import *
import json
from enum import Enum, auto
from typing import List, TypeVar

SYMBOLS_GRAPHICS_DIR = "images/slots_2.0/symbols/"

# so we can refer to this object in typing
Symbol = TypeVar("Symbol", bound="SlotsSymbol")


class RARITY(Enum):
    COMMON = auto()
    UNCOMMON = auto()
    RARE = auto()
    SUPER_RARE = auto()


SYMBOL_PROBABILITIES = {
    RARITY.COMMON: 1,
    RARITY.UNCOMMON: 0.7,
    RARITY.RARE: 0.3,
    RARITY.SUPER_RARE: 0.1,
}


class SlotsSymbol(object):
    """a symbol that can show up on the slot_machine or in the shop!"""

    def __init__(self, **kwargs):
        self.id: int = kwargs.get("id", None)
        self.owner: dict = kwargs.get("player", {})
        self.name: str = kwargs.get("name", None)
        # self.rarity: int = RARITY[kwargs.get("rarity", "COMMON")]
        self.description: str = kwargs.get("description", None)
        self.tags: List[str] = kwargs.get("tags", [])
        self.base_payout: int = kwargs.get("payout", 1)
        self.payout = self.base_payout
        self.effect_name: str = kwargs.get("effect_name", "none")
        self.effect_where: str = kwargs.get("effect_where", "none")
        self.effect_which: str = kwargs.get("effect_which", "none")
        self.effect_args: dict = kwargs.get("effect_args", {})
        self.status = None  # keep track of what happened here

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)

    def __str__(self):
        return self.name

    def to_img(self):
        return str(SYMBOLS_GRAPHICS_DIR + self.name.lower().replace(" ", "_") + ".png")

    def apply_effect(
        self, spin_results: List[List[Symbol]], row, col
    ) -> List[List[Symbol]]:

        if self.effect_name == "none" or not self.effect_name:
            return spin_results

        """
        accepts the entire spin result grid, and this symbol's current x,y in that grid
        loops over the grid and applies this symbol's effect to the appropriate symbols
        returns the entire spin result grid
        """
        if self.effect_where == "adjacent":
            for i in range(row - 1, row + 2):
                for j in range(col - 1, col + 2):
                    if self.check_surrounding(i, j, spin_results):
                        # add checks for specific types/etc here
                        if self.effect_which != "none":
                            if spin_results[i][j].name.lower() in self.effect_which:
                                spin_results[i][j] = spin_results[i][j].effect(
                                    self.effect_name, self.effect_args
                                )
                        if self.effect_which in ["any"]:
                            spin_results[i][j] = spin_results[i][j].effect(
                                self.effect_name, self.effect_args
                            )

        if self.effect_where == "any":
            for i in range(5):
                for j in range(5):
                    pass
                    # spin_results[i][j] = spin_results[i][j].effect()
        if self.effect_where == "none":
            pass

        return spin_results

    def effect(self, effect_name, effect_args) -> Symbol:
        """this is run on a symbol being affected by this symbol (does NOT run on the symbol applying effects)"""
        if getattr(self, "effect_" + effect_name):
            return getattr(self, "effect_" + effect_name)(**effect_args)

    # each of these are types of effects to be applied
    # they are only run on the symbol being affected!
    # these should return a SlotsSymbol object of some kind
    def effect_conversion(self, convert_to) -> Symbol:
        return convert_to

    def effect_destroy(self) -> Symbol:
        return EmptySymbol(payout=0)

    def effect_alter_payout(self, new_payout) -> Symbol:
        self.payout += new_payout
        return self

    def effect_none(self) -> Symbol:
        return EmptySymbol()

    #
    #

    def check_surrounding(self, inc1, inc2, results):
        """checks the 8 tiles around a given symbol, excludes self"""
        return (
            inc1 >= 0
            and inc1 < len(results)
            and inc2 >= 0
            and inc2 < len(results[0])
            and results[inc1][inc2] != self
        )
        self.owner = player
        tags = json.dumps(self.tags)
        metadata = json.dumps(self.metadata)
        with AgimusDB() as query:
            sql = """
              INSERT INTO slots__user_inventory (id, user_id, name, type, rarity, payout, tags, description, metadata) 
              VALUES (%(id)s, %(user_id)s, %(name)s, %(type)s, %(rarity)s, %(payout)s, %(tags)s, %(description)s, %(metadata)s, %(effect_name)s, %(effect_where)s, %(effect_args)%) 
              ON DUPLICATE KEY UPDATE user_id=%(user_id)s, name=%(name)s, type=%(type)s, rarity=%(rarity)s, payout=%(payout)s, tags=%(tags)s, description=%(description)s
            """
            vals = {
                "id": self.id,
                "user_id": self.owner["id"],
                "name": self.name,
                "type": self.__class__.__name__,
                "rarity": self.rarity,
                "payout": self.base_payout,
                "tags": tags,
                "description": self.description,
                "metadata": metadata,
                "effect_name": self.effect_name,
                "effect_where": self.effect_where,
                "effect_args": json.dumps(self.effect_args),
            }
            query.execute(sql, vals)
        self.id = query.lastrowid
        return query.lastrowid

    def check_tag_match(self, tag, against):
        """check if a symbol has the given tag"""
        return tag in against.tags


# UTILITIES
def create_symbol(symbol_db_info: dict) -> SlotsSymbol:
    """create symbol from text data"""
    if isinstance(symbol_db_info, str):
        symbol_db_info = json.loads(symbol_db_info)
    classname = symbol_db_info.get("type", "SlotsSymbol")
    the_class = globals()[classname]
    instance = the_class(**symbol_db_info)
    return instance


def load_from_json(json_str) -> List[SlotsSymbol]:
    final_list = []
    for s in json_str:
        if s:
            final_list.append(create_symbol(json.loads(s)))
    return final_list


""" these are symbol types that do special things! """


class EmptySymbol(SlotsSymbol):
    def __init__(self, **kwargs):
        super().__init__(name="Empty", **kwargs)
