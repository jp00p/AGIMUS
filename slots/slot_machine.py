import random
from copy import deepcopy
from enum import Enum
from multiprocessing import Pool
from typing import List
from .slots_symbol import *
from .slots_game import *
from . import symbol_defs as ALL_SYMBOLS
from .rendering import *


STARTING_SYMBOLS = ALL_SYMBOLS.basic_symbols

Machine = TypeVar("Machine", bound="SlotMachine")


class SlotMachine:
    """the actual slot machine handles spinning, displaying, applying effects etc..."""

    def __init__(
        self,
        game_id: int,
        num_rows=5,
        num_cols=5,
        new_game: bool = False,
        user_id: int = None,
        starting_symbols=[],
    ):
        self.new_game = new_game
        self.game_id = game_id
        self.user_discord_id = user_id
        self.num_rows: int = num_rows
        self.num_cols: int = num_cols
        self._spins: int = 0
        self._spin_results = self.init_spin_results()
        self.before_results = None
        self.last_result: str = ""
        self._payout: int = 0
        self._total_winnings: int = 0
        self.effects_applied = False
        self.before_image = None
        self.after_image = None
        self.starting_symbols = starting_symbols
        self._symbols: List[SlotsSymbol] = self.starting_symbols
        self.startup()

    def startup(self) -> None:
        """initialize a new machine or load an existing machine"""
        if self.new_game:
            self._symbols = self.starting_symbols
            self._spins = 0
            self.last_result = ""
            logger.info(
                f"NEW GAME STARTING SYMBOLS: {[str(s) for s in self.starting_symbols]}"
            )
        else:
            self._symbols = []
            logger.info(
                f"EXISTING GAME STARTING SYMBOLS: {[str(s) for s in self._symbols]}"
            )
            with AgimusDB(dictionary=True) as query:
                sql = "SELECT * FROM slots__games WHERE id = %s"
                vals = (self.game_id,)
                query.execute(sql, vals)
                game_db_data: dict = query.fetchone()
            self.game_id = game_db_data["id"]
            self._total_winnings = game_db_data["total_winnings"]
            if game_db_data.get("symbols", False):
                json_data = json.loads(game_db_data["symbols"])
                for s in json_data:
                    self._symbols.append(create_symbol(s))
            if game_db_data.get("last_result", False):
                self.last_result = game_db_data["last_result"]
            self._spins = game_db_data["spins"]

    @property
    def spins(self) -> int:
        return self._spins

    @spins.setter
    def spins(self, val) -> None:
        self._spins = val
        with AgimusDB() as query:
            sql = "UPDATE slots__games SET spins = spins + 1 WHERE id = %s"
            vals = (self.game_id,)
            query.execute(sql, vals)

    @property
    def symbols(self) -> List[SlotsSymbol]:
        return self._symbols

    @symbols.setter
    def symbols(self, val) -> None:
        self._symbols = val
        with AgimusDB() as query:
            sql = "UPDATE slots__games SET symbols = %s WHERE id = %s"
            vals = (
                json.dumps([s.__dict__ for s in val]),
                self.game_id,
            )
            query.execute(sql, vals)

    @property
    def spin_results(self) -> List[List[SlotsSymbol]]:
        return self._spin_results

    @property
    def payout(self) -> int:
        return self._payout

    @property
    def total_winnings(self) -> int:
        return self._total_winnings

    @payout.setter
    def payout(self, val) -> None:
        self._payout = val
        self.total_winnings = self.total_winnings + val

    @spin_results.setter
    def spin_results(self, val) -> None:
        self._spin_results = val
        with AgimusDB() as query:
            sql = "UPDATE slots__games SET last_result = %s WHERE id = %s"
            vals = (
                self.display_slots(),
                self.game_id,
            )
            query.execute(sql, vals)

    @total_winnings.setter
    def total_winnings(self, val) -> None:
        self._total_winnings = val
        with AgimusDB() as query:
            sql = "UPDATE slots__games SET total_winnings = %s WHERE id = %s"
            vals = (self._total_winnings, self.game_id)
            query.execute(sql, vals)

    def flatten_results(self, results) -> List[SlotsSymbol]:
        flat = []
        for row in range(self.num_rows):
            for col in range(self.num_cols):
                flat.append(results[row][col])
        return flat

    async def render_results(self) -> Machine:
        """render the slot machine GIF

        returns self for chaining
        """
        before_images = self.flatten_results(deepcopy(self.before_results))
        after_images = self.flatten_results(deepcopy(self._spin_results))

        await generate_transition_gif(
            [s.grid_info() for s in before_images],
            [s.grid_info() for s in after_images],
            intermediate=[s.grid_info(wiggle=True) for s in after_images],
            output_file=f"images/slots_2.0/{self.user_discord_id}_slot_anim.gif",
        )
        return self

    def init_spin_results(self) -> List[List[EmptySymbol]]:
        """create a grid of 25 empty symbols"""
        return [
            [EmptySymbol() for j in range(self.num_cols)] for i in range(self.num_rows)
        ]

    def fill_empty_slots(self) -> None:
        """fill any empty slots with EmptySymbols"""
        symbols_to_fill = self.num_rows * self.num_cols - len(self._symbols)
        self._symbols.extend([EmptySymbol() for _ in (range(symbols_to_fill))])

    def spin(self) -> Machine:
        """
        spin the slot machine!

        returns self for chaining
        """

        self.effects_applied = False
        self.spins = self.spins + 1
        self.fill_empty_slots()  # pad out the slots with empties
        temp_results = self.init_spin_results()
        random.shuffle(self._symbols)

        for i in range(self.num_rows):
            for j in range(self.num_cols):
                symbol: SlotsSymbol = self._symbols.pop()  # add a symbol to each slot!
                symbol.added_to_result()
                temp_results[i][j] = symbol
        self.before_results = deepcopy(
            temp_results
        )  # keep track of the initial results before we do stuff to it!
        self.spin_results = deepcopy(temp_results)

        return self

    def get_symbol_position(self, symbol) -> tuple:
        for x in range(self.num_cols):
            for y in range(self.num_rows):
                if self.spin_results[x][y] == symbol:
                    return (x, y)
        return None

    def display_slots(self) -> str:
        """display a string of the slots result"""
        display_str = ""
        results = [
            [f"{symbol}" if symbol is not None else "" for symbol in row]
            for row in self.spin_results
        ]
        for row in results:
            display_str += "".join(row) + "\n"
        return display_str

    def reset_status(self):
        """reset symbols to their natural state"""
        temp_symbols = self.symbols
        for s in temp_symbols:
            s.set_status()
            s.wiggly = False
            s.payout = s.base_payout
        self.symbols = temp_symbols

    def apply_effects(self) -> Machine:
        """apply this symbol's effect to other symbols"""
        temp_results = deepcopy(self.spin_results)
        for i in range(self.num_rows):
            for j in range(self.num_cols):
                symbol = temp_results[i][j]  # the symbol doing the effect
                temp_results = symbol.apply_effect(temp_results, i, j)
        self.spin_results = temp_results  # send to db
        self.effects_applied = True
        return self

    def collect_final_symbols(self) -> Machine:
        """add/remove symbols from your collection after all effects applied"""
        new_symbols = []
        final_symbols = self.flatten_results(self.spin_results)
        for s in final_symbols:
            if s and not isinstance(s, EmptySymbol):
                new_symbols.append(s)
        new_symbols += self._symbols
        self.symbols = new_symbols  # send to db
        return self

    def check_column(self, column) -> bool:
        symbols = [
            self.spin_results[column][y] for y in range(len(self.spin_results[0]))
        ]
        return all(symbol.name == symbols[0].name for symbol in symbols)

    def check_row(self, row) -> bool:
        symbols = [self.spin_results[x][row] for x in range(len(self.spin_results))]
        return all(symbol.name == symbols[0].name for symbol in symbols)

    def check_diagonal(self, x_start, y_start, x_step, y_step) -> bool:
        symbols: List[SlotsSymbol] = []
        x, y = x_start, y_start
        while 0 <= x < len(self.spin_results) and 0 <= y < len(self.spin_results[0]):
            symbols.append(self.spin_results[x][y])
            x += x_step
            y += y_step
        return all(symbol.name == symbols[0].name for symbol in symbols)

    def check_diagonals(self) -> bool:
        # Check the two main diagonals
        diagonal1 = self.check_diagonal(0, 0, 1, 1)
        diagonal2 = self.check_diagonal(len(self.spin_results) - 1, 0, -1, 1)
        return diagonal1 or diagonal2

    def calculate_payout(self) -> Machine:
        payouts = []
        # combine all payouts and add to players total
        for s in self.flatten_results(self.spin_results):
            payouts.append(s.payout)
        self.payout = sum(payouts)
        self.reset_status()
        return self
