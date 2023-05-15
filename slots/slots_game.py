""" 
The main entrypoint for the slot machine game
This is what interfaces with Discord initially
A game has a SlotMachine attached which handles almost all the actual gameplay functionality
"""
from common import *
import glob, pytz
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

# winners get latinum
# latinum exchange for points or badges?

DRAFT_ROUNDS = 5
DRAFT_PICKS_MAX = 3
SECRET_SEED_NUMBER = 2141985
TZ = os.getenv("TZ")


class SlotsGame:
    """the main slots game wrapper! handles playter registration, creating slot machines, and generating drafts"""

    def __init__(self, user_discord_id=None):
        self.id: int = None
        self.user_discord_id: int = user_discord_id
        if self.user_discord_id:
            self.player: dict = self.lookup_player() or self.register_player()
            self.day: int = datetime.now().timetuple().tm_yday
            self.slot_machine: SlotMachine = None
            self._new_symbols: List[SlotsSymbol] = []

            self.seed = self.get_daily_reset_time()
            self.random = random.Random(self.seed)

            self.challenges = []
            self.starting_draft: List[List[SlotsSymbol]] = self.generate_drafts()
            self._draft_picks: List[SlotsSymbol] = []

            self.startup()
            logger.info(
                f"Game initialized for {self.player} - Existing game ID: {self.id}"
            )

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
                self.id, new_game=False, user_id=self.player["user_discord_id"]
            )
            self.get_leaderboards()

    def new_game(self):
        """start a new game, set all old games to finished"""
        # draft cards
        logger.info("Starting a new game!")
        # self.slot_machine = None
        self.clear_new_symbols()
        self.clear_draft_picks()
        queries = [
            {
                "sql": "UPDATE slots__games SET finished = 1 WHERE user_discord_id = %(user_discord_id)s;",
                "vals": {"user_discord_id": self.player["user_discord_id"]},
            },
            {
                "sql": "INSERT INTO slots__games (user_discord_id, time_started) VALUES (%(user_discord_id)s, %(time_started)s);",
                "vals": {
                    "user_discord_id": self.player["user_discord_id"],
                    "time_started": datetime.now(pytz.timezone(TZ)),
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
        return self

    def check_if_finished(self):
        with AgimusDB() as query:
            sql = "SELECT finished FROM slots__games WHERE id = %s"
            vals = (self.id,)
            query.execute(sql, vals)
            finished = query.fetchone()
        return bool(finished[0])

    async def get_new_symbols(self):
        """load 3 new symbols for choosing after a spin"""
        if not self.new_symbols:
            temp_symbols = basic_symbols.copy() + rare_symbols.copy()
            random_choices = self.random.sample(
                temp_symbols, k=DRAFT_PICKS_MAX
            )  # TODO: weights
            self.new_symbols = random_choices
            symbol_data = [s.grid_info() for s in self.new_symbols]
            new_symbol_graphics = await numpy_grid(symbol_data, (1, DRAFT_PICKS_MAX))
            new_symbol_graphics.save(
                f"images/slots_2.0/{self.player['user_discord_id']}_new_symbols.png"
            )
        return self.new_symbols

    def clear_new_symbols(self):
        """empty the new symbols array after they pick or skip"""
        self.new_symbols = []

    def new_day(self):
        self.seed = self.get_daily_reset_time()
        with AgimusDB() as query:
            sql = "UPDATE slots__games SET finished = 1 WHERE id != 0"
            query.execute(sql)

        self.get_leaderboards()
        file = discord.File(
            "images/slots_2.0/daily_leaderboards.png", filename="leaderboards.png"
        )
        embed = discord.Embed(
            title="New day, new debt!",
            description="It's time for Brunt to collect his earnings! He gathers all the credits you've gained and gives you your cut in the form of latinum.",
        )
        embed.set_image(url="attachment://leaderboards.png")
        return embed, file

    def get_winners(self):
        with AgimusDB(dictionary=True) as query:
            sql = "SELECT * FROM slots__games ORDER BY total_winnings LIMIT 1"

    # possible scoring
    # most spins - give 3 latinum
    # most points - give 5 latinum
    # challenges - 1 latinum each

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

    def clear_draft_picks(self):
        self.draft_picks = []

    def get_daily_reset_time(self):
        """returns the time offset by 8 hours - this way we can reset the seed at 8AM"""
        seed_time = datetime.now(pytz.timezone(TZ)).replace(
            hour=8, minute=48, second=0, microsecond=0
        ) + timedelta(days=1)
        mod = seed_time.day + 5
        final_seed = int((seed_time.timestamp() + SECRET_SEED_NUMBER) * (mod / 5))
        return final_seed

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
        draft_pool = all_symbols.copy()
        self.random.shuffle(draft_pool)
        for _ in range(DRAFT_ROUNDS):
            draft_row = []
            for _ in range(DRAFT_PICKS_MAX):
                draft_row.append(draft_pool.pop())
            draft.append(draft_row)
        return draft

    async def render_drafts(self):
        """render the image used for the draft"""
        d = self.day
        draft_files = glob.glob(f"images/slots_2.0/draft_*_*.png")
        if draft_files:
            """clean up any old draft images"""
            for file in draft_files:
                if f"_{d}_" not in os.path.basename(file):
                    os.remove(file)
        for p in range(DRAFT_ROUNDS):
            # generate draft images if they aren't there
            if not os.path.exists(f"images/slots_2.0/draft_{p}_{d}.png"):
                grid_data = [s.grid_info() for s in self.starting_draft[p]]
                img = await numpy_grid(grid_data, (1, DRAFT_PICKS_MAX))
                img.save(f"images/slots_2.0/draft_{d}_{p}.png")

    async def render_player_drafts(self):
        draft_data = [d.grid_info() for d in self.draft_picks]
        draft_image = await numpy_grid(draft_data, (1, DRAFT_ROUNDS))
        draft_image.save(f"images/slots_2.0/draft_{self.player['user_discord_id']}.png")

    def get_leaderboards(self):
        with AgimusDB(dictionary=True) as query:
            sql = "SELECT user_discord_id,total_winnings,spins FROM slots__games WHERE time_started >= date_sub(now(), interval 1 day) AND finished != 0 ORDER BY total_winnings DESC LIMIT 10"
            query.execute(sql)
            results = query.fetchall()
        generate_leaderboards(results)
        return results
