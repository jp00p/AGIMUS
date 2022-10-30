from common import *
from ..ui import *
from . import main_menu as mm

class InventoryMenu(PoshimoView):
  ''' the view for your inventory '''
  def __init__(self, cog, trainer, using_item=None):
    super().__init__(cog, trainer)

    self.using_item = using_item
    self.inventory = self.trainer.list_inventory()

    self.embeds = [
      discord.Embed(
        title=f"{self.trainer}'s inventory",
        description=f"{fill_embed_text('Here are your items YOUR MAJESTY')}\n{build_inventory_tables(self.inventory)}"
      )
    ]
    
    if not using_item:
      self.add_item(mm.BackToMainMenu(self.cog, self.trainer))
    
    if len(self.trainer.inventory) > 0:
      self.add_item(ItemUseMenu(self.cog, self.trainer, selected_item=self.using_item))



class ItemUseMenu(discord.ui.Select):
  ''' 
  the selectmenu that lists your items
  '''
  #TODO: items that affect the whole party
  #TODO: replace with a global selectmenu
  def __init__(self, cog, trainer:PoshimoTrainer, selected_item:str=None, **kwargs):
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
