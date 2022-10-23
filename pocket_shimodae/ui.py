from typing import List
from common import *
import pocket_shimodae.utils as utils
from .game import PoshimoGame
from .objects import PoshimoTrainer, TrainerStatus

NBSP = "⠀"
SPACER = NBSP*40
BACK_TO_MAIN_MENU = "Main menu"

def fill_embed_text(text:str):
  ''' padd out the embed text so it's not a tiny embed '''
  return text.ljust(50, NBSP)

class PoshimoView(discord.ui.View):
  ''' basic discord.ui.View with a few extras (game and trainer objects mostly) '''
  def __init__(self, cog:discord.Cog, trainer:PoshimoTrainer=None, previous_view:discord.ui.View=None, **kwargs):
    super().__init__(**kwargs)
    self.cog = cog
    self.previous_view:discord.ui.View = previous_view
    self.trainer:PoshimoTrainer = trainer
    if self.trainer and not isinstance(self.trainer, PoshimoTrainer):
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

  def generate_battle_logs(self) -> str:
    description = ""
    if self.battle.logs:
      for log in self.battle.logs[self.battle.current_turn]:
        if log['log_entry']:
          description += log['log_entry']+'\n'
    return description
    
class Confirmation(PoshimoView):
  """ base confirmation boilerplate, for a simple yes or no question """
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
  """ 
  a select menu that lists the trainers poshimo 
  has a lil helper to pass the Poshimo object around
  """
  def __init__(self, cog, trainer, away_poshimo=False, custom_placeholder=None, **kwargs):
    self.cog = cog
    self.trainer:PoshimoTrainer = trainer
    disabled = False
    self.selected_poshimo = None
    self.poshimo_list = []

    if away_poshimo:
      self.poshimo_list = self.trainer.away_poshimo
    else:
      self.poshimo_list = self.trainer.list_all_poshimo()
    
    logger.info(self.poshimo_list)
    placeholder = "Select a Poshimo"
    if custom_placeholder:
      placeholder = custom_placeholder
    
    option_list = []
    if not self.poshimo_list:
      placeholder = "No Poshimo available!"
      disabled = True
      option_list = [discord.SelectOption(label=f"No Poshimo", value="NULL")]
    else:
      option_list = [
        discord.SelectOption(
          label=f"{p.display_name}",
          value=f"{key}"
        ) 
        for key,p in enumerate(self.poshimo_list)
      ]
    super().__init__(
      placeholder=placeholder,
      min_values=1,
      max_values=1,
      options=option_list,
      disabled=disabled,
      **kwargs
    )
  
  def get_selected_poshimo(self):
    self.selected_poshimo = self.poshimo_list[int(self.values[0])]

  async def callback(self, interaction:discord.Interaction):
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
  def __init__(self, next_view:PoshimoView, emoji="🔙", row=4, **kwargs):
    self.next_view:PoshimoView = next_view
    super().__init__(
      emoji=emoji, 
      row=row, 
      **kwargs
    )
  async def callback(self, interaction:discord.Interaction):
    view = self.next_view
    await interaction.response.edit_message(view=view, embed=view.get_embed())

def progress_bar(progress:float, ansi=False):
  ''' 
  returns a string of a progress bar, made with emojis 

  pass a float between 0.0 and 1.0
  '''
  

  filled = "◽"
  empty  = "◾"
  num_bricks = 10
  filled_num = round(progress * num_bricks)
  empty_num = num_bricks - filled_num
  progress_str = filled * filled_num
  progress_str += empty * empty_num

  ansi_filled = f"{Back.RED} {Back.RESET}"
  ansi_empty = f"{Back.BLACK} {Back.RESET}"
  ansi_progress_str = ansi_filled * filled_num
  ansi_progress_str += ansi_empty * empty_num 
  if ansi:
    return ansi_progress_str
  return progress_str