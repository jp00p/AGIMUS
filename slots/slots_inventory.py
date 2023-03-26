from common import *


class SlotsInventory:
    def __init__(self, player):
        self.symbols = []

    def add_symbol(self, symbol):
        pass  # insert into user_slots_inventory

    def remove_symbol(self, symbol):
        pass  # delete from user_slots_inventory

    def load_inventory(self):
        with AgimusDB(dictionary=True) as query:
            sql = "SELECT * FROM user_slots_inventories WHERE user_id = %s"
            # vals = player.discord_id
            query.execute(sql)
            results = query.fetchall()
