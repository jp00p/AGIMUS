from common import *
from .game import PoshimoGame
from .objects import PoshimoTrainer
import pocket_shimodae.utils as utils
from typing import List

NBSP = "⠀"
SPACER = NBSP*40

def fill_embed_text(text:str):
  return text.ljust(50, NBSP)


class PoshimoView(discord.ui.View):
  ''' basic discord.ui.View with a few extras (game and trainer objects mostly) '''
  def __init__(self, cog:discord.Cog, trainer:PoshimoTrainer=None):
    super().__init__(
      timeout=30.0,
      disable_on_timeout=True
    )
    self.cog = cog
    self.trainer:PoshimoTrainer = trainer
    if not isinstance(self.trainer, PoshimoTrainer):
      self.trainer = int(self.trainer)
      if isinstance(self.trainer, int):
        if len(str(self.trainer)) < 4:
          self.trainer = utils.get_trainer(trainer_id=trainer)
        else:
          self.trainer = utils.get_trainer(discord_id=trainer)
    self.game:PoshimoGame = cog.game
    self.pages = []
    self.paginator = None
    self.message = None
    self.embeds = None

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

  async def on_timeout(self) -> None:
    self.clear_items()
    self.add_item(discord.Embed(title="Expired", description="This is an old message. Try the command again!"))
    

  def generate_battle_logs(self) -> str:
    description = ""
    if self.battle.logs:
      for log in self.battle.logs[self.battle.current_turn]:
        if log['log_entry']:
          description += log['log_entry']+'\n'
    return description
    
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

class PoshimoSelect(discord.ui.Select):
  """ base poshimo select menu """
  def __init__(self, cog, placeholder, items:List[discord.SelectOption], min_values=1, max_values=1):
    self.cog = cog
    self.game:PoshimoGame = cog.game
    self.items = items
    self.placeholder = placeholder
    self.min_values = min_values
    self.max_values = max_values
    super().__init__(
      placeholder=self.placeholder,
      min_values=self.min_values,
      max_values=self.max_values,
      options=self.items
    )
    
  async def callback(self, interaction):
    pass


class PoshimoPaginator(pages.Paginator):
  def __init__(
    self, cog, trainer,
    pages, show_menu, custom_view,
    show_disabled, loop_pages, show_indicator,
    use_default_buttons, custom_buttons, menu_placeholder
  ):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      pages=pages,
      show_menu=show_menu,
      custom_view=custom_view,
      show_disabled=show_disabled,
      loop_pages=loop_pages,
      show_indicator=show_indicator,
      use_default_buttons=use_default_buttons,
      custom_buttons=custom_buttons,
      menu_placeholder=menu_placeholder,
    )

class BackButton(discord.ui.Button):
  ''' a back button that edits the message in place with whatever view you pass it '''
  def __init__(self, next_view:PoshimoView, **kwargs):
    self.next_view:PoshimoView = next_view
    super().__init__(emoji="🔙", row=4, **kwargs)  
  async def callback(self, interaction:discord.Interaction):
    view = self.next_view
    await interaction.response.edit_message(view=view, embed=view.get_embed())