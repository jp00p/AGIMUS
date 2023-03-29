from common import *
from .slots_game import *

TEST_SYMBOL_2 = DestructionSymbol(id=None, name="Test Symbol 2")


class SlotsMainScreen(discord.ui.View):
    """main game menu, access all features of the game through here"""

    def __init__(self, game):
        self.game: SlotsGame = game
        self.player = game.player
        super().__init__()

        self.add_item(SlotsPlayButton(self.game, row=0))
        self.add_item(SlotsContinueButton(self.game, row=0))

        self.add_item(
            ClearDatabaseButton(self.game, row=4, style=discord.ButtonStyle.danger)
        )

        ##self.add_item(SlotsShopButton(self.game))
        ##self.add_item(SlotsStatusButton(self.game))

        self.embeds = [
            discord.Embed(
                title="Luck be a Liquidator!",
                description="Liquidator Brunt, FCA, has called in your debts.  You don't have the money on hand, but Brunt is unusually benevolent today and has granted you a payment plan.\n\nBetter get out there and make some profit before he liquidates your whole world!\n\n",
                fields=[
                    discord.EmbedField(
                        name="Here's today's challenges:", value="----", inline=False
                    ),
                    discord.EmbedField(
                        name="Challenge #1",
                        value="Get at least 3 aliens in a row",
                        inline=True,
                    ),
                    discord.EmbedField(
                        name="Challenge #2",
                        value="Spin the slots 150 times",
                        inline=True,
                    ),
                    discord.EmbedField(
                        name="Challenge #3",
                        value="Fill a column with Starfleet",
                        inline=True,
                    ),
                ],
            ),
        ]


class ClearDatabaseButton(discord.ui.Button):
    def __init__(self, game, **kwargs):
        self.game: SlotsGame = game
        super().__init__(label="Clear slots DB", **kwargs)

    async def callback(self, interaction: discord.Interaction):
        queries = [
            "TRUNCATE slots__games;",
            "TRUNCATE slots__user_data;",
            "TRUNCATE slots__machines;",
        ]
        for q in queries:
            with AgimusDB(multi=True) as query:
                query.execute(q)
        await interaction.response.edit_message(
            view=None, content="Database cleared of all slots and sluts!"
        )


class SlotsPlayScreen(discord.ui.View):
    """main slot machine game screen"""

    def __init__(self, game):

        self.game: SlotsGame = game
        self.player = game.player
        super().__init__()
        self.add_item(SpinButton(self.game, row=0))
        self.add_item(CancelButton(self.game))
        self.embeds = [
            discord.Embed(
                title=f"GAME #{self.game.id}",
                description="You may perform the spin manouver whenever you are ready.",
            )
        ]


class LevelSelect(discord.ui.Select):
    """choose a level to start"""

    def __init__(self, game: SlotsGame):
        self.game: SlotsGame = game
        options = [
            discord.SelectOption(label=f"Level {i}", description="")
            for i in range(1, self.game.player["level"] + 1)
        ]
        super().__init__(
            placeholder="Choose a level", min_values=1, max_values=1, options=options
        )

    async def callback(self, interaction: discord.Interaction):
        level = self.values[0]
        self.game.new_game(level)
        view = SlotsPlayScreen(self.game)
        await interaction.response.edit_message(view=view, embeds=view.embeds)


class SlotsPlayButton(discord.ui.Button["SlotsMainScreen"]):
    """start playing the slots"""

    def __init__(self, game, **kwargs):
        self.game: SlotsGame = game
        self.player = game.player
        super().__init__(label="New game", style=discord.ButtonStyle.green, **kwargs)

    async def callback(self, interaction: discord.Interaction):
        # choose level first
        view = SlotsPlayScreen(self.game)
        view.clear_items()
        view.add_item(LevelSelect(self.game))
        view.add_item(CancelButton(self.game))

        description = ""
        if self.game.id:
            description += "> ⚠ This will erase any game currently in play! ⚠\n\n"
        description += (
            "Once you've cleared a level, you will be able to move on to the next one!"
        )
        embed = discord.Embed(
            title="Choose a level to play",
            description=description,
        )
        await interaction.response.edit_message(view=view, embed=embed)


class SlotsContinueButton(discord.ui.Button["SlotsPlayScreen"]):
    """continue an existing game"""

    def __init__(self, game, **kwargs):
        self.game: SlotsGame = game
        disabled = not self.game.id
        super().__init__(
            label="Continue",
            disabled=disabled,
            style=discord.ButtonStyle.secondary,
            **kwargs,
        )

    async def callback(self, interaction: discord.Interaction):
        view = SlotsPlayScreen(self.game)
        await interaction.response.edit_message(view=view, embeds=view.embeds)


class SpinButton(discord.ui.Button):
    """spin that slot"""

    def __init__(self, game, **kwargs):

        self.game: SlotsGame = game
        self.player = game.player
        self.slot_machine = game.slot_machine
        super().__init__(label="Spin!", style=discord.ButtonStyle.green, **kwargs)

    async def callback(self, interaction: discord.Interaction):
        # spin slots
        # render graphics
        # hand out rewards
        # check day/rent/etc
        # give another symbol

        self.slot_machine.spin()
        spin_str = self.slot_machine.display_slots()
        self.slot_machine.apply_effects()
        effects_str = self.slot_machine.display_slots()
        view = SlotsPlayScreen(self.game)
        embed = discord.Embed(
            title="Spin Results",
            description=f"""
Initial Spin:
```
{spin_str}
```

After applying effects:
```
{effects_str}
```

Cool!
            """,
        )
        await interaction.response.edit_message(view=view, embed=embed)


class SlotsNewSymbolScreen(discord.ui.View):
    def __init__(self, game, **kwargs):
        self.game = game
        super().__init__(**kwargs)
        self.embeds = [
            discord.Embed(
                title="Choose a symbol to add",
                description="...",
                fields=[
                    discord.EmbedField(
                        name="Symbol1",
                        value="The description of the symbol",
                        inline=True,
                    )
                ],
            )
        ]
        self.add_item(SkipButton(self.game))
        self.add_item(AddButton(self.game, 0, 0))
        self.add_item(CancelButton(self.game))


class SkipButton(discord.ui.Button):
    def __init__(self, game, **kwargs):
        super().__init__(**kwargs)


class AddButton(discord.ui.Button):
    def __init__(self, game, which, choices, **kwargs):
        self.chosen = which
        self.choices = choices
        super().__init__(**kwargs)


class SlotsShopButton(discord.ui.Button["SlotsMainScreen"]):
    """open the shop"""

    def __init__(self, game, **kwargs):

        self.game = game
        self.player = game.player
        super().__init__(label="Shop!", **kwargs)

    async def callback(self, interaction: discord.Interaction):
        view = SlotsShopView(self.game)
        await interaction.response.edit_message(view=view, embeds=view.embeds)


class SlotsStatusButton(discord.ui.Button["SlotsMainScreen"]):
    """check your stats/items"""

    def __init__(self, game, **kwargs):

        self.game = game
        self.player = game.player
        super().__init__(label="Status", **kwargs)

    async def callback(self, interaction: discord.Interaction):
        return await super().callback(interaction)


class SlotsShopView(discord.ui.View):
    """the ui for the symbol shop"""

    def __init__(self, game):

        self.game = game
        self.player = game.player
        super().__init__()
        self.add_item(CancelButton(self.game))
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

    def __init__(self, game):

        self.game = game
        self.player = game.player
        super().__init__()
        self.add_item(CancelButton(self.game))
        self.embeds = [
            discord.Embed(
                title="Your inventory",
                description="Here are all of your current symbols",
            )
        ]


class CancelButton(discord.ui.Button):
    def __init__(self, game):

        self.game = game
        self.player = game.player
        super().__init__(style=discord.ButtonStyle.danger, label="Cancel", row=4)

    async def callback(self, interaction: discord.Interaction):
        view = SlotsMainScreen(self.game)
        await interaction.response.edit_message(view=view, embeds=view.embeds)
