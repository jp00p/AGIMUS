import random
from typing import List
from .slots_symbol import *
from .slots_game import *

# keep track of spin data in the db too


class SlotMachine:
    """the actual slot machine handles spinning, displaying, applying effects etc..."""

    def __init__(self, symbols, num_rows, num_cols):
        self.symbols: List[SlotsSymbol] = symbols
        self.num_rows: int = num_rows
        self.num_cols: int = num_cols
        self.spin_results: list = [
            [None for j in range(num_cols)] for i in range(num_rows)
        ]
        self.payout: int = 0
        self.symbols.extend([SlotsSymbol("---") for _ in range(num_rows * num_cols)])

    def spin(self):
        random.shuffle(self.symbols)
        for i in range(self.num_rows):
            for j in range(self.num_cols):
                symbol = self.symbols.pop()
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
        results = [[symbol.name for symbol in row] for row in self.spin_results]
        for row in results:
            display_str += str(row) + "\n"
        print(display_str)

    def apply_effects(self):
        for i in range(self.num_rows):
            for j in range(self.num_cols):
                symbol = self.spin_results[i][j]
                if symbol:
                    symbol.apply_effect(self.spin_results, i, j)

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
        for x in range(self.num_cols):
            if self.check_column(x):
                print(f"Column {x} has a winning combination!")
        for y in range(self.num_rows):
            if self.check_row(y):
                print(f"Row {y} has a winning combination!")
        if self.check_diagonals():
            print("A diagonal has a winning combination!")
        return sum(payouts)
