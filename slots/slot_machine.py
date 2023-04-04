import random
from copy import deepcopy
from multiprocessing import Pool
from typing import List
from .slots_symbol import *
from .slots_game import *
from . import symbol_defs as ALL_SYMBOLS
from .rendering import *


STARTING_SYMBOLS = ALL_SYMBOLS.basic_symbols


class SlotMachine:
    """the actual slot machine handles spinning, displaying, applying effects etc..."""

    def __init__(
        self,
        game_id: int,
        num_rows=5,
        num_cols=5,
        new_game: bool = False,
        user_id: int = None,
    ):
        self.new_game = new_game
        self.game_id = game_id
        self.user_discord_id = user_id
        self.num_rows: int = num_rows
        self.num_cols: int = num_cols
        self._symbols: List[SlotsSymbol] = []
        self._spins: int = 0
        self._spin_results = self.init_spin_results()
        self.before_results = None
        self.last_result: str = ""
        self.payout: int = 0
        self.effects_applied = False
        self.before_image = None
        self.after_image = None
        self.startup()

    def startup(self):
        """initialize a new machine or load an existing machine"""
        if self.new_game:
            self._symbols = ALL_SYMBOLS.basic_symbols.copy()
            self._spins = 0
            self.last_result = ""
        else:
            self._symbols = []
            with AgimusDB(dictionary=True) as query:
                sql = "SELECT * FROM slots__games WHERE id = %s"
                vals = (self.game_id,)
                query.execute(sql, vals)
                game_db_data = query.fetchone()
            self.game_id = game_db_data["id"]
            json_data = json.loads(game_db_data["symbols"])
            for s in json_data:
                self._symbols.append(create_symbol(s))
            if game_db_data.get("last_result"):
                self.last_result = game_db_data["last_result"]
            self._spins = game_db_data["spins"]

    @property
    def spins(self):
        return self._spins

    @spins.setter
    def spins(self, val):
        self._spins = val
        with AgimusDB() as query:
            sql = "UPDATE slots__games SET spins = spins + 1 WHERE id = %s"
            vals = (self.game_id,)
            query.execute(sql, vals)

    @property
    def symbols(self):
        return self._symbols

    @symbols.setter
    def symbols(self, val):
        self._symbols = val
        with AgimusDB() as query:
            sql = "UPDATE slots__games SET symbols = %s WHERE id = %s"
            vals = (
                json.dumps([s.__dict__ for s in val]),
                self.game_id,
            )
            query.execute(sql, vals)

    @property
    def spin_results(self):
        return self._spin_results

    @spin_results.setter
    def spin_results(self, val):
        self._spin_results = val
        with AgimusDB() as query:
            sql = "UPDATE slots__games SET last_result = %s WHERE id = %s"
            vals = (
                self.display_slots(),
                self.game_id,
            )
            query.execute(sql, vals)

    def flatten_results(self, results):
        flat = []
        for row in range(self.num_rows):
            for col in range(self.num_cols):
                flat.append(results[row][col])
        return flat

    def render_results(self):

        before_images = self.flatten_results(self.before_results)
        after_images = self.flatten_results(self._spin_results)

        generate_transition_gif(
            [(s.name.lower().replace(" ", "_"), s.payout) for s in before_images],
            [(s.name.lower().replace(" ", "_"), s.payout) for s in after_images],
            output_file=f"images/slots_2.0/{self.user_discord_id}_slot_anim.gif",
        )

    def init_spin_results(self):
        """create empty 2d array"""
        return [
            [EmptySymbol() for j in range(self.num_cols)] for i in range(self.num_rows)
        ]

    def fill_empty_slots(self):
        """fill any empty slots with EmptySymbols"""
        symbols_to_fill = self.num_rows * self.num_cols - len(self._symbols)
        self._symbols.extend([EmptySymbol() for _ in (range(symbols_to_fill))])

    def spin(self):
        self.effects_applied = False
        self.spins = self.spins + 1
        self.fill_empty_slots()  # pad out the slots with empties
        temp_results = self.init_spin_results()
        random.shuffle(self._symbols)

        for i in range(self.num_rows):
            for j in range(self.num_cols):
                symbol = self._symbols.pop()  # add a symbol to each slot!
                temp_results[i][j] = symbol
        self.before_results = deepcopy(temp_results)
        logger.info(self.before_results)
        self.spin_results = temp_results.copy()
        self.apply_effects()

    def get_symbol_position(self, symbol):
        for x in range(self.num_cols):
            for y in range(self.num_rows):
                if self.spin_results[x][y] == symbol:
                    return (x, y)
        return None

    def display_slots(self):

        display_str = ""
        results = [
            [f"{symbol}" if symbol is not None else "" for symbol in row]
            for row in self.spin_results
        ]
        for row in results:
            display_str += "".join(row) + "\n"
        return display_str

    def apply_effects(self):
        """apply this symbol's effect to other symbols"""
        temp_results = self.spin_results.copy()
        for i in range(self.num_rows):
            for j in range(self.num_cols):
                symbol = temp_results[i][j]  # the symbol we're affecting
                temp_results = symbol.apply_effect(temp_results, i, j)
        self.spin_results = temp_results  # send to db
        self.effects_applied = True
        self.collect_final_symbols()
        self.render_results()  # render an "after" image

    def collect_final_symbols(self):
        """add/remove symbols from your collection after all effects applied"""
        new_symbols = []
        final_symbols = self.flatten_results(self.spin_results)
        for s in final_symbols:
            if s and not isinstance(s, EmptySymbol):
                new_symbols.append(s)
        new_symbols += self._symbols
        self.symbols = new_symbols  # send to db

    def check_column(self, column):
        symbols = [
            self.spin_results[column][y] for y in range(len(self.spin_results[0]))
        ]
        return all(symbol.name == symbols[0].name for symbol in symbols)

    def check_row(self, row):
        symbols = [self.spin_results[x][row] for x in range(len(self.spin_results))]
        return all(symbol.name == symbols[0].name for symbol in symbols)

    def check_diagonal(self, x_start, y_start, x_step, y_step):
        symbols: List[SlotsSymbol] = []
        x, y = x_start, y_start
        while 0 <= x < len(self.spin_results) and 0 <= y < len(self.spin_results[0]):
            symbols.append(self.spin_results[x][y])
            x += x_step
            y += y_step
        return all(symbol.name == symbols[0].name for symbol in symbols)

    def check_diagonals(self):
        # Check the two main diagonals
        diagonal1 = self.check_diagonal(0, 0, 1, 1)
        diagonal2 = self.check_diagonal(len(self.spin_results) - 1, 0, -1, 1)
        return diagonal1 or diagonal2

    def calculate_payout(self):
        payouts = []
        # Check columns/rows/diaganols for a winning combination
        # TODO: check tags too
        for x in self.spin_results:
            payouts.append(x.payout)
        return sum(payouts)
