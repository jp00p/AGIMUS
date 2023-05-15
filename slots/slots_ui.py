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
        super().__init__()

        self.add_item(
            SlotsPlayButton(
                self.game,
                row=0,
                disabled=bool(len(self.game.draft_picks) < DRAFT_ROUNDS),
            )
        )
        if len(self.game.draft_picks) < DRAFT_ROUNDS:
            # if they still have draft picks
            self.add_item(SlotsDraftBegin(self.game, label="Draft symbols"))

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
        ).set_footer(text=f"SEED {self.game.seed}")


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
        )

        if self.slot_machine:
            self.embed.set_footer(
                text=f"Total winnings today: {self.slot_machine.total_winnings}"
            )

        if self.slot_machine and self.game.new_symbols:
            self.add_item(
                SpinButton(self.game, row=0, also_skip=True, custom_id="game:spin")
            )
            self.add_item(NewSymbolsButton(self.game))
        else:
            self.add_item(SpinButton(self.game, row=0, custom_id="game:spin"))
        self.add_item(CancelButton(self.game, custom_id="game:cancel"))
        self.add_item(ViewInventoryButton(self.game, row=1))
        self.add_item(LeaderboardsButton(self.game, row=3))
        self.add_item(DayDebugButton(self.game, row=4))


class DayDebugButton(discord.ui.Button):
    def __init__(self, game, **kwargs):
        self.game: SlotsGame = game
        super().__init__(label="Debug (new day)", **kwargs)

    async def callback(self, interaction: discord.Interaction):
        self.game.new_day()
        view = SlotsMainScreen(self.game)
        view.embed.description += "\n> New day triggered!"
        await interaction.response.edit_message(
            view=view, embed=view.embed, attachments=[]
        )


class SlotsDraftScreen(discord.ui.View):
    """drafting symbols screen"""

    def __init__(self, game, last_symbol=None, **kwargs):
        self.game: SlotsGame = game
        self.round = len(self.game.draft_picks)  # 1,2,3
        self.last_symbol = last_symbol
        logger.info(f"ROUND {self.round}")
        super().__init__(**kwargs)

        self.embed = discord.Embed(
            title=f"Draft your starting slots (Round {self.round+1}/{DRAFT_ROUNDS})",
            description="...",
            fields=[
                discord.EmbedField(name=s.name, value=str(s.description), inline=True)
                for s in self.game.starting_draft[self.round]
            ],
        ).set_image(url=f"attachment://draft_{self.round}.png")

        for s in self.game.starting_draft[self.round]:
            self.add_item(SlotsDraftButton(self.game, s))


class LeaderboardsButton(discord.ui.Button):
    def __init__(self, game, **kwargs):
        self.game: SlotsGame = game
        super().__init__(label="Leaderboards", **kwargs)

    async def callback(self, interaction: discord.Interaction):
        view = LeaderboardsScreen(self.game)
        await interaction.response.edit_message(view=view, embed=view.embed)


class LeaderboardsScreen(discord.ui.View):
    def __init__(self, game, **kwargs):
        self.game: SlotsGame = game
        super().__init__(**kwargs)
        leaderboard_data = self.game.get_leaderboards()
        self.embed = discord.Embed(
            title="Leaderboards", description=f"{leaderboard_data}"
        )
        self.add_item(BackToGameButton(self.game))


class SlotsInventory(discord.ui.View):
    """view all symbols owned"""

    def __init__(self, game, **kwargs):
        self.game: SlotsGame = game
        super().__init__(**kwargs)
        self.embed = discord.Embed(title="Inventory", description="Your symbols")
        self.add_item(BackToGameButton(self.game))


class ViewInventoryButton(discord.ui.Button):
    """go to your inventory screen"""

    def __init__(self, game, **kwargs):
        self.game: SlotsGame = game
        label = "Inventory"
        super().__init__(label=label, **kwargs)

    async def callback(self, interaction: discord.Interaction):
        all_symbols = self.game.slot_machine.symbols
        all_symbols.sort(key=lambda x: x.name, reverse=False)
        inventory_img = await numpy_grid([s.grid_info() for s in all_symbols], (10, 10))
        inventory_img.save("images/slots_2.0/inventory.png")
        view = SlotsInventory(self.game)
        file = discord.File(
            fp="images/slots_2.0/inventory.png", filename="inventory.png"
        )
        view.embed.set_image(url="attachment://inventory.png")
        await interaction.response.edit_message(
            view=view, embed=view.embed, file=file, attachments=[]
        )


class SlotsDraftBegin(discord.ui.Button):
    """start/continue drafting symbols"""

    def __init__(self, game, **kwargs):
        self.game: SlotsGame = game
        self.round = len(self.game.draft_picks)
        super().__init__(**kwargs)

    async def callback(self, interaction: discord.Interaction):
        view = SlotsDraftScreen(self.game)
        await self.game.render_drafts()

        file = discord.File(
            f"images/slots_2.0/draft_{self.game.day}_{self.round}.png",
            filename=f"draft_{self.round}.png",
        )

        await interaction.response.edit_message(
            view=view, embed=view.embed, file=file, attachments=[]
        )


class SlotsDraftButton(discord.ui.Button):
    """draft a symbol"""

    def __init__(self, game, symbol, **kwargs):
        self.game: SlotsGame = game
        self.symbol: SlotsSymbol = symbol
        self.round = len(self.game.draft_picks)  # 1,2,3
        super().__init__(label=self.symbol.name, **kwargs)

    async def callback(self, interaction: discord.Interaction):
        picks = self.game.draft_picks
        picks.append(self.symbol)
        self.game.draft_picks = picks
        self.round = len(self.game.draft_picks)

        if self.round <= DRAFT_ROUNDS - 1:
            file = discord.File(
                f"images/slots_2.0/draft_{self.game.day}_{self.round}.png",
                filename=f"draft_{self.round}.png",
            )
            view = SlotsDraftScreen(self.game, last_symbol=self.symbol)
            view.embed.set_image(url=f"attachment://draft_{self.round}.png")
            await interaction.response.edit_message(
                view=view, embed=view.embed, file=file, attachments=[]
            )
        else:
            # final pick has been made!
            await self.game.render_player_drafts()
            file = discord.File(
                f"images/slots_2.0/draft_{self.game.player['user_discord_id']}.png",
                filename=f"final_draft_{self.game.player['user_discord_id']}.png",
            )
            view = SlotsPlayScreen(self.game, just_added=self.symbol)
            view.embed.set_image(
                url=f"attachment://final_draft_{self.game.player['user_discord_id']}.png"
            )
            view.embed.description += f"\n > Draft complete! Here's your final picks:"
            await interaction.response.edit_message(
                view=view, embed=view.embed, file=file, attachments=[]
            )


class SlotsNewSymbolScreen(discord.ui.View):
    """new symbol selection screen"""

    def __init__(self, game, **kwargs):
        self.game: SlotsGame = game
        self.new_symbols = game.new_symbols
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
        super().__init__(label="Play!", style=discord.ButtonStyle.green, **kwargs)

    async def callback(self, interaction: discord.Interaction):
        if not self.game.id:
            self.game.new_game()
        view = SlotsPlayScreen(self.game)
        await interaction.response.edit_message(view=view, embed=view.embed)


class SpinButton(discord.ui.Button):
    """spin that slot you nasty little slot spinner"""

    def __init__(self, game, also_skip=False, **kwargs):
        self.game: SlotsGame = game
        self.player = self.game.player
        self.slot_machine: SlotMachine = self.game.slot_machine
        self.also_skip = also_skip
        label = "Spin"
        if self.also_skip:
            label = "Spin/skip"
        super().__init__(label=label, style=discord.ButtonStyle.green, **kwargs)

    async def callback(self, interaction: discord.Interaction):
        """if a new game has started, send em back to the menu, otherwise process the spin"""
        if self.game.check_if_finished():
            self.game = self.game.new_game()
            view = SlotsMainScreen(self.game)
            embed = discord.Embed(
                title="A new day dawns",
                description="Your previous slot machine has been shut down while Brunt collects his winnings.",
            )
            await interaction.response.edit_message(
                view=view, embeds=[embed, view.embed], attachments=[]
            )
            return
        await self.game.get_new_symbols()
        self.slot_machine.spin().apply_effects().collect_final_symbols()
        await self.slot_machine.render_results()
        self.slot_machine.calculate_payout()

        embed = discord.Embed(
            title="Spin Results",
            description=f"\n > **Total payout for this spin:** {self.slot_machine.payout}",
        ).set_footer(text=f"Total winnings today: {self.slot_machine.total_winnings}")

        embed.set_image(
            url=f"attachment://{self.player['user_discord_id']}_results.gif"
        )
        view = SlotsPlayScreen(self.game)  # this needs to happen after the spin
        results_image = discord.File(
            fp=f"images/slots_2.0/{self.player['user_discord_id']}_slot_anim.gif",
            filename=f"{self.player['user_discord_id']}_results.gif",
        )
        await interaction.response.edit_message(
            view=view,
            embed=embed,
            file=results_image,
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
            label=f"{self.symbol.name}", style=discord.ButtonStyle.primary, **kwargs
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


class BackToGameButton(discord.ui.Button):
    def __init__(self, game, **kwargs):
        self.game = game
        super().__init__(label="Back to game", **kwargs)

    async def callback(self, interaction: discord.Interaction):
        view = SlotsPlayScreen(self.game)
        await interaction.response.edit_message(
            view=view, embed=view.embed, attachments=[]
        )


class CancelButton(discord.ui.Button):
    def __init__(self, game, **kwargs):
        self.game: SlotsGame = game
        self.player = game.player
        self.row = kwargs.get("row", 4)
        super().__init__(style=discord.ButtonStyle.danger, label="Main menu", **kwargs)

    async def callback(self, interaction: discord.Interaction):
        view = SlotsMainScreen(self.game)
        await interaction.response.edit_message(
            view=view, embed=view.embed, attachments=[]
        )
