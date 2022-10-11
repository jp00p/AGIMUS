from select import select
from common import *
from ..ui import *
from ..views import *
from ..objects import PoshimoTrainer, TrainerStatus
from pocket_shimodae import views

BACK_TO_MAIN_MENU = "Back to main menu"

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
    self.add_item(ShopMenuButton(self.cog, self.trainer, row=2))
    self.add_item(InnMenuButton(self.cog, self.trainer, row=2))

    self.add_item(QuestMenuButton(self.cog, self.trainer, row=3))
    self.add_item(HuntMenuButton(self.cog, self.trainer, row=3))
    self.add_item(DuelMenuButton(self.cog, self.trainer, row=3))

class InventoryMenu(PoshimoView):
  ''' the view for your inventory '''
  def __init__(self, cog, trainer, using_item=None):
    super().__init__(cog, trainer)

    self.using_item = using_item
    self.embeds = [
      discord.Embed(
        title=f"{self.trainer}'s inventory",
        description=f"{fill_embed_text(self.trainer.list_inventory())}"
      )
    ]
    
    if not using_item:
      self.add_item(BackButton(MainMenu(self.cog, trainer=self.trainer), label=BACK_TO_MAIN_MENU))
    
    if len(self.trainer.inventory) > 0:
      self.add_item(ItemUseMenu(self.cog, self.trainer, selected_item=self.using_item))


class ItemUseMenu(discord.ui.Select):
  ''' 
  the selectmenu that lists your items
  this is where the item gets selected
  '''
  #TODO: items that affect the whole party
  def __init__(self, cog, trainer, selected_item:str=None, **kwargs):
    self.cog = cog
    self.trainer = trainer
    self.selected_item = selected_item
    logger.info(selected_item)
    options = []
    for id in self.trainer.inventory.keys():
      id = str(id)
      
      if selected_item and self.selected_item == id:
        options.append(
          discord.SelectOption(
            label=id.title(), value=id,
            default=True
          )
        )
      else:
        options.append(
          discord.SelectOption(
            label=id.title(), value=id
          )
        )
    super().__init__(
      placeholder="Select an item to use",
      options=options,
      row=0,
      disabled=bool(self.selected_item),
      **kwargs
    )
  async def callback(self, interaction:discord.Interaction):
    selected_item = self.values[0]
    view = InventoryMenu(self.cog, self.trainer, selected_item)
    view.add_item(BackButton(InventoryMenu(self.cog, self.trainer, None), label="Cancel"))
    self.disabled = True
    view.add_item(PoshimoSelectMenu(self.cog, self.trainer, selected_item))
    await interaction.response.edit_message(view=view, embed=view.get_embed())
    

class PoshimoSelectMenu(discord.ui.Select):
  ''' 
  selectmenu to choose a poshimo to use a item on 
  this is when the item actually gets used
  '''
  def __init__(self, cog, trainer:PoshimoTrainer, item:str):
    self.cog = cog
    self.trainer = trainer
    self.poshimo_choices = self.trainer.list_all_poshimo()
    self.item_choice = self.trainer.inventory[item]["item"]
    options = []
    for id,poshimo in enumerate(self.poshimo_choices):
      options.append(discord.SelectOption(
        label=f"{poshimo.display_name}",
        value=f"{id}"
      ))
    super().__init__(
      placeholder=f"Choose which Poshimo to use this {self.item_choice} on",
      options=options,
      row=1
    )
  async def callback(self, interaction:discord.Interaction):
    selected_poshimo = self.poshimo_choices[int(self.values[0])]
    results = self.trainer.use_item(self.item_choice, selected_poshimo)
    view = InventoryMenu(self.cog, self.trainer)
    view.embeds.append(
      discord.Embed(
        title="Item results",
        description=f"{results}"
      )
    )
    await interaction.response.edit_message(view=view, embeds=view.get_embeds())

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
    view = views.FishingLog(self.cog, self.trainer)
    view.add_item(BackButton(MainMenu(self.cog, self.trainer), label=BACK_TO_MAIN_MENU))
    
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
    view = views.ManageStart(self.cog, self.trainer)
    view.add_item(BackButton(MainMenu(self.cog, self.trainer), label=BACK_TO_MAIN_MENU))
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
    view = views.TravelMenu(self.cog, self.trainer)
    view.add_item(BackButton(MainMenu(self.cog, self.trainer), label=BACK_TO_MAIN_MENU))
    await interaction.response.edit_message(view=view, embed=view.get_embed())

class ShopMenuButton(discord.ui.Button):
  def __init__(self, cog, trainer, **kwargs):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      label="Shopping",
      emoji="🛒",
      **kwargs
    )
  async def callback(self, interaction:discord.Interaction):
    pass

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
    pass

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