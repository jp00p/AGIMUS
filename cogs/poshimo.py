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
    self.game = PoshimoGame() # load the game
    self.all_trainers = self.game.get_all_trainers() # get a list of all active poshimo trainers
    logger.info(f"ALL POSHIMO TRAINERS: {self.all_trainers}")

  @ps.command(
    name="start",
    description="Register as a new player and start your Poshimo journey!"
  )
  async def start(self, ctx:discord.ApplicationContext):
    """Starts the game for a new player (does nothing if you are already registered)"""

    #if ctx.author.id in self.all_trainers:
    #  await ctx.respond("You're already registered!", ephemeral=True)
    #  return
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
    name="help",
    description="Get information about this game and the commands"
  )
  async def help(self, ctx:discord.ApplicationContext):
    await ctx.defer(ephemeral=True)

  @ps.command(
    name="sac",
    description="Manage your Poshimo Sac"
  )
  async def sac(self, ctx:discord.ApplicationContext):
    await ctx.defer(ephemeral=True)
  
  @ps.command(
    name="swap",
    description="Swap out your active Poshimo"
  )
  async def swap(self, ctx:discord.ApplicationContext):
    await ctx.defer(ephemeral=True)

  @ps.command(
    name="explore",
    description="Explore your current location"
  )
  async def explore(self, ctx:discord.ApplicationContext):
    await ctx.defer(ephemeral=True)

  @ps.command(
    name="move",
    description="Move to a new location"
  )
  async def move(self, ctx:discord.ApplicationContext):
    await ctx.defer(ephemeral=True)

  @ps.command(
    name="duel",
    description="Start a duel with another trainer"
  )
  async def explore(self, ctx:discord.ApplicationContext):
    await ctx.defer(ephemeral=True)