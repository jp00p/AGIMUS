from common import *

from ..objects import PoshimoTrainer, TrainerStatus
from ..ui import *
from .battle import *
from .fishing import *
from .manage import *
from .inventory import *
from .missions import *
from .shop import *
from .travel import *

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
          discord.EmbedField(name="Belt buckles", value=f"{self.trainer.buckles}", inline=True),
          discord.EmbedField(name="Active Poshimo", value=f"{self.trainer.active_poshimo}", inline=False),
          discord.EmbedField(name="Poshimo sac", value=f"{self.trainer.list_sac()}", inline=False)
        ]
      )
    ]
    self.add_item(ManageMenuButton(self.cog, self.trainer, row=1))
    self.add_item(FishingMenuButton(self.cog, self.trainer, row=1))
    self.add_item(InventoryMenuButton(self.cog, self.trainer, row=1))
      

    self.add_item(TravelMenuButton(self.cog, self.trainer, row=2))
    self.add_item(ShopMenuButton(self.cog, self.trainer, self.trainer_location, row=2))
    self.add_item(CraftingMenuButton(self.cog, self.trainer, row=2))
    self.add_item(InnMenuButton(self.cog, self.trainer, row=2))

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
      **kwargs
    )
  async def callback(self, interaction):
    view = FishingLog(self.cog, self.trainer)
    view.add_item(BackToMainMenu(self.cog, self.trainer))
    
    await interaction.response.edit_message(view=view, embed=view.get_embed())

class InventoryMenuButton(discord.ui.Button):
  ''' the button to open the inventory menu '''
  def __init__(self, cog, trainer, **kwargs):
    self.trainer = trainer
    self.cog = cog
    super().__init__(
      label="Inventory",
      emoji="💼",
      **kwargs
    )
  async def callback(self, interaction):
    view = InventoryMenu(self.cog, self.trainer)
    await interaction.response.edit_message(view=view, embed=view.get_embed())

class ManageMenuButton(discord.ui.Button):
  def __init__(self, cog, trainer, **kwargs):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      label="Manage Poshimo",
      emoji="🔧",
      **kwargs
    )
  async def callback(self, interaction:discord.Interaction):
    view = ManageStart(self.cog, self.trainer)
    view.add_item(BackToMainMenu(self.cog, self.trainer))
    await interaction.response.edit_message(view=view, embed=view.get_embed())

class TravelMenuButton(discord.ui.Button):
  def __init__(self, cog, trainer, **kwargs):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      label="Travel",
      emoji="✈",
      **kwargs
    )
  async def callback(self, interaction:discord.Interaction):
    view = TravelMenu(self.cog, self.trainer)
    view.add_item(BackToMainMenu(self.cog, self.trainer))
    await interaction.response.edit_message(view=view, embed=view.get_embed())

class CraftingMenuButton(discord.ui.Button):
  def __init__(self, cog, trainer, **kwargs):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      label="Crafting",
      emoji="🔨",
      **kwargs
    )
  async def callback(self, interaction:discord.Interaction):
    pass

class ShopMenuButton(discord.ui.Button):
  def __init__(self, cog, trainer, location, **kwargs):
    self.cog = cog
    self.trainer = trainer
    self.location = location
    super().__init__(
      label="Shopping",
      emoji="🛒",
      disabled=bool(self.location.shop is None),
      **kwargs
    )
  async def callback(self, interaction:discord.Interaction):
    view = ShoppingScreen(self.cog, self.trainer, self.location.shop)
    view.add_item(BackToMainMenu(self.cog, self.trainer))
    view.add_item(ShopBuyMenu(self.cog, self.trainer, self.location.shop))
    if len(self.trainer.inventory) > 0:
      view.add_item(ShopSellMenu(self.cog, self.trainer, self.location.shop))
    await interaction.response.edit_message(view=view, embed=view.get_embed())

class QuestMenuButton(discord.ui.Button):
  def __init__(self, cog, trainer, **kwargs):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      label="Quests",
      emoji="💎",
      **kwargs
    )
  async def callback(self, interaction:discord.Interaction):
    view = ManageAwayMissions(self.cog, self.trainer)
    view.add_item(BackToMainMenu(self.cog, self.trainer))
    await interaction.response.edit_message(view=view, embed=view.get_embed())

class InnMenuButton(discord.ui.Button):
  def __init__(self, cog, trainer, **kwargs):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      label="Call EMH",
      emoji="🩺",
      **kwargs
    )
  async def callback(self, interaction:discord.Interaction):
    pass

class DuelMenuButton(discord.ui.Button):
  def __init__(self, cog, trainer, **kwargs):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      label="Duel",
      emoji="⚔",
      **kwargs
    )
  async def callback(self, interaction:discord.Interaction):
    pass

class HuntMenuButton(discord.ui.Button):
  def __init__(self, cog, trainer:PoshimoTrainer, **kwargs):
    self.cog = cog
    self.trainer = trainer
    disabled = False
    if self.trainer.status is TrainerStatus.BATTLING:
      label = "Resume your hunt"
      emoji = "⏯"
    else:
      label = "Start a hunt"
      emoji = "🏹"
    
    if self.trainer.active_poshimo.hp <= 0:
      disabled = True
      emoji = "❌"

    super().__init__(
      label=label,
      emoji=emoji,
      disabled=disabled,
      **kwargs
    )
  async def callback(self, interaction:discord.Interaction):
    pass
