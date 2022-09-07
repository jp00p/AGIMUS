from common import *

class PoshimoView(discord.ui.View):
  """ base poshimo UI class """
  def __init__(self, cog):
    self.cog = cog
    self.game = cog.game
    self.pages = []
    self.paginator = None
    super().__init__(timeout=30)

  def get_pages(self):
    return self.pages

  def get_paginator(self):
    return self.paginator
    
  async def on_timeout(self):
    self.disable_all_items()
    #await self.message.edit(content="You took too long, sorry!", embed=None, view=self)

class StarterPages(PoshimoView):
  """ The pages for choosing a starter poshimo """
  def __init__(self, cog):
    super().__init__(cog)
    
    self.starters = self.game.starter_poshimo
    
    for s in self.starters:
      embed = discord.Embed(
        title="Choose your starter Poshimo", 
        description=f"**{s.name}**", 
        fields=[
          discord.EmbedField(name="Types", value=f"{s.types}"), 
          discord.EmbedField(name="Moves", value=f"{[m.display_name for m in s.move_list]}")]
      )
      self.pages.append(pages.Page(
        embeds=[embed]
      ))
    
    self.paginator = pages.Paginator(
      pages=self.get_pages(),
      custom_view=self
    )

  @discord.ui.button(label="Choose this one", emoji="😎", style=discord.ButtonStyle.blurple)
  async def button_callback(self, button, interaction:discord.Interaction):
    page_choice = self.paginator.current_page
    logger.info(self.paginator)
    await interaction.response.send_message(content=f"You chose page {page_choice}")
    await interaction.delete_original_message()