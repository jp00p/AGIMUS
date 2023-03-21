import random

class SlotsSymbol:
  def __init__(self, name):
    self.name = name
  
  def __str__(self):
    return self.name
  
  def apply_effect(self, spin_results, row, col):
    pass
  
class DestroySymbol(SlotsSymbol):
  def apply_effect(self, spin_results, row, col):
    for i in range(row-1, row+2):
      for j in range(col-1, col+2):
        if i >= 0 and i < len(spin_results) and j >= 0 and j < len(spin_results[0]):
          spin_results[i][j] = SlotsSymbol("BBB")


class ConvertSymbol(SlotsSymbol):
  def apply_effect(self, spin_results, row, col):
    for i in range(row-1, row+2):
      for j in range(col-1, col+2):
        if i >= 0 and i < len(spin_results) and j >= 0 and j < len(spin_results[0]):
          spin_results[i][j] = SlotsSymbol(random.choice(['PPP', 'QQQ']))
