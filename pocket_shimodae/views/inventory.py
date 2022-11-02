from common import *
from ..ui import *
from . import main_menu as mm

class InventoryMenu(PoshimoView):
  ''' the view for your inventory '''
  def __init__(self, cog, trainer, category="Basic items", using_item=None):
    super().__init__(cog, trainer)

    self.using_item = using_item
    self.categories = ["Basic items", "Combat items", "Capture items", "Crafting materials", "Other"]
    self.inventory = [] 
    self.category = category
    can_use = False
    description = ""

    if self.category == "Basic items":
      self.inventory = self.trainer.list_inventory(include_use=[UseWhere.USE_ANYWHERE, UseWhere.USE_IN_FIELD])
      can_use = True
      description = "Basic items that you can use right now"
    if self.category == "Combat items":
      self.inventory = self.trainer.list_inventory(include_use=[UseWhere.USE_IN_BATTLE], exclude_type=[ItemTypes.CAPTURE])
      description = "Items that can only be used in combat"
    if self.category == "Capture items":
      self.inventory = self.trainer.list_inventory(include_type=[ItemTypes.CAPTURE])
      description = "Items that can be used to capture Poshimo"
    if self.category == "Crafting materials":
      self.inventory = self.trainer.list_inventory(include_type=[ItemTypes.CRAFTING])
      description = "Items that can be used to craft other items"
    if self.category == "Other":
      description = "Miscellaneous items"
      self.inventory = self.trainer.list_inventory(include_type=[ItemTypes.KEY, ItemTypes.NONE])
           

    if not using_item:
      self.add_item(mm.BackToMainMenu(self.cog, self.trainer))
      self.add_item(ItemCategoryMenu(self.cog, self.trainer, self.categories, self.category))
    

    if len(self.inventory) > 0:
      if can_use:
        self.add_item(ItemUseMenu(self.cog, self.trainer, self.inventory, selected_item=self.using_item))

      self.embeds = [
        discord.Embed(
          title=self.category,
          description=description,
          fields=generate_inventory_fields(self.inventory)
        )
      ]

    else:
      self.embeds = [
        discord.Embed(
          title="Crickets...",
          description=fill_embed_text("No items found!\n")
        )
      ]

class ItemCategoryMenu(discord.ui.Select):
  '''
  selectmenu for item categories
  '''
  def __init__(self, cog, trainer:PoshimoTrainer, categories, selected=None):
    self.cog = cog
    self.trainer = trainer
    self.categories = categories
    self.selected = selected
    
    options = []
    for cat in self.categories:
      options.append(discord.SelectOption(
        label=f"{cat}",
        value=f"{cat}",
        default=bool(self.selected == cat)
      ))
    super().__init__(
      placeholder="Select an item category",
      options=options
    )
  async def callback(self, interaction: discord.Interaction):
    self.selected = self.values[0]
    view = InventoryMenu(self.cog, self.trainer, category=self.selected)
    await interaction.response.edit_message(view=view, embed=view.get_embed())

class ItemUseMenu(discord.ui.Select):
  ''' 
  the selectmenu that lists your items
  '''
  #TODO: items that affect the whole party
  #TODO: replace with a global selectmenu
  def __init__(self, cog, trainer:PoshimoTrainer, inventory:List[InventoryDict], selected_item:str=None, **kwargs):
    self.cog = cog
    self.trainer = trainer
    self.selected_item = selected_item
    self.inventory = inventory
    options = []

    for item in self.inventory:
      default = False
      if item["item"].name.lower() == self.selected_item:
        default = True
      options.append(
        discord.SelectOption(
          label=item["item"].name.title(),
          value=item["item"].name.lower(),
          default=default
        )
      )
    
    super().__init__(
      placeholder="Select an item to use",
      options=options,
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
    self.poshimo_choices = self.trainer.list_all_poshimo(exclude=[PoshimoStatus.AWAY, PoshimoStatus.BATTLING])
    self.item_choice = self.trainer.inventory[item]["item"]
    disabled = False
    if len(self.poshimo_choices) > 0:
      options = []
      for id,poshimo in enumerate(self.poshimo_choices):
        options.append(discord.SelectOption(
          label=f"{poshimo.display_name}",
          value=f"{id}"
        ))
    else:
      options = [discord.SelectOption(label="No Poshimo are around right now", value="NULL")]
      disabled = True
    super().__init__(
      placeholder=f"Choose which Poshimo to use this {self.item_choice} on",
      options=options,
      disabled=disabled,
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
