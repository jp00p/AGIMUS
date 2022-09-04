from common import *
from .buttons import PoshimoButton

class PoshimoView:
  """ base poshimo UI class """
  def __init__(self, cog):
    self.cog = cog
    self.game = cog.game
    self.view = discord.ui.View
    self.pages = list
    self.paginator = pages.Paginator
  def get_view(self) -> discord.ui.View:
    return self.view
  def get_pages(self) -> list:
    return self.pages
  def get_paginator(self) -> pages.Paginator:
    return self.paginator
  def add_button(self) -> None:
    pass

class StarterPages(PoshimoView):
  """ The pages for choosing a starter pokemon """
  def __init__(self, cog):
    super().__init__(cog) 
    self.starters = self.game.starter_poshimo
    self.pages = []
    
    for s in self.starters:
      embed = discord.Embed(title="Choose your starter Poshimo", description=f"**{s.name}**", fields=[discord.EmbedField(name="Types", value=f"{s.types}"), discord.EmbedField(name="Moves", value=f"{s.move_list}")])
      self.pages.append(pages.Page(embeds=[embed]))
    
    starter_button = PoshimoButton(self.cog, "Choose this one", callback_func="pick_starter")

    self.view = discord.ui.View(
      starter_button
    )

    self.paginator = pages.Paginator(
      pages=self.get_pages(),
      show_disabled=False,
      loop_pages=True,
      disable_on_timeout=True,
      timeout=60,
      custom_view=self.get_view()
    )
    self.paginator.remove_button("first")
    self.paginator.remove_button("last")