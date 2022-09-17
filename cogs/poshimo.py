from doctest import debug_script
from common import *
from pocket_shimodae.game import *
from pocket_shimodae.views import *

class PocketShimodae(commands.Cog):
  def __init__(self, bot):
    self.bot = bot  
    self.game = None
    self.all_trainers = None
  
  ps = discord.SlashCommandGroup("ps", "poShimo game commands")

  @commands.Cog.listener()
  async def on_ready(self):
    self.game = PoshimoGame(self) # load the game, this will be important later i think
    self.all_trainers = self.game.get_all_trainers()
    logger.info(f"ALL POSHIMO TRAINERS: {self.all_trainers}")

  @ps.command(
    name="test_add_poshimo",
    description="DEBUG"
  )
  async def test_add_poshimo(self, ctx:discord.ApplicationContext):
    p = self.game.test_add_poshimo(ctx.author.id)
    await ctx.respond(f"Did you win? {p.display_name}")

  @ps.command(
    name="test_clear_db",
    description="DEBUG"
  )
  async def test_clear_db(self, ctx:discord.ApplicationContext):
    self.game.test_clear_db()
    await ctx.respond(f"Did you feel that?")

  @ps.command(
    name="start",
    description="Register as a new player and start your Poshimo journey!"
  )
  async def start(self, ctx:discord.ApplicationContext):
    """Starts the game for a new player (does nothing if you are already registered)"""
    if ctx.author.id in self.all_trainers:
     await ctx.respond("You're already registered!", ephemeral=True)
     return
    await ctx.defer(ephemeral=True)
    intro = registration.StarterPages(self)
    await intro.paginator.respond(ctx.interaction, ephemeral=True)

  @ps.command(
    name="status",
    description="Get your current game status"
  )
  async def status(self, ctx:discord.ApplicationContext):
    await ctx.defer(ephemeral=True)
    status_screen = status.Status(self, ctx.author.id)
    await ctx.followup.send(embed=status_screen.get_embed())
  
  @ps.command(
    name="manage",
    description="Manage your Poshimo"
  )
  async def manage(self, ctx:discord.ApplicationContext):
    await ctx.defer(ephemeral=True)
    manage_screen = manage.ManageStart(self, ctx.author.id)
    await ctx.followup.send(embed=manage_screen.get_embed(), view=manage_screen)

  @ps.command(
    name="help",
    description="DOES NOTHING YET Get information about this game and the commands"
  )
  async def help(self, ctx:discord.ApplicationContext):
    await ctx.defer(ephemeral=True)

  @ps.command(
    name="sac",
    description="DOES NOTHING YET Manage your Poshimo Sac"
  )
  async def sac(self, ctx:discord.ApplicationContext):
    await ctx.defer(ephemeral=True)
  
  @ps.command(
    name="swap",
    description="DOES NOTHING YET Swap out your active Poshimo"
  )
  async def swap(self, ctx:discord.ApplicationContext):
    await ctx.defer(ephemeral=True)

  @ps.command(
    name="explore",
    description="DOES NOTHING YET Explore your current location"
  )
  async def explore(self, ctx:discord.ApplicationContext):
    await ctx.defer(ephemeral=True)

  @ps.command(
    name="travel",
    description="Move to a different location"
  )
  async def travel(self, ctx:discord.ApplicationContext):
    await ctx.defer(ephemeral=True)
    travel_agency = travel.TravelMenu(self, ctx.author.id)
    await ctx.followup.send(embed=travel_agency.get_embed(), view=travel_agency)

  @ps.command(
    name="duel",
    description="DOES NOTHING YET Start a duel with another trainer"
  )
  async def explore(self, ctx:discord.ApplicationContext):
    await ctx.defer(ephemeral=True)