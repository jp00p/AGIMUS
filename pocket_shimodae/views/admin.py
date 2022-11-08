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
    self.add_item(AlterPoshimoButton(self.trainer))


    # buttons:
    # reset DB
    # add poshimo
    # add item
    # add scarves
    # unlock location
    # alter poshimo (hp, xp, etc)
    # run queries


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
    await interaction.response.send_message("Database cleared!", ephemeral=True)

class AddPoshimoButton(discord.ui.Button):
  def __init__(self, game:PoshimoGame, trainer:PoshimoTrainer):
    self.game = game
    self.trainer = trainer
    super().__init__(
      label="Add random Poshimo"
    )
  async def callback(self, interaction: discord.Interaction):
    new_poshimo = self.game.admin_give_random_poshimo(self.trainer)
    await interaction.response.send_message(f"Added {new_poshimo} to your sac!", ephemeral=True)

class AlterPoshimoButton(discord.ui.Button):
  def __init__(self, trainer):
    self.trainer = trainer
    super().__init__(
      label="Alter a Poshimo"
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
      await interaction.response.send_message(f"Invalid value: {self.children[0].value} ")
    else:
      qty = int(self.children[0].value)
      self.trainer.scarves += qty
      await interaction.response.send_message(f"Added {qty} scarves! You now have {self.trainer.scarves} scarves.")

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

