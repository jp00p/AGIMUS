import random
from .slots_symbol import SlotsSymbol


class DestroySymbol(SlotsSymbol):
    """destroys symbols around it"""

    def apply_effect(self, spin_results, row, col):
        for i in range(row - 1, row + 2):
            for j in range(col - 1, col + 2):
                if (
                    i >= 0
                    and i < len(spin_results)
                    and j >= 0
                    and j < len(spin_results[0])
                ):
                    spin_results[i][j] = SlotsSymbol("BBB")


class ConvertSymbol(SlotsSymbol):
    """converts symbols around it"""

    def apply_effect(self, spin_results, row, col):
        for i in range(row - 1, row + 2):
            for j in range(col - 1, col + 2):
                if (
                    i >= 0
                    and i < len(spin_results)
                    and j >= 0
                    and j < len(spin_results[0])
                ):
                    spin_results[i][j] = SlotsSymbol(random.choice(["PPP", "QQQ"]))
