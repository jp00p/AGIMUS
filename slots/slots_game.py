from .slot_machine import SlotMachine
from .slots_symbol import *
from .symbol_types import *

TEST_SYMBOL = SlotsSymbol(id=None, name="Test Symbol")


class SlotsGame:
    """an instance of a game someone is playing, this is the part that interfaces with discord"""

    def __init__(self, user_discord_id):
        self.user_discord_id = user_discord_id
        # self.slot_machine: SlotMachine = slot_machine
        self.player = self.lookup_player() or self.register_player()

    def lookup_player(self):
        logger.info(f"Looking up user {self.user_discord_id}...")
        with AgimusDB(dictionary=True) as query:
            sql = "SELECT slots__user_data.id FROM slots__user_data LEFT JOIN users ON users.discord_id = %s"
            vals = (self.user_discord_id,)
            query.execute(sql, vals)
            result = query.fetchone()
        return result

    def register_player(self):
        logger.info(f"Registering player {self.user_discord_id}...")
        with AgimusDB() as query:
            sql = "INSERT INTO slots__user_data (user_discord_id, latinum) VALUES (%s, %s)"
            vals = (self.user_discord_id, 0)
            query.execute(sql, vals)
        logger.info(f"Player ID {query.lastrowid}")
        self.give_symbol(query.lastrowid, TEST_SYMBOL)
        return query.lastrowid

    def give_symbol(self, player, symbol: SlotsSymbol):
        symbol.save(player=player)

    def remove_symbol(self, player, symbol):
        sql = "DELETE FROM slots__user_inventory WHERE id = %s"

    def play(self, bet):
        # self.player_money -= bet
        spin_results = self.slot_machine.spin()
        self.slot_machine.display_slots()
        self.slot_machine.apply_effects()
        self.slot_machine.display_slots()
        # payout = self.slot_machine.calculate_payout()
        # print(f"Payout: {payout}")


# def main():

#     symbols = [
#         SlotsSymbol("CUM"),
#         SlotsSymbol("ANT"),
#         SlotsSymbol("CAT"),
#         DestroySymbol("XXX"),
#         ConvertSymbol("OOO"),
#     ]

#     slot_machine = SlotMachine(symbols, 5, 5)

#     game = SlotsGame(100, slot_machine)

#     bet = 5

#     game.play(bet)


# if __name__ == "__main__":
#     main()
