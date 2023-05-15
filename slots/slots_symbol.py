from common import *
import json
from enum import Enum, auto
from typing import List, TypeVar

SYMBOLS_GRAPHICS_DIR = "images/slots_2.0/symbols/"

# so we can refer to this object in typing
Symbol = TypeVar("Symbol", bound="SlotsSymbol")

STATUS_COLORS = {
    "destroy": (255, 0, 0),
    "alter_payout": (0, 255, 0),
    "did_destroy": (128, 0, 128),
    "did_alter_payout": (0, 128, 0),
    "conversion": (50, 40, 30),
    "did_conversion": (30, 40, 50),
    "none": (0, 24, 24),
    "did_none": (0, 24, 24),
    None: (0, 24, 24),
}


class RARITY(Enum):
    COMMON = auto()
    UNCOMMON = auto()
    RARE = auto()
    SUPER_RARE = auto()


SYMBOL_PROBABILITIES = {
    RARITY.COMMON: 1,
    RARITY.UNCOMMON: 0.7,
    RARITY.RARE: 0.3,
    RARITY.SUPER_RARE: 0.1,
}


class SlotsSymbol(object):
    """a symbol that can show up on the slot_machine or in the shop!"""

    def __init__(self, **kwargs):
        self.name: str = kwargs.get("name", None)
        # self.rarity: int = RARITY[kwargs.get("rarity", "COMMON")]
        self.description: str = kwargs.get("description", None)
        self.tags: List[str] = kwargs.get("tags", [])
        self.base_payout: int = kwargs.get("base_payout", 0)
        self.payout: int = kwargs.get("payout", self.base_payout)
        self.effect_name: str = kwargs.get("effect_name", "none")
        self.effect_where: str = kwargs.get("effect_where", "none")
        self.effect_which: str = kwargs.get("effect_which", "none")
        self.effect_args: dict = kwargs.get("effect_args", {})
        self.affect_self: bool = kwargs.get("affect_self", False)
        self.effect_chance: float = kwargs.get("effect_chance", None)  # 0.0 - 1.0
        self.match_tags: list = kwargs.get("match_tags", [])

        # how many times has this paid out
        self.times_paid: int = kwargs.get("times_paid", 0)
        # how many times has this shown up
        self.times_appeared: int = kwargs.get("times_appeared", 0)
        # how many times has this effect been activated
        self.limited: bool = kwargs.get("limited", False)
        self.uses = kwargs.get("uses", 0)
        self.status = None  # keep track of what happened here
        self.wiggly: bool = False

    def to_json(self) -> str:
        return json.dumps(self, default=lambda o: o.__dict__)

    def __str__(self) -> str:
        return self.name

    def slug(self) -> str:
        return self.name.lower().replace("_", " ")

    def to_img(self) -> str:
        return str(SYMBOLS_GRAPHICS_DIR + self.slug() + ".png")

    def apply_effect(
        self, spin_results: List[List[Symbol]], row: int, col: int
    ) -> List[List[Symbol]]:
        """
        accepts the entire spin result grid, and this symbol's current x,y in that grid
        loops over the grid and applies this symbol's effect to the appropriate symbols


        `row, col` = current symbol's x,y

        when you see `i, j` it refers to the symbol being affected

        this is a mess but it does work probably

        returns the modified spin results

        """

        if self.effect_name == "none" or not self.effect_name:
            # no effect at all
            return spin_results

        if self.effect_chance and random.random() > self.effect_chance:
            # if there's a random chance of the effect and it doesn't fire
            return spin_results

        if self.effect_where == "adjacent":
            """adjacent check loop.  notice the `check_surrounding` condition (and not searching whole board)"""
            for i in range(row - 1, row + 2):
                for j in range(col - 1, col + 2):
                    if self.check_surrounding(i, j, spin_results):
                        if self.effect_which not in ["any", "none", "tag"]:
                            if spin_results[i][j].slug() in self.effect_which:
                                """affects specifically named symbols"""
                                spin_results = self.do_effect(
                                    spin_results, i, j, row, col
                                )

                        elif self.effect_which == "any":
                            """affects all symbols regardless"""
                            spin_results = self.do_effect(spin_results, i, j, row, col)
                        elif self.effect_which == "tag":
                            if spin_results[i][j].check_tag_match(self.match_tags):
                                """affects symbols that match a tag"""
                                spin_results = self.do_effect(
                                    spin_results, i, j, row, col
                                )

        if self.effect_where == "any":
            """anywhere check loop.  just searches the whole board"""
            for i in range(5):
                for j in range(5):
                    if self.effect_which not in ["any", "none", "tag"]:
                        if spin_results[i][j].slug() in self.effect_which:
                            spin_results = self.do_effect(spin_results, i, j, row, col)
                    elif self.effect_which == "any":
                        spin_results = self.do_effect(spin_results, i, j, row, col)
                    elif self.effect_which == "tag":
                        if spin_results[i][j].check_tag_match(self.match_tags):
                            """affects symbols that match a tag"""
                            spin_results = self.do_effect(spin_results, i, j, row, col)
        if self.effect_where == "none":
            """don't loop over the results (for custom effects)"""
            pass

        return spin_results

    def set_status(self, effect_name=None):
        self.status = None
        self.wiggly = False
        if effect_name and effect_name != "none":
            self.status = "did_" + self.effect_name
            self.wiggly = True

    def affect_grid_item(self, results, row, col, affect_self=False) -> None:
        self.set_status(self.effect_name)

        if not affect_self:
            results[row][col] = results[row][col].effect(
                self.effect_name, self.effect_args
            )
        else:
            results[row][col] = self.effect(self.effect_name, self.effect_args)

        return results

    def do_effect(self, spin_results, i, j, row, col):
        """do the effect on others or self"""
        if self.affect_self:  # only affects self
            spin_results = self.affect_grid_item(
                spin_results, row, col, affect_self=True
            )
            self.effect_complete()
        else:  # affects others
            spin_results = self.affect_grid_item(spin_results, i, j)
            spin_results[row][col] = spin_results[row][col].effect_complete()
        return spin_results

    def effect(self, effect_name, effect_args) -> Symbol:
        """this is run on a symbol being affected by this symbol (does NOT run on the symbol applying effects)"""
        if getattr(self, "effect_" + effect_name):
            self.wiggly = True
            self.payout = self.base_payout
            self.status = effect_name
            self.uses = self.uses - 1
            return getattr(self, "effect_" + effect_name)(**effect_args)

    # each of these are types of effects to be applied
    # they are only run on the symbol being affected!
    # these should return a SlotsSymbol object of some kind
    def effect_conversion(self, convert_to) -> Symbol:
        """convert to a new symbol"""
        from . import symbol_defs

        convert_to = getattr(symbol_defs, convert_to)
        convert_to = random.choice(convert_to)
        return convert_to

    def effect_destroy(self, payout=0) -> Symbol:
        """destroy a symbol"""
        return EmptySymbol(payout=payout)

    def effect_alter_payout(self, new_payout, permanent=False) -> Symbol:
        """change the payout"""
        if permanent:
            self.base_payout += new_payout
        self.payout += new_payout
        return self

    def effect_none(self) -> Symbol:
        """nothing!"""
        return EmptySymbol()

    def effect_transform(self) -> Symbol:
        return SlotsSymbol()

    def effect_prevent_destruction(self):
        pass

    def effect_unlock(self, box):
        from . import symbol_defs

        if self.slug() == box:
            unlocks = self.effect_args["unlocks"]
            unlockables, chances = zip(*unlocks)
            unlocked = random.choices(unlockables, weights=chances, k=1)[0]
            box_contents = getattr(symbol_defs, unlocked)
            prize = random.choice(box_contents)
            logger.info(
                f"Unlockables: {unlockables} \n Chances: {chances}\n Prize: {prize}"
            )
            return prize

    #
    #
    #
    def effect_complete(self) -> Symbol:
        self.uses = max(self.uses - 1, 0)
        logger.info(f"Finished running effects on {self.name} - uses: {self.uses}")
        if self.limited and self.uses <= 0:
            logger.info(f"No more uses!")
            return EmptySymbol(payout=0)
        else:
            return self

    def on_destroy(self) -> Symbol:
        return self

    def added_to_result(self) -> None:
        """if a symbol showed up in results, this fires"""
        self.times_appeared += 1

    def grid_info(self, wiggle=False) -> tuple:
        """build a tuple for sending to grid image renderer

        the tuple contains:
          - symbol name
          - symbol payout
          - status color
          - wiggle true/false
          - number of uses (if relevant)
        """
        return (
            self.name,
            self.payout,
            STATUS_COLORS[self.status],
            bool(self.wiggly and wiggle),
            self.uses if self.limited else 0,
        )

    def check_surrounding(
        self, increment_1, increment_2, grid_results, include_self=False
    ) -> bool:
        """checks the 8 tiles around a given symbol, excludes self by default"""
        if not include_self:
            return (
                increment_1 >= 0
                and increment_1 < len(grid_results)
                and increment_2 >= 0
                and increment_2 < len(grid_results[0])
            )
        return (
            increment_1 >= 0
            and increment_1 < len(grid_results)
            and increment_2 >= 0
            and increment_2 < len(grid_results[0])
            and grid_results[increment_1][increment_2] != self
        )

    def check_tag_match(self, tags) -> bool:
        """check if a symbol has the given tag"""
        for tag in tags:
            if tag in self.tags:
                return True
        return False


# UTILITIES
def create_symbol(symbol_db_info: dict) -> SlotsSymbol:
    """create symbol from text data"""
    if isinstance(symbol_db_info, str):
        symbol_db_info = json.loads(symbol_db_info)
    classname = symbol_db_info.get("type", "SlotsSymbol")
    the_class = globals()[classname]
    instance = the_class(**symbol_db_info)
    return instance


def load_from_json(json_str) -> List[SlotsSymbol]:
    final_list = []
    for s in json_str:
        if s:
            final_list.append(create_symbol(json.loads(s)))
    return final_list


""" these are symbol types that do special things! """


class EmptySymbol(SlotsSymbol):
    """an empty slot on the grid"""

    def __init__(self, **kwargs):
        super().__init__(name="Empty", base_payout=0, **kwargs)


class BorgItemSymbol(SlotsSymbol):
    """a piece of borg tech"""

    def __init__(self, **kwargs):
        super().__init__(
            base_payout=0,
            tags=["borg"],
            effect_where="any",
            effect_which="tag",
            match_tags=["borg"],
            effect_name="alter_payout",
            affect_self=True,
            description="Gains 5 points for every other Borg item on screen",
            effect_args={"new_payout": 5, "permanent": False},
            **kwargs,
        )


class BasicFoodSymbol(SlotsSymbol):
    def __init__(self, **kwargs):
        super().__init__(base_payout=1, tags=["food"], **kwargs)
