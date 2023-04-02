import random
from typing import List
from .slots_symbol import *
from .slots_game import *
from . import symbol_defs as ALL_SYMBOLS
from wand.image import Image, COMPOSITE_OPERATORS

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
        self._symbols: List[SlotsSymbol] = STARTING_SYMBOLS.copy()
        self._spins: int = 0
        self._spin_results = self.init_spin_results()
        self.last_result: str = ""
        self.payout: int = 0
        self.effects_applied = False
        self.startup()

    def startup(self):
        """initialize a new machine or load an existing machine"""
        if self.new_game:
            self._symbols = STARTING_SYMBOLS.copy()
            self._spins = 0
            self.last_result = ""
            logger.info(f"Starting new slot machine: {self.game_id} {self._symbols}")
        else:
            logger.info(f"Loading existing gamedata: GAME ID {self.game_id}")
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
        logger.info(f"Updating symbols to {val}")
        with AgimusDB() as query:
            sql = "UPDATE slots__games SET symbols = %s WHERE id = %s"
            vals = (
                json.dumps([s.__dict__ for s in self._symbols]),
                self.game_id,
            )
            query.execute(sql, vals)

    @property
    def spin_results(self):
        return self._spin_results

    @spin_results.setter
    def spin_results(self, val):
        self._spin_results = val
        logger.info("Updating last_result in DB")
        with AgimusDB() as query:
            sql = "UPDATE slots__games SET last_result = %s WHERE id = %s"
            vals = (
                self.display_slots(),
                self.game_id,
            )
            query.execute(sql, vals)

    def render_results(self):
        suffix = "before"
        image_base = None
        transition_images = []

        if self.effects_applied:
            suffix = "after"
        flat_list = []

        for col in range(self.num_cols):
            for row in range(self.num_rows):
                flat_list.append(self.spin_results[col][row])

        filename = f"images/slots_2.0/{self.user_discord_id}_{suffix}_results.png"

        with Image() as final_result_img:
            for src in [s.to_img() for s in flat_list]:
                with Image(width=100, height=100, filename=src) as item:
                    final_result_img.image_add(item)

            final_result_img.background_color = "black"
            final_result_img.alpha_channel = True
            final_result_img.montage(tile="5x5")
            final_result_img.border("white", 2, 2)
            final_result_img.save(filename=filename)
            i = 0
            if self.effects_applied:
                base_file = (
                    f"images/slots_2.0/{self.user_discord_id}_before_results.png"
                )
                image_base = Image(filename=base_file)
                image_base.alpha_channel = True

                with final_result_img.clone() as animation_final_frame:
                    animation_final_frame.alpha_channel = True
                    for alpha in [
                        1.0,
                        0.9,
                        0.8,
                        0.7,
                        0.6,
                        0.5,
                        0.4,
                        0.3,
                        0.2,
                        0.1,
                        0.0,
                    ]:
                        base = image_base.clone()
                        frame = animation_final_frame.clone()

                        frame.evaluate(
                            operator="set",
                            value=frame.quantum_range * alpha,
                            channel="alpha",
                        )
                        base.composite(frame, 0, 0)
                        base.delay = 8
                        if alpha == 0.0:
                            base.delay = 10000
                        base.loop = 0
                        animation_final_frame.sequence.append(base)

                    animation_final_frame.type = "optimize"
                    animation_final_frame.save(
                        filename=f"images/slots_2.0/{self.user_discord_id}_slot_anim.gif"
                    )

    def init_spin_results(self):
        """create empty 2d array"""
        return [
            [EmptySymbol() for j in range(self.num_cols)] for i in range(self.num_rows)
        ]

    def fill_empty_slots(self):
        """fill any empty slots with EmptySymbols"""
        symbols_to_fill = self.num_rows * self.num_cols - len(self._symbols)
        logger.info(f"Filling {symbols_to_fill} empty symbol slots")
        self._symbols.extend([EmptySymbol() for _ in (range(symbols_to_fill))])

    def spin(self):
        self.effects_applied = False
        logger.info(f"Spinnin the slots!")
        self.spins = self.spins + 1
        self.fill_empty_slots()  # pad out the slots with empties
        temp_results = self.init_spin_results()
        random.shuffle(self._symbols)

        for i in range(self.num_rows):
            for j in range(self.num_cols):
                symbol = self._symbols.pop()  # add a symbol to each slot!
                temp_results[i][j] = symbol
        self.spin_results = temp_results
        return self.spin_results

    def get_symbol_position(self, symbol):
        for x in range(self.num_cols):
            for y in range(self.num_rows):
                if self.spin_results[x][y] == symbol:
                    return (x, y)
        return None

    def display_slots(self):

        display_str = ""
        # logger.info(f"Results: {self.spin_results}")
        results = [
            [f"{symbol}" if symbol is not None else "" for symbol in row]
            for row in self.spin_results
        ]
        for row in results:
            display_str += "".join(row) + "\n"
        return display_str

    def apply_effects(self):
        """apply this symbol's effect to other symbols"""
        logger.info(f"Applying effects to current spin")
        self.render_results()  # render a "before" image
        temp_results = self.spin_results
        for i in range(self.num_rows):
            for j in range(self.num_cols):
                symbol = temp_results[i][j]  # the symbol we're affecting
                temp_results = symbol.apply_effect(self.spin_results, i, j)
        self.spin_results = temp_results  # send to db
        self.effects_applied = True
        self.collect_final_symbols()
        random.shuffle(self._spin_results)
        self.render_results()  # render an "after" image

    def collect_final_symbols(self):
        """add/remove symbols from your collection after all effects applied"""
        new_symbols = []
        for row in self.spin_results:
            for symbol in row:
                if not isinstance(symbol, EmptySymbol):
                    new_symbols.append(symbol)
        for symbol in self.symbols:
            if not isinstance(symbol, EmptySymbol):
                new_symbols.append(symbol)
        logger.info(f"NEW SYMBOLS: {new_symbols}")
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
