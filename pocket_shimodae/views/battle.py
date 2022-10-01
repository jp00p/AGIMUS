from common import *
from typing import List
from ..ui import PoshimoView, Confirmation
from ..objects import Poshimo, PoshimoBattle, BattleTypes, BattleStates, PoshimoTrainer, PoshimoMove

spacer = f"\n{'⠀'*53}" # fills out the embed to max width

class ActionScreen(PoshimoView):
  def __init__(self, cog, action:str, trainer:PoshimoTrainer, battle:PoshimoBattle):
    super().__init__(cog)

class BattleTurn(PoshimoView):
  """
  A view of a turn of battle
  ----
  shows your active poshimo, your opponent, and possible actions

  this will get sent to a player each time its their turn, basically the start of each round of battle

  ...if i can make it work gewd
  """

  def __init__(self, cog, battle:PoshimoBattle):
    super().__init__(cog)
    
    self.battle = battle
    self.you = battle.trainers[0]
    self.opponent = battle.trainers[1]
    self.embeds = []
    battle_embed = None
    default_battle_fields = [
      discord.EmbedField( # your poshimo
        name=f"{self.you.active_poshimo}",
        value=f'(Your Poshimo)\nHP: {self.you.active_poshimo.hp}/{self.you.active_poshimo.max_hp}',
        inline=True,
      ),
      discord.EmbedField(
        name="🆚",
        value="⠀",
        inline=True
      ),
      discord.EmbedField( # their poshimo
        name=f"{self.opponent.active_poshimo}",
        value=f'(Wild Poshimo)\nHP: {self.opponent.active_poshimo.hp}/{self.opponent.active_poshimo.max_hp}',
        inline=True
      )
    ]
    
    

    if self.battle.battle_type is BattleTypes.HUNT:
      if self.battle.state is BattleStates.ACTIVE:
        
        if self.battle.current_turn == 0:
          # FIRST ROUND OF HUNT
          battle_embed = discord.Embed(
            title="Let the hunt begin!",
            description=f"You encounter a wild {self.opponent.active_poshimo}!",
            fields=default_battle_fields
          )

        if self.battle.current_turn > 0:
          # SUBSEQUENT ROUNDS OF HUNT
          description = self.generate_battle_logs()
          
          battle_embed = discord.Embed(
            title=f"Round {self.battle.current_turn}:",
            description=description,
            fields=default_battle_fields
          )
          battle_embed.set_footer(text="Choose your next move wisely")

      if self.battle.state is BattleStates.FINISHED:
        # HUNT IS OVER
        description = self.generate_battle_logs()
        battle_embed = discord.Embed(
          title=f"The hunt is over!",
          description=description,
          fields=default_battle_fields
        )
        battle_embed.set_footer(text="Wow finally.")

    # HUNT OVER EMBED
    
    # ---- end of custom embeds ---- #
    battle_embed.description += spacer
    self.embeds = [battle_embed]
    
    if self.battle.state is BattleStates.ACTIVE:
      stamina_count = 0
      for move in self.you.active_poshimo.move_list:
        # add move buttons
        self.add_item(MoveButton(self.cog, move, self.you, self.battle))
        stamina_count += move.stamina
      
      if stamina_count == 0:
        # if they are out of moves, they can always struggle
        self.add_item(MoveButton(self.cog, PoshimoMove("struggle"), self.you, self.battle))

      for action in self.battle.battle_actions:
        # add action buttons
        self.add_item(ActionButton(action, self.you, self.battle))

class MoveButton(discord.ui.Button):
  ''' 
  Poshimo move button!
  ----
  This will enqueue a move for battle, or will be disabled if you're out of stamina
  '''
  def __init__(self, cog, move:PoshimoMove, you:PoshimoTrainer, battle:PoshimoBattle, *args, **kwargs):
    self.cog = cog
    self.you = you
    self.move = move
    self.battle = battle
    button_label = self.move.button_label()

    super().__init__(
      label=button_label, 
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
    next_view = BattleTurn(self.cog, battle=self.battle)
    content = ""
    #logger.info(self.battle.logs[self.battle.current_turn])
    
    await interaction.response.edit_message(content=content, view=next_view, embed=next_view.get_embed())

class ActionButton(discord.ui.Button):
  '''
  Poshimo action button!
  ----
  This will queue up an action in battle instead of a move during your turn
  '''
  def __init__(self, action:str, you:PoshimoTrainer, battle:PoshimoBattle, *args, **kwargs):
    self.action = action
    self.you = you
    self.battle = battle
    super().__init__(
      label=self.action.title(), 
      row=2, 
      style=discord.ButtonStyle.blurple, 
      *args, 
      **kwargs
    )
  
  async def callback(self, interaction:discord.Interaction):
    error = action_not_possible(self.action, self.battle, self.you)
    if error:
      await interaction.response.send_message(content=f"Oops: {error}")
    else:
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

def action_not_possible(action:str, battle:PoshimoBattle, trainer:PoshimoTrainer):
  if action == "flee":
    if not battle._can_flee:
      return "You can't flee this battle!"
  if action == "item":
    if not trainer.inventory:
      return "You have no items!"
  if action == "snatch":
    return "You can't snatch ...yet"
  if action == "swap":
    return "You can't swap ...yet"
  return False