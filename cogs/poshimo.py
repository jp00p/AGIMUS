from common import *
from pocket_shimodae.game import *
from pocket_shimodae.views import *
from pocket_shimodae.utils import get_all_trainers

class PocketShimodae(commands.Cog):
  def __init__(self, bot):
    self.bot = bot  
    self.game = None
    self.all_trainers = None
  
  ps = discord.SlashCommandGroup("ps", "poShimo game commands")

  @commands.Cog.listener()
  async def on_ready(self):
    """ when everything is happily loaded, this will run """
    self.game = PoshimoGame(self) # load the game, this will be important later i think
    self.all_trainers = get_all_trainers()
    logger.info(f"ALL POSHIMO TRAINERS: {self.all_trainers}")

  @tasks.loop(hours=1.0)
  async def set_poshimo_weather(self):
    """ every hour the weather changes """
    self.game.world.set_weather()

  @tasks.loop(minutes=1.0)
  async def check_away_missions(self):
    logger.info("Checking away missions...")

  # @ps.command(
  #   name="test_give_poshimo",
  #   description="DEBUG"
  # )
  # async def test_give_poshimo(self, ctx:discord.ApplicationContext):
  #   p = self.game.test_give_poshimo(ctx.author.id)
  #   await ctx.respond(f"Did you win? {p.display_name}", ephemeral=True)

  # @ps.command(
  #   name="test_unlock_locations",
  #   description="DEBUG"
  # )
  # async def test_unlock_locations(self, ctx:discord.ApplicationContext):
  #   self.game.test_unlock_loc(ctx.author.id, "vertiform field")
  #   self.game.test_unlock_loc(ctx.author.id, "forest of forever")
  #   self.game.test_unlock_loc(ctx.author.id, "heorot")
  #   self.game.test_unlock_loc(ctx.author.id, "new vertiform city")
  #   self.game.test_unlock_loc(ctx.author.id, "meung-sur-loire")
  #   self.game.test_unlock_loc(ctx.author.id, "ktaris pointe")
  #   await ctx.respond(f"All locations unlocked", ephemeral=True)

  # @ps.command(
  #   name="test_give_item",
  #   description="DEBUG"
  # )
  # async def test_give_item(self,ctx:discord.ApplicationContext):
  #   inventory = self.game.test_give_item(ctx.author.id)
  #   await ctx.respond("Here's the list:\n"+"\n".join(item["item"].name for item in inventory), ephemeral=True)

  # @ps.command(
  #   name="test_clear_db",
  #   description="DEBUG"
  # )
  # async def test_clear_db(self, ctx:discord.ApplicationContext):
  #   self.game.test_clear_db()
  #   await ctx.respond(f"Did you feel that?", ephemeral=True)

  # @ps.command(
  #   name="test_fish_log",
  #   description="DEBUG"
  # )
  # async def test_fish_log(self, ctx:discord.ApplicationContext):
  #   self.game.test_fish_log(ctx.author.id)
  #   await ctx.respond(f"Fish log sent to logger for logging purposes", ephemeral=True)

  @ps.command(
    name="start",
    description="Register as a new player and start your Poshimo journey!"
  )
  async def start(self, ctx:discord.ApplicationContext):
    """Starts the game for a new player (does nothing if you are already registered)"""
    if ctx.author.id not in get_all_users():
      register_user(ctx.author)

    if ctx.author.id in self.all_trainers:
     await ctx.respond("You're already registered! Use `/ps menu` to play the game!", ephemeral=True)
     return
    await ctx.defer(ephemeral=True)
    intro = registration.StarterPages(self)
    original_message = await intro.paginator.respond(ctx.interaction, ephemeral=True)
    intro.original_message = original_message

  @ps.command(
    name="menu",
    description="The main game menu",
    aliases=["status", "info"]
  )
  async def status(self, ctx:discord.ApplicationContext):
    await ctx.defer(ephemeral=True)
    if ctx.author.id not in self.all_trainers:
      await ctx.followup.send("You are not registered as a Poshimo trainer yet!  Use `/ps start` to begin your adventures.", ephemeral=True)
    else:
      mm = main_menu.MainMenu(self, ctx.author.id)
      message = await ctx.followup.send(view=mm, embed=mm.get_embed())
      mm.original_message = message
    
  @ps.command(
    name="admin",
    description="Admin debug menu"
  )
  async def admin(self, ctx:discord.ApplicationContext):
    await ctx.defer(ephemeral=True)
    admin_menu = admin.AdminMenu(self, ctx.author.id)
    original_message = await ctx.followup.send(view=admin_menu, embed=admin_menu.get_embed())
    admin_menu.original_message = original_message