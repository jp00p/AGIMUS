import random
#from common import *
#from handlers.xp import increment_user_xp
from slots_symbol import *

class SlotMachine:
  def __init__(self, symbols, num_rows, num_cols):
      self.symbols = symbols
      self.num_rows = num_rows
      self.num_cols = num_cols
      self.spin_results = [[None for j in range(num_cols)] for i in range(num_rows)]
      self.payout = 0

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
    # for row in results:
    #   for s in row:
    #     display_str += f"{s.name}"
    #   display_str += "\n"
    print(display_str)

  def apply_effects(self):
    for i in range(self.num_rows):
      for j in range(self.num_cols):
        symbol = self.spin_results[i][j]
        if symbol:
          symbol.apply_effect(self.spin_results, i, j)

  def check_column(self, column):
    symbols = [self.spin_results[column][y] for y in range(len(self.spin_results[0]))]
    return all(symbol == symbols[0] for symbol in symbols)

  def check_row(self, row):
      symbols = [self.spin_results[x][row] for x in range(len(self.spin_results))]
      return all(symbol == symbols[0] for symbol in symbols)

  def check_diagonal(self, x_start, y_start, x_step, y_step):
      symbols = []
      x, y = x_start, y_start
      while 0 <= x < len(self.spin_results) and 0 <= y < len(self.spin_results[0]):
        symbols.append(self.spin_results[x][y])
        x += x_step
        y += y_step
      return all(symbol == symbols[0] for symbol in symbols)

  def check_diagonals(self):
      # Check the two main diagonals
      diagonal1 = self.check_diagonal(0, 0, 1, 1)
      diagonal2 = self.check_diagonal(len(self.spin_results) - 1, 0, -1, 1)
      return diagonal1 or diagonal2
  
  def calculate_payout(self):
    payouts = []
    # Check for a winning combination
    for x in range(self.num_cols):
      if self.check_column(x):
          print(f"Column {x} has a winning combination!")
    for y in range(self.num_rows):
      if self.check_row(y):
          print(f"Row {y} has a winning combination!")
    if self.check_diagonals():
        print("A diagonal has a winning combination!")
    return sum(payouts)

class Game:
  def __init__(self, player_money, slot_machine):
    self.player_money = player_money
    self.slot_machine = slot_machine

  def play(self, bet):
    if bet > self.player_money:
      print("Insufficient funds!")
      return

    self.player_money -= bet
    spin_results = self.slot_machine.spin()
    #payout = self.slot_machine.calculate_payout()

    self.slot_machine.display_slots()
    self.slot_machine.apply_effects()
    self.slot_machine.display_slots()
    #print(f"Payout: {payout}")




def main():
    symbols = [
      SlotsSymbol("CUM"),
      SlotsSymbol("ANT"),
      SlotsSymbol("CAT"),
      DestroySymbol("XXX"),
      ConvertSymbol("OOO")
    ]
    rows = 5
    cols = 5
    symbols.extend([SlotsSymbol("---") for _ in range(rows * cols)])
    slot_machine = SlotMachine(symbols, 5, 5)
    game = Game(100, slot_machine)

    while game.player_money > 0:
        bet = int(input("Enter your bet: "))
        game.play(bet)

if __name__ == "__main__":
    main()