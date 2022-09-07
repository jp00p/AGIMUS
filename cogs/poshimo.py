from common import *
from pocket_shimodae.game import *
import pocket_shimodae.views as psViews

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
    name="test",
    description="testing testing 123"
  )
  async def test(self, ctx:discord.ApplicationContext):
    view = psViews.StarterPages(self)
    await view.get_paginator().respond(ctx.interaction)

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
      await ctx.respond(f"You've been registered: Welcome to the world of POCKET SHIMODA, Trainer #{trainer_id:03d}!")
    else:
      await ctx.respond(f"There was some kind of anomaly trying to registering you! Maybe you're already registered.")