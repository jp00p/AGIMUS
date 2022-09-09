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
