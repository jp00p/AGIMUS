from typing import List

from common import *

from ..objects import (BattleStates, BattleTypes, Poshimo, PoshimoBattle,
                       PoshimoMove, PoshimoTrainer)

from ..ui import *
from . import main_menu as mm

class CancelButton(discord.ui.Button):
  def __init__(self, cog, battle=None):
    self.cog = cog
    self.battle = battle
    super().__init__(
      label="Cancel",
      style=discord.ButtonStyle.secondary,
      emoji="❌",
      row=1
    )
  async def callback(self, interaction:discord.Interaction):
    pass

class BattleTurn(PoshimoView):
  """
  A view of a turn of battle
  ----
  shows your active poshimo, your opponent, and possible actions

  this will get sent to a player each time its their turn, basically the start of each round of battle

  ...if i can make it work gewd
  """

  def __init__(self, cog, trainer, battle:PoshimoBattle, action_mode=False):
    super().__init__(cog, trainer)
    self.battle = battle
    self.you = battle.trainers[0]
    self.opponent = battle.trainers[1]
    self.embeds = []
    battle_embed = None

    your_hp_bar = (self.you.active_poshimo.hp/self.you.active_poshimo.max_hp)
    your_filled = them_filled = "🟩"
    them_hp_bar = (self.opponent.active_poshimo.hp/self.opponent.active_poshimo.max_hp)
    if your_hp_bar <= 0.3:
      your_filled = "🟥"
    if them_hp_bar <= 0.3:
      them_filled = "🟥"
    
    default_battle_fields = [
      discord.EmbedField( # your poshimo
        name=f"{self.you.active_poshimo}",
        value=f'''
        (Your Poshimo)
        HP: {self.you.active_poshimo.hp}/{self.you.active_poshimo.max_hp}
        {progress_bar(your_hp_bar, filled=your_filled)}
        ''',
        inline=True,
      ),
      discord.EmbedField(
        name="⠀\n🆚\n",
        value="⠀",
        inline=True
      ),
      discord.EmbedField( # their poshimo
        name=f"{self.opponent.active_poshimo}",
        value=f'''
        (Wild Poshimo)
        HP: {self.opponent.active_poshimo.hp}/{self.opponent.active_poshimo.max_hp}
        {progress_bar(them_hp_bar, filled=them_filled)}
        ''',
        inline=True
      )
    ]
    
    if self.battle.battle_type is BattleTypes.HUNT:
      if self.battle.state is BattleStates.ACTIVE:
        
        if self.battle.current_turn == 0:
          # FIRST ROUND OF HUNT
          battle_embed = discord.Embed(
            title="Let the hunt begin!",
            description=fill_embed_text(f"You encounter a wild {self.opponent.active_poshimo}!"),
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
          description=fill_embed_text(description),
          fields=default_battle_fields
        )
        battle_embed.set_footer(text="Wow finally.")
    
    # ---- end of custom embeds ---- #
    
    self.embeds = [battle_embed]
    
    if self.battle.state is BattleStates.ACTIVE:
      stamina_count = 0
      for move in self.you.active_poshimo.move_list:
        # add move buttons
        self.add_item(MoveButton(self.cog, move, self.you, self.battle, action_mode))
        stamina_count += move.stamina
      
      if stamina_count == 0:
        # if they are out of moves, they can always struggle
        self.add_item(MoveButton(self.cog, PoshimoMove("struggle"), self.you, self.battle, action_mode))

      for action in self.battle.battle_actions:
        # add action buttons
        self.add_item(ActionButton(action, self.cog, self.you, self.battle, action_mode))

class MoveButton(discord.ui.Button):
  ''' 
  Poshimo move button!
  ----
  This will enqueue a move for battle, or will be disabled if you're out of stamina
  '''
  def __init__(self, cog, move:PoshimoMove, you:PoshimoTrainer, battle:PoshimoBattle, action_mode=False, *args, **kwargs):
    self.cog = cog
    self.you = you
    self.move = move
    self.battle = battle
    button_label = self.move.button_label()

    super().__init__(
      label=button_label, 
      row=2, 
      style=discord.ButtonStyle.primary, 
      disabled=bool(self.move.stamina <= 0 or action_mode),
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
    next_view = BattleTurn(self.cog, self.you, battle=self.battle)
    content = ""
    #logger.info(self.battle.logs[self.battle.current_turn])
    await interaction.response.edit_message(content=content, view=next_view, embed=next_view.get_embed())

class ActionButton(discord.ui.Button):
  '''
  Poshimo action button!
  ----
  This will queue up an action in battle instead of a move during your turn
  '''
  def __init__(self, action:str, cog, you:PoshimoTrainer, battle:PoshimoBattle, action_mode=False, *args, **kwargs):
    self.action = action
    self.you = self.trainer = you # i am good programmer
    self.battle = battle
    self.cog = cog
    super().__init__(
      label=self.action.title(), 
      row=3, 
      style=discord.ButtonStyle.blurple, 
      disabled=action_mode,
      *args, 
      **kwargs
    )
  
  async def callback(self, interaction:discord.Interaction):
    ''' send the action to Battle if possible '''
    error = action_not_possible(self.action, self.battle, self.you)
    if error:
      await interaction.response.send_message(content=f"Oops: {error}", ephemeral=True)
    else:
      view = BattleTurn(self.cog, self.you, self.battle)
      if self.action == "swap":
        view.add_item(SwapMenu(self.cog, self.you, self.battle))
        view.add_item(CancelButton(self.cog, self.battle))
        await interaction.response.edit_message(view=view, embed=view.get_embed())
      if self.action == "snatch":
        #view.add_item(CaptureBallSelect(self.cog, self.you))
        view.add_item(CancelButton(self.cog, self.battle))
        pass
      if self.action == "item":
        view.add_item(ItemSelect(self.cog, self.trainer, battle_only=True, placeholder="Choose an item"))
        view.add_item(CancelButton(self.cog, self.battle))
        await interaction.response.edit_message(view=view, embed=view.get_embed())


class SwapMenu(discord.ui.Select):
  ''' menu for swapping your active poshimo in combat '''
  def __init__(self, cog, trainer:PoshimoTrainer, battle:PoshimoBattle):
    self.cog = cog
    self.battle = battle
    self.trainer = trainer
    self.eligible = self.trainer.list_all_poshimo(include=[PoshimoStatus.IDLE])
    options = []
    for index, p in enumerate(self.eligible):
      logger.info(index)
      options.append(
        discord.SelectOption(
          label=f"{p.display_name}",
          value=f"{index}"
        )
      )
    super().__init__(
      placeholder=f"Swap out {self.trainer.active_poshimo} with which Poshimo?",
      options=options,
      row=0
    )
  
  async def callback(self, interaction:discord.Interaction):
    ''' user has selected a poshimo to swap out '''
    index = int(self.values[0])
    poshimo = self.eligible[index]
    log_line = self.trainer.swap(poshimo)
    self.battle.enqueue_action("swap", self.trainer, log_line)
    view = BattleTurn(self.cog, self.trainer, self.battle)
    await interaction.response.edit_message(view=view, embed=view.get_embed())


class BattleResults(BattleTurn):
  ''' results of a turn '''
  def __init__(self):
    super().__init__(self.cog, self.trainer, self.battle)

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
    if len(trainer.list_all_poshimo(exclude=[PoshimoStatus.DEAD, PoshimoStatus.AWAY])) < 1:
      return "You don't have any eligible Poshimo to swap out!"
  return False
