from common import *
import json
from enum import Enum, auto
from typing import List, TypeVar

SYMBOLS_GRAPHICS_DIR = "graphics/symbols/"
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

    def __init__(self, id=None, **kwargs):
        self.id: int = id
        self.owner: dict = kwargs.get("player", None)
        self.name: str = kwargs.get("name", None)
        self.rarity: int = RARITY[kwargs.get("rarity", "COMMON")]
        self.description: str = kwargs.get("description", None)
        self.tags: List[str] = kwargs.get("tags", [])
        self.base_payout: int = kwargs.get("payout", 1)
        self.payout = self.base_payout
        self.effect_name = "conversion"  # what effect does this do to other symbols
        self.effect_where = "any|adjacent"
        self.metadata: dict = None
        self.status = None  # keep track of what happened here

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)

    def __str__(self):
        return self.name

    def apply_effect(
        self, spin_results: List[List[Symbol]], row, col
    ) -> List[List[Symbol]]:
        """
        accepts the entire spin result grid, and this symbol's current x,y in that grid
        loops over the grid and applies this symbol's effect to the appropriate symbols
        returns the entire spin result grid
        """
        for i in range(row - 1, row + 2):
            for j in range(col - 1, col + 2):
                if self.check_surrounding(i, j, spin_results):
                    spin_results[i][j] = spin_results[i][j].effect(
                        self.effect_name, self.convert_to
                    )
        return spin_results

    def effect(self, **args: any) -> Symbol:
        """this is run on a symbol being affected by this symbol (does NOT run on the symbol applying effects)"""
        if getattr(self, "effect_" + self.effect_name):
            getattr(self, "effect_" + self.effect_name)(**args)

    def effect_conversion(self, convert_to) -> Symbol:
        return convert_to

    def effect_destroy(self):
        return EmptySymbol()

    def effect_alter_payout(self, new_payout):
        self.payout = new_payout

    def check_surrounding(self, inc1, inc2, results):
        """checks the 8 tiles around a given symbol, excludes self"""
        return (
            inc1 >= 0
            and inc1 < len(results)
            and inc2 >= 0
            and inc2 < len(results[0])
            and results[inc1][inc2] != self
        )

    def save(self, player):
        logger.info(f"Attempting to save symbol {self.name}...")
        self.owner = player
        tags = json.dumps(self.tags)
        metadata = json.dumps(self.metadata)
        with AgimusDB() as query:
            sql = """
              INSERT INTO slots__user_inventory (id, user_id, name, type, rarity, payout, tags, description, metadata) 
              VALUES (%(id)s, %(user_id)s, %(name)s, %(type)s, %(rarity)s, %(payout)s, %(tags)s, %(description)s, %(metadata)s) 
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
    classname = symbol_db_info.get("type", "SlotsSymbol")
    the_class = globals()[classname]
    instance = the_class(name=symbol_db_info.get("name", "NONAME"))
    logger.info(f"Creating... {instance}")
    return instance


def load_from_json(json_str) -> List[SlotsSymbol]:
    final_list = []
    logger.info(json_str)
    for s in json_str:
        if s:
            final_list.append(create_symbol(json.loads(s)))
    return final_list


def load_symbol(id) -> SlotsSymbol:
    """load a specific symbol from the db"""
    with AgimusDB(dictionary=True) as query:
        sql = "SELECT * FROM slots__user_inventory WHERE id = %s LIMIT 1;"
        vals = (id,)
        query.execute(sql, vals)
        results = query.fetchone()
    logger.info(results)
    return create_symbol(results)


def load_symbols(user_id) -> List[SlotsSymbol]:
    """load all of a users' symbols from the db"""
    with AgimusDB(dictionary=True) as query:
        sql = "SELECT * FROM slots__user_inventory WHERE user_id = %s;"
        vals = (user_id,)
        query.execute(sql, vals)
        results = query.fetchall()
    logger.info(results)
    symbols = []
    for s in results:
        symbols.append(create_symbol(s))
    return symbols


""" these are symbol types that do special things! """


class EmptySymbol(SlotsSymbol):
    def __init__(self, **kwargs):
        super().__init__(name="⬛", **kwargs)

    def apply_effect(
        self, spin_results: List[List[Symbol]], row, col
    ) -> List[List[Symbol]]:
        """empty symbol does nothing!"""
        pass


class DestructionSymbol(SlotsSymbol):
    """destroys symbols around it"""

    def apply_effect(self, spin_results, row, col):
        for i in range(row - 1, row + 2):
            for j in range(col - 1, col + 2):
                if self.check_surrounding(i, j, spin_results):
                    spin_results[i][j] = EmptySymbol()


class ConversionSymbol(SlotsSymbol):
    """converts symbols around it"""

    def __init__(self, convert_to: SlotsSymbol = None, **kwargs):
        self.convert_to = convert_to
        super().__init__(**kwargs)

    def apply_effect(self, spin_results: List[List[SlotsSymbol]], row, col):
        for i in range(row - 1, row + 2):
            for j in range(col - 1, col + 2):
                if self.check_surrounding(i, j, spin_results):
                    spin_results[i][j] = spin_results[i][j].effect(
                        self.effect_name, self.convert_to
                    )


class ModifyPayoutSymbol(SlotsSymbol):
    def __init__(self, amt: int = 1, **kwargs):
        self.amt = amt
        super().__init__(**kwargs)

    def apply_effect(self, spin_results, row, col):
        for i in range(row - 1, row + 2):
            for j in range(col - 1, col + 2):
                if self.check_surrounding(i, j, spin_results):
                    spin_results[i][j].payout = spin_results[i][j].payout + self.amt


class MatchTagSymbol(SlotsSymbol):
    def __init__(
        self, match_anywhere=False, match_adjacent=False, tags_to_match=[], **kwargs
    ):
        self.match_anywhere = match_anywhere
        self.match_adjacent = match_adjacent
        self.tags_to_match = tags_to_match
        super().__init__(**kwargs)

    def apply_effect(self, spin_results, row, col):
        pass
