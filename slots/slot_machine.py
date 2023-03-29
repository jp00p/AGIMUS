import random
from typing import List
from .slots_symbol import *
from .slots_game import *

STARTING_SYMBOLS = [
    SlotsSymbol(name="💙", description="whatever"),
    SlotsSymbol(name="💌"),
    SlotsSymbol(name="👽"),
    ConversionSymbol(name="💊", convert_to=SlotsSymbol(name="🟨")),
    DestructionSymbol(name="🎃"),
]


class SlotMachine:
    """the actual slot machine handles spinning, displaying, applying effects etc..."""

    def __init__(self, num_rows=5, num_cols=5, game_id=None, new_game=False):
        self.new_game = new_game
        self.game_id = game_id
        self.num_rows: int = num_rows
        self.num_cols: int = num_cols
        self._symbols: List[SlotsSymbol] = STARTING_SYMBOLS
        self._spins: int = 0
        self.spin_results = self.init_spin_results()
        self.payout: int = 0
        self.startup()
        self.fill_empty_slots()

    def startup(self):
        if self.new_game:
            with AgimusDB() as query:
                sql = "INSERT INTO slots__machines (game_id, symbols) VALUES (%s, %s)"
                vals = (
                    self.game_id,
                    json.dumps([s.to_json() if s else None for s in self._symbols]),
                )
                query.execute(sql, vals)

        else:
            with AgimusDB(dictionary=True) as query:
                sql = "SELECT * FROM slots__machines WHERE game_id = %s LIMIT 1"
                vals = (self.game_id,)
                query.execute(sql, vals)
                machine_db_data = query.fetchone()
                logger.info(f"Machine loaded")
            self._symbols = load_from_json(json.loads(machine_db_data["symbols"]))
            self._spins = machine_db_data["spins"]

    @property
    def spins(self):
        return self._spins

    @spins.setter
    def spins(self, val):
        self._spins = val

    @property
    def symbols(self):
        return self._symbols

    @symbols.setter
    def symbols(self, val):
        self._symbols = val

    def init_spin_results(self):
        return [
            [EmptySymbol() for j in range(self.num_cols)] for i in range(self.num_rows)
        ]

    def fill_empty_slots(self):
        logger.info("Filling empty symbol slots")
        self._symbols.extend(
            [
                EmptySymbol()
                for _ in (range(self.num_rows * self.num_cols - len(self._symbols)))
            ]
        )

    def spin(self):
        logger.info("Spinnin the slots!")
        self.spins = self.spins + 1
        temp_symbols = self._symbols.copy()
        random.shuffle(temp_symbols)
        for i in range(self.num_rows):
            for j in range(self.num_cols):
                symbol = temp_symbols.pop()
                self.spin_results[i][j] = symbol
        return self.spin_results

    def get_symbol_position(self, symbol):
        for x in range(self.num_cols):
            for y in range(self.num_rows):
                if self.spin_results[x][y] == symbol:
                    return (x, y)
        return None

    def display_slots(self):
        display_str = ""
        logger.info(f"Results: {self.spin_results}")
        results = [
            [f"{symbol}" if symbol is not None else "" for symbol in row]
            for row in self.spin_results
        ]
        for row in results:
            display_str += "".join(row) + "\n"
        return display_str

    def apply_effects(self):
        for i in range(self.num_rows):
            for j in range(self.num_cols):
                symbol = self.spin_results[i][j]
                if symbol:
                    self.spin_results = symbol.apply_effect(self.spin_results, i, j)

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
