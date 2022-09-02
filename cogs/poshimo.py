from common import *
from pocket_shimodae.game import *

class PocketShimodae(commands.Cog):
  def __init__(self, bot):
    self.bot = bot  
    self.game = None
    self.all_trainers = None
  
  ps = discord.SlashCommandGroup("ps", "poShimo game commands")

  @commands.Cog.listener()
  async def on_ready(self):
    self.game = PoshimoGame()
    self.all_trainers = PoshimoGame().get_all_trainers()
    logger.info(self.all_trainers)


  @ps.command(
    name="test",
    description="testing testing 123"
  )
  async def test(self, ctx:discord.ApplicationContext):
    starters = self.game.starter_poshimo
    await ctx.respond(starters)
    logger.info(starters)


  @ps.command(
    name="start",
    description="Register as a new player and start your poShimo journey!"
  )
  async def start(self, ctx:discord.ApplicationContext):
    """Starts the game for a new player (does nothing if you are already registered)"""

    if ctx.author.id in self.all_trainers:
      await ctx.respond("You're already registered!", ephemeral=True)
      return

    user_info = get_user(ctx.author.id)

    # start building the dict we'll send to register_player
    trainer_info = {
      "userid" : user_info["id"]
    }

    # pick your starter poShimo
    

    trainer_id = self.game.register_trainer(trainer_info)
    if trainer_id != 0:
      await ctx.respond(f"You've been registered: TRAINER ID NUMBER: {trainer_id}")
    else:
      await ctx.respond(f"There was some kind of anomaly trying to registering you!")