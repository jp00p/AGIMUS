from common import *
from slots.slots import SlotMachine
from slots.slots_ui import *

class Slots(commands.cog):
  def __init__(self, bot):
    self.bot = bot

  sm = discord.SlashCommandGroup("slots", "Slots!")

  @commands.Cog.listener()
  async def on_ready(self):
    pass

  @sm.command(
    name="play",
    description="Play the slots!"
  )
  async def play(self, ctx:discord.ApplicationContext):
    player = get_user(ctx.author.id)
    view = SlotsGame(player, self)
    await ctx.respond(view=view, embeds=view.embeds)


# self sealing stem bolt
# tribble
# probability modulator
# jumja stick
# tooth sharpener