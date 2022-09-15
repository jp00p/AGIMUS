from logging import PlaceHolder
from common import *
from ..ui import PoshimoView, Confirmation

class ManageMenu(discord.ui.Select):
  def __init__(self, cog, items):
    self.cog = cog
    options = []
    for item in items:
      options.append(discord.SelectOption(
        label=f"{item.display_name}",
        value=f"{item.id}"
      ))
    super().__init__(
      placeholder="Select the Poshimo to manage",
      options=options
    )
  async def callback(self, interaction):
    pass

class ManageScreen(PoshimoView):
  """ start of /ps manage command """
  def __init__(self, cog, discord_id):
    super().__init__(cog)
    self.discord_id = discord_id
    self.trainer = self.game.get_trainer(self.discord_id)
    self.embeds = [
      discord.Embed(title="Manage your Poshimo", description="Swap, rename, release, or just examine your Poshimo.")
    ]
    self.add_item(ManageMenu(cog, self.trainer.list_all_poshimo()))