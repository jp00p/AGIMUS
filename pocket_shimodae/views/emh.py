from common import *
from ..ui import *
from . import main_menu as mm

class SummonEMH(PoshimoView):
  # EMH appears
  # choices: Heal one, heal all
  def __init__(self, cog, trainer):
    super().__init__(cog, trainer)

    self.embeds = [
      discord.Embed(
        title="The EMH appears before you",
        description="\"Please state the nature of the holo-emergency.\""
      )
    ]
    
    self.add_item(HealOneButton(self.cog, self.trainer))
    self.add_item(HealAllButton(self.cog, self.trainer))
    self.add_item(mm.BackToMainMenu(self.cog, self.trainer))

class HealOneButton(discord.ui.Button):
  def __init__(self, cog, trainer):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      label="Heal one Poshimo",
      emoji="🩹"
    )
  async def callback(self, interaction:discord.Interaction):
    view = self.view
    view.add_item(PoshimoSelect(self.cog, self.trainer, custom_placeholder="Choose a Poshimo to heal"))

class HealAllButton(discord.ui.Button):
  def __init__(self, cog, trainer):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      label="Heal all Poshimo (123🧣)",
      emoji="💊"
    )
  async def callback(self, interaction:discord.Interaction):
    pass