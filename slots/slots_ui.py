from common import *
from .slots_symbol import load_symbol, SlotsSymbol
from .slots_game import SlotsGame

TEST_SYMBOL_2 = SlotsSymbol(id=None, name="Test Symbol 2")


class SlotsMainScreen(discord.ui.View):
    """main game menu, access all features of the game through here"""

    def __init__(self, player, game):
        self.player = player
        self.game: SlotsGame = game
        super().__init__()
        self.add_item(SlotsPlayButton(self.player))
        self.add_item(SlotsShopButton(self.player))
        self.add_item(SlotsStatusButton(self.player))
        self.add_item(DebugButton(self.player))
        game.give_symbol()

        self.embeds = [
            discord.Embed(
                title="Slotegema",
                description="Slot machine subroutine activated. Here are today's current missions:",
                fields=[
                    discord.EmbedField(
                        name="Challenge #1", value="Get at least 3 aliens in a row"
                    ),
                    discord.EmbedField(
                        name="Challenge #2", value="Spin the slots 150 times"
                    ),
                    discord.EmbedField(
                        name="Challenge #3", value="Fill a column with Starfleet"
                    ),
                ],
            ),
        ]


class DebugButton(discord.ui.Button):
    def __init__(self, player, **kwargs):
        self.player = player
        super().__init__(label="DEBUG", **kwargs)

    async def callback(self, interaction: discord.Interaction):
        with AgimusDB() as query:
            sql = "SELECT symbol_data FROM slots__user_inventory WHERE id = 1"
            query.execute(sql)
            result = query.fetchall()
        test = load_symbol(1)
        logger.info(test.name)
        return await super().callback(interaction)


class SlotsPlayScreen(discord.ui.View):
    """main slot machine game screen"""

    def __init__(self, player):
        self.player = player
        super().__init__()
        self.add_item(SpinButton(self.player, row=0))
        self.add_item(CancelButton(self.player))
        self.embeds = [
            discord.Embed(
                title="Ready to spin",
                description="You may perform the spin manouver whenever you are ready.",
            )
        ]


class SlotsPlayButton(discord.ui.Button["SlotsMainScreen"]):
    """start playing the slots"""

    def __init__(self, player, **kwargs):
        self.player = player
        super().__init__(label="Play!", **kwargs)

    async def callback(self, interaction: discord.Interaction):
        view = SlotsPlayScreen(self.player)
        await interaction.response.edit_message(view=view, embeds=view.embeds)


class SpinButton(discord.ui.Button):
    """spin that slot"""

    def __init__(self, player, **kwargs):
        self.player = player
        super().__init__(label="Spin!", style=discord.ButtonStyle.green, **kwargs)

    async def callback(self, interaction: discord.Interaction):
        view = SlotsPlayScreen(self.player)


class SlotsShopButton(discord.ui.Button["SlotsMainScreen"]):
    """open the shop"""

    def __init__(self, player, **kwargs):
        self.player = player
        super().__init__(label="Shop!", **kwargs)

    async def callback(self, interaction: discord.Interaction):
        view = SlotsShopView(self.player)
        await interaction.response.edit_message(view=view, embeds=view.embeds)


class SlotsStatusButton(discord.ui.Button["SlotsMainScreen"]):
    """check your stats/items"""

    def __init__(self, player, **kwargs):
        super().__init__(label="Status", **kwargs)

    async def callback(self, interaction: discord.Interaction):
        return await super().callback(interaction)


class SlotsShopView(discord.ui.View):
    """the ui for the symbol shop"""

    def __init__(self, player):
        self.player = player
        super().__init__()
        self.add_item(CancelButton(self.player))
        self.embeds = [
            discord.Embed(
                title="Slots shop",
                description="Expand your slots experience with these new symbols",
                fields=[
                    discord.EmbedField(
                        name="Locutus",
                        value="Payout: 5\nRarity: Very Rare\nConverts all adjacent Starfleet to Borg drones\nPrice: 1000",
                    ),
                    discord.EmbedField(
                        name="Fajo",
                        value="Payout: 3\nRarity: Uncommon\nHas a 1% chance to add a rare symbol to an empty adjacent space.\nPrice: 500",
                    ),
                    discord.EmbedField(
                        name="Tribble",
                        value="Payout: 1\nRarity: Common\nAdds another tribble to your inventory every spin\nPrice: 250",
                    ),
                ],
            )
        ]


class SlotsInventoryView(discord.ui.View):
    """the ui for user's symbol inventory"""

    def __init__(self, player):
        self.player = player
        super().__init__()
        self.add_item(CancelButton(self.player))
        self.embeds = [
            discord.Embed(
                title="Your inventory",
                description="Here are all of your current symbols",
            )
        ]


class CancelButton(discord.ui.Button):
    def __init__(self, player):
        self.player = player
        super().__init__(style=discord.ButtonStyle.danger, label="Cancel", row=4)

    async def callback(self, interaction: discord.Interaction):
        view = SlotsMainScreen(self.player)
        await interaction.response.edit_message(view=view, embeds=view.embeds)
