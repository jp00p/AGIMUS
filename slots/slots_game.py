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


# challenges reset at 8AM PST
# end of challenge, hand out a badge
# if game started before current day, start a new game
# daily leaderboards
# weekly leaderboards
# all time?

# choose starting loadout (draft, everyone gets the same draft)

DRAFT_ROUNDS = 5
DRAFT_PICKS_MAX = 4
SECRET_SEED_NUMBER = 2141985


class SlotsGame:
    """games can be resumed from previous sessions, which is why this is so dumb!"""

    def __init__(self, user_discord_id):
        self.id: int = None
        self.user_discord_id: int = user_discord_id
        self.player: dict = self.lookup_player() or self.register_player()
        self.level: int = 1
        self.day: int = datetime.now().timetuple().tm_yday
        self.debt: int = 0
        self.slot_machine: SlotMachine = None
        self._new_symbols: List[SlotsSymbol] = []
        self.seed = (
            datetime.now().year
            + datetime.now().month
            + datetime.now().day
            + SECRET_SEED_NUMBER
        )
        self.challenges = []
        self.starting_draft: List[List[SlotsSymbol]] = self.generate_drafts()
        self._draft_picks: List[SlotsSymbol] = []
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
            logger.info(result["time_started"])
            self.id = result["id"]
            new_symbols_json = result.get("new_symbols", None)
            if new_symbols_json:
                for s in json.loads(new_symbols_json):
                    self._new_symbols.append(create_symbol(s))
            draft_picks_json = result.get("draft_picks", None)
            if draft_picks_json:
                for s in json.loads(draft_picks_json):
                    self._draft_picks.append(create_symbol(s))
            self.slot_machine = SlotMachine(
                self.id,
                new_game=False,
                user_id=self.player["user_discord_id"],
                starting_symbols=self.draft_picks,
            )

    def new_game(self, level):
        """start a new game, set all old games to finished"""
        # draft cards
        logger.info("Starting a new game!")
        # self.slot_machine = None
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
            self.id,
            new_game=True,
            user_id=self.player["user_discord_id"],
            starting_symbols=self.draft_picks,
        )

    async def get_new_symbols(self):
        """load 3 new symbols for choosing after a spin"""
        if not self.new_symbols:
            temp_symbols = basic_symbols.copy()
            random_choices = random.sample(
                temp_symbols, k=DRAFT_PICKS_MAX
            )  # TODO: weights
            self.new_symbols = random_choices
            symbol_data = [(s.name, s.payout, (0, 0, 0)) for s in self.new_symbols]
            new_symbol_graphics = await numpy_grid(symbol_data, (1, DRAFT_PICKS_MAX))
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

    @property
    def draft_picks(self):
        return self._draft_picks

    @draft_picks.setter
    def draft_picks(self, val):
        self._draft_picks = val
        logger.info(f"Updating draft picks: {val}")
        draft_picks_json = json.dumps([s.__dict__ for s in val])
        with AgimusDB() as query:
            sql = "UPDATE slots__games SET draft_picks = %s WHERE id = %s"
            vals = (draft_picks_json, self.id)
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

    def generate_drafts(self) -> List[List[SlotsSymbol]]:
        """generate the symbols used for today's draft"""
        # use daily seed for starting draft
        draft = []
        for i in range(DRAFT_ROUNDS):
            draft.append(random.sample(basic_symbols, k=DRAFT_PICKS_MAX))
        return draft

    async def render_drafts(self):
        """render the image used for the draft"""
        d = self.day
        previous_day = d - 1
        if os.path.exists(f"images/slots_2.0/draft_{previous_day}_*"):
            os.remove(f"images/slots_2.0/draft_{previous_day}_*")
        for p in range(DRAFT_ROUNDS):
            # generate draft images if they aren't there
            if not os.path.exists(f"images/slots_2.0/draft_{p}_{d}.png"):
                grid_data = [(s.name, 0, (0, 0, 0)) for s in self.starting_draft[p]]
                img = await numpy_grid(grid_data, (1, DRAFT_PICKS_MAX))
                img.save(f"images/slots_2.0/draft_{d}_{p}.png")

    async def render_player_drafts(self):
        draft_data = [(d.name, 0, (0, 0, 0)) for d in self.draft_picks]
        draft_image = await numpy_grid(draft_data, (1, DRAFT_ROUNDS))
        draft_image.save(f"images/slots_2.0/draft_{self.player['user_discord_id']}.png")
