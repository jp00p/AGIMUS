from common import *
from .slots_game import *
import discord.ext.commands


# each level:
# requires x amount of money to complete
# only allowed x amount of spins
# new symbol added each spin
# if complete, level increases
# if fail, the game resets


class SlotsMainScreen(discord.ui.View):
    """main game menu, access all features of the game through here"""

    def __init__(self, game):
        self.game: SlotsGame = game
        self.player = game.player
        timeout = 180
        super().__init__(timeout=timeout)

        self.add_item(SlotsPlayButton(self.game, row=0))
        self.add_item(SlotsContinueButton(self.game, row=0))

        self.embed = discord.Embed(
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
        )


class SlotsPlayScreen(discord.ui.View):
    """where most the action happens"""

    def __init__(self, game, just_added=None):
        self.game: SlotsGame = game
        self.slot_machine = self.game.slot_machine
        self.player = game.player
        super().__init__(timeout=None)

        description = ""

        if just_added:
            description += f"\n> Added {just_added.name} to your collection!\n"

        self.embed = discord.Embed(
            title=f"GAME #{self.game.id}",
            description=description,
        ).set_footer(text=f"Day: {self.game.day}/10 | Game ID: #{self.game.id}")

        if self.slot_machine and self.game.new_symbols:
            self.add_item(NewSymbolsButton(self.game))
        else:
            self.add_item(SpinButton(self.game, row=0, custom_id="game:spin"))
        self.add_item(CancelButton(self.game, custom_id="game:cancel"))
        self.game.get_new_symbols()


class SlotsNewSymbolScreen(discord.ui.View):
    def __init__(self, game, **kwargs):
        self.game: SlotsGame = game
        self.new_symbols = game.new_symbols
        # TODO: Graphics here
        super().__init__(**kwargs)

        self.embed = discord.Embed(
            title="Choose a new symbol to add",
            description="...",
            fields=[
                discord.EmbedField(
                    name=f"{symbol.name}",
                    value=f"{symbol.description}",
                    inline=True,
                )
                for symbol in self.new_symbols
            ],
        ).set_image(
            url=f"attachment://{self.game.player['user_discord_id']}_symbols.png"
        )

        for symbol in self.new_symbols:
            self.add_item(AddSymbolButton(self.game, symbol))
        self.add_item(SkipButton(self.game, row=4))
        # self.add_item(CancelButton(self.game, row=4))


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

        description = f"{self.game.slot_machine}"
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
        await interaction.response.edit_message(view=view, embed=view.embed)


class SpinButton(discord.ui.Button):
    """spin that slot you nasty little slot spinner"""

    def __init__(self, game, **kwargs):
        self.game: SlotsGame = game
        self.player = self.game.player
        self.slot_machine = self.game.slot_machine
        super().__init__(label="Spin!", style=discord.ButtonStyle.green, **kwargs)

    async def callback(self, interaction: discord.Interaction):
        self.slot_machine.spin()

        embed = discord.Embed(
            title="Spin Results",
            description=f"___",
        ).set_footer(
            text=f"GAME #{self.game.id} / SPIN #{self.game.slot_machine.spins}"
        )

        embed.set_image(
            url=f"attachment://{self.player['user_discord_id']}_results.gif"
        )
        view = SlotsPlayScreen(self.game)  # this needs to happen after the spin
        results_image = discord.File(
            fp=f"images/slots_2.0/{self.player['user_discord_id']}_slot_anim.gif",
            filename=f"{self.player['user_discord_id']}_results.gif",
        )
        await interaction.response.edit_message(
            view=view, embed=embed, file=results_image
        )


class NewSymbolsButton(discord.ui.Button):
    """button to go to the new symbols choice screen"""

    def __init__(self, game, **kwargs):
        self.game: SlotsGame = game
        super().__init__(label="Add a new symbol", emoji="⭐")

    async def callback(self, interaction: discord.Interaction):
        symbol_image = discord.File(
            fp=f"images/slots_2.0/{self.game.player['user_discord_id']}_new_symbols.png",
            filename=f"{self.game.player['user_discord_id']}_symbols.png",
        )
        view = SlotsNewSymbolScreen(self.game)

        await interaction.response.edit_message(
            view=view, embed=view.embed, file=symbol_image
        )


class AddSymbolButton(discord.ui.Button):
    def __init__(self, game, symbol, **kwargs):
        self.game: SlotsGame = game
        self.symbol: SlotsSymbol = symbol
        self.slot_machine: SlotMachine = self.game.slot_machine
        super().__init__(
            label=f"{self.symbol.name}", style=discord.ButtonStyle.blurple, **kwargs
        )

    async def callback(self, interaction: discord.Interaction):
        self.slot_machine.symbols.append(self.symbol)
        self.game.clear_new_symbols()
        view = SlotsPlayScreen(self.game, just_added=self.symbol)
        results_image = discord.File(
            fp=f"images/slots_2.0/{self.game.player['user_discord_id']}_slot_anim.gif",
            filename=f"{self.game.player['user_discord_id']}_results.gif",
        )
        view.embed.set_image(
            url=f"attachment://{self.game.player['user_discord_id']}_results.gif"
        )
        await interaction.response.edit_message(
            view=view, embed=view.embed, file=results_image, attachments=[]
        )


class SkipButton(discord.ui.Button):
    def __init__(self, game, **kwargs):
        self.game: SlotsGame = game
        super().__init__(label="Skip", **kwargs)

    async def callback(self, interaction: discord.Interaction):
        self.game.clear_new_symbols()
        results_image = discord.File(
            fp=f"images/slots_2.0/{self.game.player['user_discord_id']}_slot_anim.gif",
            filename=f"{self.game.player['user_discord_id']}_results.gif",
        )

        view = SlotsPlayScreen(self.game)
        view.embed.set_image(
            url=f"attachment://{self.game.player['user_discord_id']}_results.gif"
        )
        view.embed.description = "> You didn't add a new symbol!\n"
        await interaction.response.edit_message(
            view=view, embed=view.embed, file=results_image, attachments=[]
        )


class CancelButton(discord.ui.Button):
    def __init__(self, game, **kwargs):
        self.game: SlotsGame = game
        self.player = game.player
        self.row = kwargs.get("row", 4)
        super().__init__(style=discord.ButtonStyle.danger, label="Cancel", **kwargs)

    async def callback(self, interaction: discord.Interaction):
        view = SlotsMainScreen(self.game)
        await interaction.response.edit_message(view=view, embed=view.embed)


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
        await interaction.response.edit_message(view=view, embed=view.embed)
