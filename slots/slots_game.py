from .slot_machine import SlotMachine
from .slots_symbol import *

TEST_SYMBOL = SlotsSymbol(id=None, name="Test Symbol")


class SlotsGame:
    """games can be resumed from previous sessions, which is why this is so dumb!"""

    BASE_DEBTS = [25, 50, 75, 100, 125, 150, 175, 200]

    def __init__(self, user_discord_id):
        self.id: int = None
        self.user_discord_id: int = user_discord_id
        self.player: dict = self.lookup_player() or self.register_player()
        self.level: int = 1
        self.day: int = 1
        self.debt: int = 0
        self.slot_machine: SlotMachine = None
        self.startup()
        logger.info(f"Game started {self.player} - Existing game ID: {self.id}")

    def startup(self):
        """find existing game id if any, load machine if found"""
        logger.info("Slots starting up...")
        with AgimusDB(dictionary=True) as query:
            sql = (
                "SELECT * FROM slots__games WHERE user_id = %s AND finished = 0 LIMIT 1"
            )
            vals = (self.player["id"],)
            query.execute(sql, vals)
            result = query.fetchone()
        if result is not None:
            logger.info("Existing game found, loading")
            self.id = result["id"]
            self.slot_machine = SlotMachine(game_id=self.id)

    def new_game(self, level):
        """start a new game, set all old games to finished"""
        logger.info("Starting a new game")
        self.current_level = level
        queries = [
            {
                "sql": "UPDATE slots__games SET finished = 1 WHERE user_id = %(user_id)s;",
                "vals": {"user_id": self.player["id"]},
            },
            {
                "sql": "INSERT INTO slots__games (user_id, level) VALUES (%(user_id)s, %(level)s);",
                "vals": {"user_id": self.player["id"], "level": self.level},
            },
        ]
        for q in queries:
            with AgimusDB(multi=True) as query:
                sql = q["sql"]
                vals = q["vals"]
                query.execute(sql, vals)
                game_id = query.lastrowid
        logger.info(f"Creating a new game entry in the DB {game_id}")
        self.id = game_id
        self.slot_machine = SlotMachine(new_game=True, game_id=self.id)

    def calc_debt(self):
        return self.day * 25

    def lookup_player(self):
        """lookup player details in DB"""
        logger.info(f"Looking up user {self.user_discord_id}...")
        with AgimusDB(dictionary=True) as query:
            sql = "SELECT slots__user_data.* FROM slots__user_data LEFT JOIN users ON users.discord_id = %s"
            vals = (self.user_discord_id,)
            query.execute(sql, vals)
            result = query.fetchone()
        return result

    def register_player(self):
        """register new player in DB"""
        logger.info(f"Registering player {self.user_discord_id}...")
        with AgimusDB() as query:
            sql = "INSERT INTO slots__user_data (user_discord_id, latinum) VALUES (%s, %s)"
            vals = (self.user_discord_id, 0)
            query.execute(sql, vals)
        return self.lookup_player()

    def give_symbol(self, player, symbol: SlotsSymbol):
        """give a symbol to a player"""
        symbol.save(player=player)

    def remove_symbol(self, player, symbol):
        """remove a symbol from a player"""
        sql = "DELETE FROM slots__user_inventory WHERE id = %s"

    def play(self, bet):
        """start a game"""
        # self.player_money -= bet
        # spin_results = self.slot_machine.spin()
        # self.slot_machine.display_slots()
        # self.slot_machine.apply_effects()
        # self.slot_machine.display_slots()
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
