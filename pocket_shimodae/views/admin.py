from common import *
from ..ui import *
from ..objects.poshimo import Poshimo
from ..objects.world.item import item_data

class AdminMenu(PoshimoView):
  ''' the admin menu '''
  def __init__(self, cog, trainer):
    super().__init__(cog, trainer)
    self.embeds = [
      discord.Embed(
        title=f"ADMIN MENU",
        description=fill_embed_text("Top secret"),
      )
    ]
    self.add_item(AddPoshimoButton(self.game, self.trainer))
    self.add_item(ResetButton(self.game))
    self.add_item(AddItemButton(self.trainer))
    self.add_item(AddScarvesButton(self.trainer))
    self.add_item(AddRecipeButton(self.trainer))
    self.add_item(UnlockLocsButton(self.trainer))
    self.add_item(AlterPoshimoButton(self.trainer))

class ResetButton(discord.ui.Button):
  def __init__(self, game:PoshimoGame):
    self.game = game
    super().__init__(
      label="Reset DB",
      style=discord.ButtonStyle.danger,
      row=4
    )
  async def callback(self, interaction: discord.Interaction):
    self.game.admin_clear_db()
    who = interaction.user.display_name
    await interaction.response.send_message(f"Poshimo database cleared by {who}", ephemeral=False)

class UnlockLocsButton(discord.ui.Button):
  def __init__(self, trainer:PoshimoTrainer):
    self.trainer = trainer
    super().__init__(
      label="Unlock location"
    )
  async def callback(self, interaction: discord.Interaction):
    await interaction.response.send_modal(LocationModal(self.trainer))

class LocationModal(discord.ui.Modal):
  def __init__(self, trainer):
    self.trainer:PoshimoTrainer = trainer
    super().__init__(
      title="Unlock a location"
    )
    self.add_item(discord.ui.InputText(label="Location name"))
  async def callback(self, interaction: discord.Interaction):
    loc = self.children[0].value
    self.trainer.unlock_location(loc)
    await interaction.response.send_message(f"Unlocked {loc.title()} - if you typed it correctly...")


class AddPoshimoButton(discord.ui.Button):
  def __init__(self, game:PoshimoGame, trainer:PoshimoTrainer):
    self.game = game
    self.trainer = trainer
    super().__init__(
      label="Add random Poshimo",
      row=3
    )
  async def callback(self, interaction: discord.Interaction):
    new_poshimo = self.game.admin_give_random_poshimo(self.trainer)
    await interaction.response.send_message(f"Added {new_poshimo} to your sac!", ephemeral=True)

class AlterPoshimoButton(discord.ui.Button):
  def __init__(self, trainer):
    self.trainer = trainer
    super().__init__(
      label="Alter a Poshimo",
      row=3
    )
  async def callback(self, interaction: discord.Interaction):
    await interaction.response.send_modal(AlterPoshimoModal(self.trainer))

class AlterPoshimoModal(discord.ui.Modal):
  def __init__(self, trainer):
    self.trainer = trainer
    super().__init__(
      title="Alter a Poshimo"
    )
    self.add_item(discord.ui.InputText(label="Poshimo ID"))
    self.add_item(discord.ui.InputText(label="Column to update"))
    self.add_item(discord.ui.InputText(label="New value"))

  async def callback(self, interaction: discord.Interaction):
    id = self.children[0].value
    col = self.children[1].value
    value = self.children[2].value
    poshimo = Poshimo(id=int(id))
    poshimo.update(col, value)
    await interaction.response.send_message("Poshimo updated!", ephemeral=True)

class AddRecipeButton(discord.ui.Button):
  def __init__(self, trainer):
    self.trainer = trainer
    super().__init__(
      label="Add recipe"
    )
  async def callback(self, interaction: discord.Interaction):
    await interaction.response.send_modal(AddRecipeModal(self.trainer))

class AddRecipeModal(discord.ui.Modal):
  def __init__(self, trainer):
    self.trainer:PoshimoTrainer = trainer
    super().__init__(
      title="Add recipe"
    )
    self.add_item(discord.ui.InputText(label="Recipe name", value="makeshift hypospray"))
  async def callback(self, interaction: discord.Interaction):
    recipe = self.children[0].value
    self.trainer.learn_recipe(recipe)
    await interaction.response.send_message(f"Added {recipe} to the list!", ephemeral=True)

class AddScarvesButton(discord.ui.Button):
  def __init__(self, trainer):
    self.trainer = trainer
    super().__init__(
      label="Add scarves"
    )
  async def callback(self, interaction: discord.Interaction):
    await interaction.response.send_modal(AddScarvesModal(self.trainer))

class AddScarvesModal(discord.ui.Modal):
  def __init__(self, trainer):
    self.trainer:PoshimoTrainer = trainer
    super().__init__(
      title="Add scarves"
    )
    self.add_item(discord.ui.InputText(label="Scarves quantity", value="0"))
  
  async def callback(self, interaction: discord.Interaction):
    if not is_integer(self.children[0].value):
      await interaction.response.send_message(f"Invalid value: {self.children[0].value} ", ephemeral=True)
    else:
      qty = int(self.children[0].value)
      self.trainer.scarves += qty
      await interaction.response.send_message(f"Added {qty} scarves! You now have {self.trainer.scarves} scarves.", ephemeral=True)

class AddItemButton(discord.ui.Button):
  def __init__(self, trainer):
    self.trainer = trainer
    super().__init__(
      label="Add items"
    )
  async def callback(self, interaction: discord.Interaction):
    await interaction.response.send_modal(AddItemModal(self.trainer))

class AddItemModal(discord.ui.Modal):
  def __init__(self, trainer) -> None:
    super().__init__(
      title="Add items"
    )
    self.trainer:PoshimoTrainer = trainer
    self.add_item(discord.ui.InputText(label="Item name"))
    self.add_item(discord.ui.InputText(label="Quantity", value="1"))
  async def callback(self, interaction: discord.Interaction):
    item_name = self.children[0].value.lower()
    qty = int(self.children[1].value)
    if item_data.get(item_name):
      item = PoshimoItem(item_name)
      self.trainer.add_item(item, qty)
      await interaction.response.send_message(f"You got {qty} x {item_name}!", ephemeral=True)
    else:
      await interaction.response.send_message(f"That's not a valid item name ({item_name})", ephemeral=True)

