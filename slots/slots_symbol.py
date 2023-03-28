from common import *
import json
from typing import List

SYMBOLS_GRAPHICS_DIR = "graphics/symbols/"


class SlotsSymbol:
    """a symbol that can show up on the slot_machine or in the shop!"""

    def __init__(self, id=None, **kwargs):
        self.id: int = id
        self.owner: dict = kwargs.get("player", None)
        self.name: str = kwargs.get("name", None)
        self.rarity: int = kwargs.get("rarity", None)
        self.description: str = kwargs.get("description", None)
        self.tags: List[str] = kwargs.get("tags", [])
        self.payout = kwargs.get("payout", 1)
        self.metadata: dict = None
        self.status = None  # keep track of what happened here

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)

    def __str__(self):
        return self.name

    def apply_effect(self, spin_results, row, col):
        """this gets overloaded in symbol_types"""
        pass

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
                "payout": self.payout,
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


""" these are symbols that do special things! """


class EmptySymbol(SlotsSymbol):
    def __init__(self, **kwargs):
        self.name = "Empty"


class DestructionSymbol(SlotsSymbol):
    """destroys symbols around it"""

    def apply_effect(self, spin_results, row, col):
        for i in range(row - 1, row + 2):
            for j in range(col - 1, col + 2):
                if (
                    i >= 0
                    and i < len(spin_results)
                    and j >= 0
                    and j < len(spin_results[0])
                ):
                    spin_results[i][j] = EmptySymbol()


class ConversionSymbol(SlotsSymbol):
    """converts symbols around it"""

    def __init__(self, convert_to: SlotsSymbol = None, **kwargs):
        self.convert_to = convert_to
        super().__init__(**kwargs)

    def apply_effect(self, spin_results, row, col):
        for i in range(row - 1, row + 2):
            for j in range(col - 1, col + 2):
                if (
                    i >= 0
                    and i < len(spin_results)
                    and j >= 0
                    and j < len(spin_results[0])
                ):
                    spin_results[i][j] = self.convert_to
