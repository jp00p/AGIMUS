from common import *
from slots.slots_game import *
from slots.slots_ui import SlotsMainScreen


class Slots(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    sm = discord.SlashCommandGroup("slots", "Slots!")

    @commands.Cog.listener()
    async def on_ready(self):
        pass

    @sm.command(name="play", description="Play the slots!")
    async def play(self, ctx: discord.ApplicationContext):
        if ctx.author.id not in get_all_users():
            register_user(ctx.author)

        game = SlotsGame(ctx.author.id)
        view = SlotsMainScreen(game)
        await ctx.respond(view=view, embeds=view.embeds, ephemeral=True)
