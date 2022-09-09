from common import *

class PoshimoView(discord.ui.View):
  """ base view boilerplate """
  def __init__(self, cog):
    self.cog = cog
    self.game = cog.game
    self.pages = []
    self.paginator = None
    self.message = None
    self.embeds = None
    super().__init__(timeout=30)

  def get_pages(self):
    return self.pages

  def get_paginator(self):
    return self.paginator

  def get_embed(self):
    """ just get one embed """
    return self.embeds[0]

  def get_embeds(self):
    """ get all the embeds! """
    return self.embeds
    
  async def on_timeout(self):
    self.disable_all_items()


class Confirmation(PoshimoView):
  """ base confirmation boilerplate """
  def __init__(self, cog, choice=None):
    self.choice = choice
    super().__init__(cog)

  @discord.ui.button(label="Cancel", emoji="👎", style=discord.ButtonStyle.danger, row=2)
  async def cancel_button(self, button, interaction):
    await self.cancel_callback(button, interaction)

  @discord.ui.button(label="Confirm", emoji="👍", style=discord.ButtonStyle.green, row=2)  
  async def confirm_button(self, button, interaction):
    await self.confirm_callback(button, interaction)

  async def cancel_callback(self, button, interaction):
    """ what happens when they click the cancel button """
    pass
  async def confirm_callback(self, button, interaction):
    """ what happens when they click the confirm button """
    pass