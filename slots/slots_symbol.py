from common import *
import json
from typing import List

SYMBOLS_GRAPHICS_DIR = "graphics/symbols/"


class SlotsSymbol:
    """a symbol that can show up on the slot_machine or in the shop!"""

    def __init__(self, id=None, **kwargs):
        self.id: int = id
        self.owner: int = kwargs.get("owner", None)
        self.name: str = kwargs.get("name", None)
        self.rarity: int = kwargs.get("rarity", None)
        self.description: str = kwargs.get("description", None)
        self.tags: List[str] = kwargs.get("tags", [])
        self.payout = kwargs.get("payout", 1)

    def __str__(self):
        return self.name

    def apply_effect(self, spin_results, row, col):
        """this gets overloaded in symbol_types"""
        pass

    def save(self, player):
        logger.info(f"Attempting to save symbol {self.name}...")
        self.owner = player
        data = json.dumps(self.__dict__)
        with AgimusDB() as query:
            sql = "INSERT INTO slots__user_inventory (id, user_id, symbol_name, symbol_data) VALUES(%(id)s, %(user_id)s, %(symbol_name)s, %(symbol_data)s)  ON DUPLICATE KEY UPDATE user_id=%(user_id)s, symbol_name=%(symbol_name)s, symbol_data=%(symbol_data)s"
            vals = {
                "id": self.id,
                "user_id": self.owner,
                "symbol_name": self.name,
                "symbol_type": type(self).__name__,
                "symbol_data": data,
            }
            query.execute(sql, vals)

    def check_tag_match(self, tag, against):
        """check if a symbol has the given tag"""
        return tag in against.tags


def load_symbol(id):
    with AgimusDB(dictionary=True) as query:
        sql = "SELECT symbol_data FROM slots__user_inventory WHERE id = %s LIMIT 1"
        vals = (id,)
        query.execute(sql, vals)
        results = query.fetchone()
    logger.info(results)
    return json.loads(results["symbol_data"])
