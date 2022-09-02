from common import *
from .game import PoshimoGame

class poshimoView:
  """ base poshimo UI class """
  def __init__(self, game:PoshimoGame):
    self.view = None
    self.pages = None
  def get_view(self) -> discord.ui.View:
    return self.view
  def get_pages(self) -> list:
    return self.pages

class StarterPages(poshimoView):
  """ The pages for choosing a starter pokemon """
  def __init__(self, game):
    super().__init__(game)
    self.starters = game.starter_poshimo
    self.pages = []
    for s in self.starters:
      embed = discord.Embed(title="Choose your starter Poshimo", description=f"**{s.name}**", fields=[discord.EmbedField(name="Types", value=f"{s.types}"), discord.EmbedField(name="Moves", value=f"{s.move_list}")])
      self.pages.append(pages.Page(embeds=[embed]))
    self.view = discord.ui.View(
      discord.ui.Button(label="Choose this one", row=1)
    )
  
  