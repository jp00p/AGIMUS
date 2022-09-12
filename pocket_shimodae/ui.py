from common import *
from .game import PoshimoGame

class PoshimoView(discord.ui.View):
  """ base view boilerplate """
  def __init__(self:discord.ui.View, cog:discord.Cog):
    self.cog = cog
    self.game:PoshimoGame = cog.game
    self.pages = []
    self.paginator = None
    self.message = None
    self.embeds = None
    super().__init__()

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