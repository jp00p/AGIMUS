from common import *

class PoshimoView(discord.ui.View):
  """ base poshimo UI class """
  def __init__(self, cog):
    self.cog = cog
    self.game = cog.game
    self.pages = []
    super().__init__(timeout=30)

  def get_pages(self):
    return self.pages

  def get_paginator(self):
    return pages.Paginator(
      pages=self.get_pages(),
      custom_view=self
    )
  async def on_timeout(self):
    self.disable_all_items()
    await self.message.edit(content="You took too long, sorry!", embed=None, view=self)

class StarterPages(PoshimoView):
  """ The pages for choosing a starter poshimo """
  def __init__(self, cog):
    super().__init__(cog, timeout=30)
    self.starters = self.game.starter_poshimo
    
    for s in self.starters:
      embed = discord.Embed(
        title="Choose your starter Poshimo", 
        description=f"**{s.name}**", 
        fields=[
          discord.EmbedField(name="Types", value=f"{s.types}"), 
          discord.EmbedField(name="Moves", value=f"{[m.display_name for m in s.move_list]}")]
      )
      self.pages.append(pages.Page(embeds=[embed]))
  
  @discord.ui.button(label="Choose this one", emoji="😎", style=discord.ButtonStyle.blurple)
  async def button_callback(self, button, interaction):
    await interaction.response.send_message("You clicked me!!!", view=self)