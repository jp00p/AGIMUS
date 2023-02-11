from common import *
from ..ui import *
from ..objects.battle import PoshimoBattle
from . import battle as mm_battle
from . import fishing as mm_fish
from . import inventory as mm_inventory
from . import manage as mm_manage
from . import missions as mm_missions
from . import shop as mm_shop
from . import travel as mm_travel
from . import emh as mm_emh
from . import crafting as mm_crafting
from . import exploration as mm_exploration

class MainMenu(PoshimoView):
  ''' the primary menu '''
  def __init__(self, cog, trainer):
    super().__init__(cog, trainer)
    self.trainer_location = self.game.find_in_world(self.trainer.location)
    self.embeds = [
      discord.Embed(
        title=f"{self.trainer}'s overview",
        description=fill_embed_text("The world of Poshimo awaits"),
        fields=[
          discord.EmbedField(name="Location", value=f"{self.trainer_location}", inline=False),
          discord.EmbedField(name="Current status", value=f"{self.trainer.status}", inline=True),
          discord.EmbedField(name="Wins/losses", value=f"{self.trainer.wins}/{self.trainer.losses}", inline=True),
          discord.EmbedField(name="Scarves", value=f"{self.trainer.scarves}", inline=True),
          discord.EmbedField(name="Crafting level", value=f"{self.trainer.crafting_level} ({self.trainer.crafting_xp} xp)"),
          discord.EmbedField(name="Belt buckles", value=f"{self.trainer.buckles}", inline=True),
          discord.EmbedField(name="Active Poshimo", value=f"{self.trainer.active_poshimo}", inline=False),
          discord.EmbedField(name="Poshimo Sac", value=f"{self.trainer.list_sac()}", inline=False),
          discord.EmbedField(name="Poshimo on missions", value=f"{self.trainer.list_away()}", inline=False)
        ]
      )
    ]
    self.add_item(ManageMenuButton(self.cog, self.trainer, row=1))
    self.add_item(FishingMenuButton(self.cog, self.trainer, row=1))
    self.add_item(InventoryMenuButton(self.cog, self.trainer, row=1))
    #self.add_item(ExplorationMenuButton(self.cog, self.trainer, row=1))

    self.add_item(TravelMenuButton(self.cog, self.trainer, row=2))
    self.add_item(ShopMenuButton(self.cog, self.trainer, self.trainer_location, row=2))
    self.add_item(CraftingMenuButton(self.cog, self.trainer, row=2))
    self.add_item(EMHMenuButton(self.cog, self.trainer, row=2))

    self.add_item(QuestMenuButton(self.cog, self.trainer, row=3))    
    self.add_item(HuntMenuButton(self.cog, self.trainer, row=3))
    self.add_item(DuelMenuButton(self.cog, self.trainer, row=3))


class BackToMainMenu(BackButton):
  def __init__(self, cog, trainer):
    super().__init__(
      MainMenu(cog, trainer),
      label=BACK_TO_MAIN_MENU
    )


class FishingMenuButton(discord.ui.Button):
  ''' the button to open the fishing menu '''
  def __init__(self, cog, trainer, **kwargs):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      label="Fishing",
      emoji="🐟",
      disabled=bool(self.trainer.status is TrainerStatus.BATTLING),
      **kwargs
    )
  async def callback(self, interaction):
    view = mm_fish.FishingLog(self.cog, self.trainer)
    # view.add_item(BackToMainMenu(self.cog, self.trainer))
    await interaction.response.edit_message(view=view, embed=view.get_embed())

class ExplorationMenuButton(discord.ui.Button):
  def __init__(self, cog, trainer, **kwargs):
    self.trainer = trainer
    self.cog = cog
    super().__init__(
      label="Explore?!",
      emoji="📼",
      **kwargs
    )
  async def callback(self, interaction):
    view = mm_exploration.ExploreMenu(self.cog, self.trainer)
    await interaction.response.edit_message(view=view, embeds=view.get_embeds())

class InventoryMenuButton(discord.ui.Button):
  ''' the button to open the inventory menu '''
  def __init__(self, cog, trainer, **kwargs):
    self.trainer = trainer
    self.cog = cog
    super().__init__(
      label="Inventory",
      emoji="💼",
      disabled=bool(self.trainer.status is TrainerStatus.BATTLING),
      **kwargs
    )
  async def callback(self, interaction):
    view = mm_inventory.InventoryMenu(self.cog, self.trainer)
    await interaction.response.edit_message(view=view, embed=view.get_embed())


class ManageMenuButton(discord.ui.Button):
  def __init__(self, cog, trainer, **kwargs):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      label="Manage Poshimo",
      emoji="🔧",
      disabled=bool(self.trainer.status is TrainerStatus.BATTLING),
      **kwargs
    )
  async def callback(self, interaction:discord.Interaction):
    view = mm_manage.ManageStart(self.cog, self.trainer)
    await interaction.response.edit_message(view=view, embed=view.get_embed())


class TravelMenuButton(discord.ui.Button):
  def __init__(self, cog, trainer, **kwargs):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      label="Travel",
      emoji="✈",
      disabled=bool(self.trainer.status is TrainerStatus.BATTLING),
      **kwargs
    )
  async def callback(self, interaction:discord.Interaction):
    view = mm_travel.TravelMenu(self.cog, self.trainer)
    # view.add_item(BackToMainMenu(self.cog, self.trainer))
    await interaction.response.edit_message(view=view, embed=view.get_embed())


class CraftingMenuButton(discord.ui.Button):
  def __init__(self, cog, trainer, **kwargs):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      label="Crafting",
      emoji="🔨",
      disabled=False, #bool(self.trainer.status is TrainerStatus.BATTLING),
      **kwargs
    )
  async def callback(self, interaction:discord.Interaction):
    view = mm_crafting.CraftingMenu(self.cog, self.trainer)
    await interaction.response.edit_message(view=view, embeds=view.get_embeds())


class ShopMenuButton(discord.ui.Button):
  def __init__(self, cog, trainer, location, **kwargs):
    self.cog = cog
    self.trainer = trainer
    self.location = location
    super().__init__(
      label="Shopping",
      emoji="🛒",
      disabled=bool(self.location.shop is None or self.trainer.status is TrainerStatus.BATTLING),
      **kwargs
    )
  async def callback(self, interaction:discord.Interaction):
    view = mm_shop.ShoppingScreen(self.cog, self.trainer, self.location.shop)
    await interaction.response.edit_message(view=view, embed=view.get_embed())


class QuestMenuButton(discord.ui.Button):
  def __init__(self, cog, trainer, **kwargs):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      label="Missions",
      emoji="💎",
      disabled=bool(self.trainer.status is TrainerStatus.BATTLING),
      **kwargs
    )
  async def callback(self, interaction:discord.Interaction):
    view = mm_missions.ManageAwayMissions(self.cog, self.trainer)
    # view.add_item(BackToMainMenu(self.cog, self.trainer))
    await interaction.response.edit_message(view=view, embed=view.get_embed())


class EMHMenuButton(discord.ui.Button):
  def __init__(self, cog, trainer, **kwargs):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      label="Call EMH",
      emoji="🩺",
      disabled=bool(self.trainer.status is TrainerStatus.BATTLING),
      **kwargs
    )
  async def callback(self, interaction:discord.Interaction):
    view = mm_emh.SummonEMH(self.cog, self.trainer)
    await interaction.response.edit_message(view=view, embed=view.get_embed())


class DuelMenuButton(discord.ui.Button):
  def __init__(self, cog, trainer, **kwargs):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      label="Duel",
      emoji="⚔",
      disabled=True, #bool(self.trainer.status is TrainerStatus.BATTLING),
      **kwargs
    )
  async def callback(self, interaction:discord.Interaction):
    pass


class HuntMenuButton(discord.ui.Button):
  def __init__(self, cog, trainer:PoshimoTrainer, **kwargs):
    self.cog = cog
    self.game:PoshimoGame = self.cog.game
    self.trainer = trainer
    disabled = False

    if self.trainer.status is TrainerStatus.BATTLING:
      label = "Resume your hunt"
      emoji = "⏯"
      
    else:
      label = "Start a hunt"
      emoji = "🏹"
    
    if not self.trainer.is_active_poshimo_ready():
      label = "Hunt not ready"
      disabled = True
      emoji = "❌"

    super().__init__(
      label=label,
      emoji=emoji,
      disabled=disabled,
      **kwargs
    )
    
  async def callback(self, interaction:discord.Interaction):     
    if self.trainer.status is TrainerStatus.BATTLING:
      old_hunt = self.game.resume_battle(self.trainer)
      resumed_battle = mm_battle.BattleTurn(self.cog, self.trainer, old_hunt)
      await interaction.response.edit_message(embed=resumed_battle.get_embed(), view=resumed_battle)
    else:
      hunt = self.game.start_hunt(self.trainer)
      initial_turn = mm_battle.BattleTurn(self.cog, self.trainer, hunt)
      await interaction.response.edit_message(embed=initial_turn.get_embed(), view=initial_turn)