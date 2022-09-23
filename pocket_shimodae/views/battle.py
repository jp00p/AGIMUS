from common import *
from typing import List
from ..ui import PoshimoView, Confirmation
from ..objects import Poshimo, PoshimoBattle, PoshimoTrainer, PoshimoMove

class BattleTurn(PoshimoView):
  """
  shows your active poshimo, your opponent, and possible actions
  this will get sent to a player each time its their turn  
  """

  def __init__(self, cog, battle:PoshimoBattle):
    super().__init__(cog)
    self.battle = battle
    self.you = battle.trainers[0]
    self.opponent = battle.trainers[1]

    battle_embed = discord.Embed(
      title="It's your move.",
      description="What will you do now?",
      fields=[
        discord.EmbedField( # your poshimo
          name=f"You:",
          value=f'**{self.you.active_poshimo}**\nHP: {self.you.active_poshimo.hp}/{self.you.active_poshimo.max_hp}',
          inline=True,
        ),
        discord.EmbedField( # their poshimo
          name=f"Opponent:",
          value=f'**{self.opponent.active_poshimo}**\nHP: {self.opponent.active_poshimo.hp}/{self.opponent.active_poshimo.max_hp}',
          inline=True
        )
      ]
    )

    self.embeds = [battle_embed]
    
    for move in self.you.active_poshimo.move_list:
      # add move buttons
      self.add_item(MoveButton(move,self.you,self.battle))

    for action in self.battle.battle_actions:
      # add action buttons
      self.add_item(ActionButton(action))

class MoveButton(discord.ui.Button):
  def __init__(self, move:PoshimoMove, you:PoshimoTrainer, battle:PoshimoBattle, *args, **kwargs):
    self.you = you
    self.move = move
    self.battle = battle
    #logger.info(f"Move:{self.move} {self.move.stamina} {self.move.max_stamina}")
    super().__init__(
      label=f"{self.move.display_name} {self.move.stamina}/{self.move.max_stamina}", 
      row=1, 
      style=discord.ButtonStyle.primary, 
      disabled=self.move.stamina <= 0,
      *args, 
      **kwargs
    )

  async def callback(self, interaction:discord.Interaction):
    """ reduce this move's stamina by one and add the move to the queue! """
    temp_list:List[PoshimoMove] = self.you.active_poshimo.move_list
    move_in_list:int = temp_list.index(self.move)
    temp_list[move_in_list].stamina -= 1
    self.battle.enqueue_move(self.move, self.you)
    self.you.active_poshimo.move_list = temp_list # update stamina
    await interaction.response.send_message(content=f"Nice, you clicked {self.label}", ephemeral=True)

class ActionButton(discord.ui.Button):
  def __init__(self, action:str, *args, **kwargs):
    self.action = action
    super().__init__(label=self.action.title(), row=2, style=discord.ButtonStyle.blurple, *args, **kwargs)
  
  async def callback(self, interaction:discord.Interaction):
    await interaction.response.send_message(content=f"Nice, you clicked {self.action}")

class InventoryScreen(PoshimoView):
  pass

class SwapMenu(discord.SelectMenu):
  ''' menu for swapping your active poshimo '''
  pass

class BattleResults(BattleTurn):
  ''' results of a turn '''
  def __init__(self):
    super().__init__(self.cog, self.battle)