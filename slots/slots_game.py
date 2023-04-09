""" 
The main entrypoint for the slot machine game
This is what interfaces with Discord initially
A game has a SlotMachine attached which handles almost all the actual gameplay functionality
"""
from common import *
from copy import deepcopy
from .slot_machine import SlotMachine
from .symbol_defs import *
from .slots_symbol import *
from .rendering import *


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
        self._new_symbols: List[SlotsSymbol] = []
        self.startup()
        logger.info(f"Game initialized for {self.player} - Existing games: {self.id}")

    def startup(self):
        """find existing game id if any, load machine if found"""
        with AgimusDB(dictionary=True) as query:
            sql = "SELECT * FROM slots__games WHERE user_discord_id = %s AND finished = 0 LIMIT 1"
            vals = (self.player["user_discord_id"],)
            query.execute(sql, vals)
            result = query.fetchone()
        if result is not None:
            self.id = result["id"]
            new_symbols_json = json.loads(result["new_symbols"])
            if new_symbols_json:
                for s in new_symbols_json:
                    self._new_symbols.append(create_symbol(s))
            self.slot_machine = SlotMachine(
                self.id, new_game=False, user_id=self.player["user_discord_id"]
            )

    def new_game(self, level):
        """start a new game, set all old games to finished"""
        logger.info("Starting a new game!")
        self.slot_machine = None
        self.current_level = level
        self.clear_new_symbols()
        queries = [
            {
                "sql": "UPDATE slots__games SET finished = 1 WHERE user_discord_id = %(user_discord_id)s;",
                "vals": {"user_discord_id": self.player["user_discord_id"]},
            },
            {
                "sql": "INSERT INTO slots__games (user_discord_id, level) VALUES (%(user_discord_id)s, %(level)s);",
                "vals": {
                    "user_discord_id": self.player["user_discord_id"],
                    "level": self.level,
                },
            },
        ]
        for q in queries:
            with AgimusDB(multi=True) as query:
                sql = q["sql"]
                vals = q["vals"]
                logger.info(f"Running query: {sql}")
                query.execute(sql, vals)

        self.id = query.lastrowid
        logger.info(f"Creating a new game entry in the DB #{self.id}")
        self.slot_machine = SlotMachine(
            self.id, new_game=True, user_id=self.player["user_discord_id"]
        )

    def calc_debt(self):
        return self.day * 25

    def get_new_symbols(self):
        """load 3 new symbols for choosing after a spin"""
        if not self.new_symbols:
            temp_symbols = basic_symbols.copy()
            random_choices = random.sample(temp_symbols, k=3)  # TODO: weights
            self.new_symbols = random_choices
            symbol_data = [(s.name, s.payout, (0, 0, 0)) for s in self.new_symbols]
            new_symbol_graphics = numpy_grid(symbol_data, (1, 3))
            new_symbol_graphics.save(
                f"images/slots_2.0/{self.player['user_discord_id']}_new_symbols.png"
            )
        return self.new_symbols

    def clear_new_symbols(self):
        self.new_symbols = []

    @property
    def new_symbols(self):
        return self._new_symbols

    @new_symbols.setter
    def new_symbols(self, val):
        self._new_symbols = val
        symbols_json = json.dumps([s.__dict__ for s in val])
        with AgimusDB() as query:
            sql = "UPDATE slots__games SET new_symbols = %s WHERE id = %s"
            vals = (symbols_json, self.id)
            query.execute(sql, vals)

    def lookup_player(self):
        """lookup player details in DB"""
        logger.info(f"Looking up user {self.user_discord_id}...")
        with AgimusDB(dictionary=True) as query:
            sql = "SELECT * FROM slots__user_data WHERE user_discord_id = %s"
            vals = (self.user_discord_id,)
            query.execute(sql, vals)
            result = query.fetchone()
        return result

    def register_player(self):
        """register new slots player in DB"""
        logger.info(f"Registering player {self.user_discord_id}...")
        with AgimusDB() as query:
            sql = "INSERT INTO slots__user_data (user_discord_id, latinum) VALUES (%s, %s)"
            vals = (self.user_discord_id, 0)
            query.execute(sql, vals)

        return self.lookup_player()
