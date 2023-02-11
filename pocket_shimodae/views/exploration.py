from common import *
from ..ui import *
from . import main_menu as mm
from ..objects import ExplorationMinigame

DIRECTIONS = {
  "up" : "⬆",
  "down" : "⬇",
  "left" : "⬅",
  "right" : "➡"
}

class ExploreMenu(PoshimoView):
  def __init__(self, cog, trainer, minigame=None):
    super().__init__(cog, trainer)
    
    if not minigame:
      self.minigame = ExplorationMinigame()
    else:
      self.minigame = minigame
    
    self.embeds = [
      discord.Embed(
        title="Explore!",
        description="The view:\n" + self.minigame.map_string
      )
    ]

    self.add_item(discord.ui.Button(label=NBSP, row=1, disabled=True))
    self.add_item(DirectionButton(self.cog, self.trainer, self.minigame, dir="up", row=1))
    self.add_item(discord.ui.Button(label=NBSP, row=1, disabled=True))

    self.add_item(DirectionButton(self.cog, self.trainer, self.minigame, dir="left", row=2))
    self.add_item(discord.ui.Button(label=NBSP, row=2, disabled=True))
    self.add_item(DirectionButton(self.cog, self.trainer, self.minigame, dir="right", row=2))

    self.add_item(discord.ui.Button(label=NBSP, row=3, disabled=True))
    self.add_item(DirectionButton(self.cog, self.trainer, self.minigame, dir="down", row=3))
    self.add_item(discord.ui.Button(label=NBSP, row=3, disabled=True))
  

class DirectionButton(discord.ui.Button):
  def __init__(self, cog, trainer, minigame, dir="", **kwargs):
    self.cog = cog
    self.trainer = trainer
    self.minigame = minigame
    self.dir = dir
    super().__init__(
      label=DIRECTIONS[dir],
      **kwargs
    )
  async def callback(self, interaction):
    self.minigame.move(self.dir)
    view = ExploreMenu(self.cog, self.trainer, self.minigame)
    await interaction.response.edit_message(content=self.minigame.show_whole_map())