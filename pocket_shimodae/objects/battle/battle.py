from common import *
from math import floor
import pickle
from typing import List, Tuple, Dict
from enum import Enum
from pocket_shimodae.objects.battle import effect
import pocket_shimodae.utils as utils
from ..poshimo import Poshimo, PoshimoMove, MoveKinds, MoveTargets
from ..trainer import PoshimoTrainer, TrainerStatus

class BattleStates(Enum):
  ACTIVE = 0
  PENDING = 1
  FINISHED = 2

class BattleTypes(Enum):
  HUNT = 0
  NPC = 1
  DUEL = 2

class PoshimoBattle(object):
  """ a poshimo battle between two trainers or a trainer and a wild poshimo """
  def __init__(self, battle_type:BattleTypes=None, trainer_1:PoshimoTrainer=PoshimoTrainer, trainer_2:PoshimoTrainer=None, wild_poshimo:Poshimo=None, id:int=None) -> None:
    self.id:int = id
    self._battle_type:BattleTypes = battle_type
    self.trainers:List[PoshimoTrainer] = [trainer_1, trainer_2] # trainer 1 should always be the initiator of the battle, trainer 2 is optional and will be a dummy trainer if not specified
    self._queued_moves:List[Tuple[PoshimoMove,PoshimoTrainer]] = [] 
    self._state:BattleStates = BattleStates.ACTIVE
    self._current_turn:int = 0
    self._round:int = 1
    self.wild_poshimo:Poshimo = wild_poshimo
    self._logs:Dict[int,List[dict]] = {}
    self.battle_actions:list = ["item", "swap", "flee"] # the base actions for the actions menu

    if self._battle_type is BattleTypes.HUNT:
      self.battle_actions.insert(-1, "capture") # add capture to actions menu if this is a hunt
      self.trainers[1] = self.load_npc(self.wild_poshimo, name="Test NPC") # create the fake NPC

    if self.id:
      # battle in progress
      self.load()
    else:
      # new battle
      self.id = self.start()

  @property
  def battle_type(self) -> BattleTypes:
    return self._battle_type
  
  @battle_type.setter
  def battle_type(self, val:BattleTypes):
    self._battle_type = val
    self.update("battle_type", self._battle_type.value)

  @property
  def state(self) -> BattleStates:
    return self._state
  
  @state.setter
  def state(self, val:BattleStates):
    self._state = val
    self.update("state", self._state.value)

  @property
  def current_turn(self) -> int:
    return self._current_turn
  
  @current_turn.setter
  def current_turn(self, val:int):
    self._current_turn = val
    self.update("current_turn", self._current_turn)

  @property
  def round(self) -> int:
    return self._round
  
  @round.setter
  def round(self, val:int):
    self._round = val
    self.update("round", self._round)

  @property
  def logs(self) -> dict:
    return self._logs
  
  @logs.setter
  def logs(self, val:dict):
    self._logs = val
    pickled_logs = pickle.dumps(self._logs)
    self.update("logs", pickled_logs)

  def add_log(self, logline) -> None:
    """ adds a line to the combat log """
    newline = {
      "log_entry" : logline,
      "turn" : self._current_turn,
      "timestamp" : 0
    }    
    temp_logs = self._logs
    temp_logs[self._current_turn].append(newline)
    self.logs = temp_logs # fire the update
    
  def load_npc(self, poshimo:Poshimo, name=None) -> PoshimoTrainer:
    """ load an NPC, give it a name """
    npc = PoshimoTrainer(name=name)
    npc.active_poshimo = poshimo
    logger.info(f"Created an NPC! {npc}")
    return npc

  def update(self, col, val) -> None:
    """ update a col in the DB for this battle """
    if not self.id:
      return
    with AgimusDB() as query:
      sql = f"UPDATE poshimo_battles SET {col} = %s WHERE id = %s;"
      vals = (val, self.id)
      query.execute(sql, vals)
      #logger.info(f"Updated poshimo battle #{self.id}'s {col} with value {val}")
  
  def start(self) -> int:
    """
    begin a new battle! 

    register this battle in the database 

    returns the new battle's ID
    """

    for trainer in self.trainers:
      trainer.status = TrainerStatus.BATTLING # set trainers to battling
    
    with AgimusDB() as query:
      sql = """INSERT INTO poshimo_battles (battle_type,trainer_1,trainer_2,wild_poshimo) VALUES (%s, %s, %s, %s)"""
      vals = (self._battle_type.value,)
      for trainer in self.trainers:
        if trainer.id:
          vals += (trainer.id,)
        else:
          vals += (trainer.name,)
      if self.wild_poshimo:
        vals += (self.wild_poshimo.id,)
      else:
        vals += (None,)
      query.execute(sql, vals)
      return query.lastrowid

  def load(self) -> None:
    """ Internal only: load in-progress battle from DB """
    if not self.id:
      return
    with AgimusDB(dictionary=True) as query:
      sql = "SELECT * FROM poshimo_battles WHERE id = %s"
      vals = (self.id,)
      query.execute(sql, vals)
      battle_data = query.fetchone()
    self._battle_type = BattleTypes(battle_data["battle_type"])
    self._state = BattleStates(battle_data["state"])
    self._current_turn:int = battle_data["current_turn"]
    self._round = battle_data["round"]
    
    self._logs:Dict[int,List[dict]] = pickle.loads(battle_data["logs"])
    self.wild_poshimo = battle_data["wild_poshimo"]

    if self.wild_poshimo:
      self.wild_poshimo = Poshimo(id=self.wild_poshimo, is_wild=True) # load the wild poshimo
    for i,trainer in enumerate([battle_data["trainer_1"], battle_data["trainer_2"]]):
      logger.info(f"{i} {trainer} {type(trainer)}")
      if isinstance(trainer,int):
        self.trainers[i] = utils.get_trainer(trainer_id=trainer) # real trainer
      else:
        self.trainers[i] = self.load_npc(self.wild_poshimo, name=trainer) # npc trainer

  def do_turn(self):
    """ once both sides have input their moves, this will run """
    logger.info(f"Doing the turn!")
    self.current_turn = self.current_turn + 1
    self._logs[self.current_turn] = [] # init the log list (this won't trigger a db update)
    self.turn_start() # apply status effects
    self.handle_actions() # if someone used an action, these happen first
    self.handle_moves() # process moves
    self.turn_end() # more status effects

  def turn_start(self):
    """ handle things that happen at the start of the turn """
    #self.add_log(f"Turn {self.current_turn} starts!")
    self.process_statuses(start=True)

  def turn_end(self):
    """ handle things that happen at the end of the turn """
    #self.add_log(f"Turn {self.current_turn} is over!")
    self.process_statuses(end=True)

  def handle_actions(self):
    """ handle actions like items, swapping, etc """
    pass

  def handle_moves(self):
    """ 
    determine the order of operations and determine the outcome for each poshimo
    """
    
    self.calculate_speed() # determine which move goes first
    final_moves:List[Tuple[PoshimoMove, PoshimoTrainer, PoshimoTrainer]] = []

    # first move
    move1,trainer1 = self._queued_moves[0]
    target1 = self._queued_moves[1][1]
    final_moves.append((move1, target1, trainer1))

    # second move!
    move2,trainer2 = self._queued_moves[1]
    target2 = self._queued_moves[0][1]
    final_moves.append((move2, target2, trainer2))

    # now we have both moves in order, apply them to each poshimo in order!
    for move,target,trainer in final_moves:
      results = self.apply_move(move,target,trainer)      
      self.add_log(results)

    self._queued_moves = [] # empty the queue
    

  def calculate_speed(self) -> None:
    """ 
    updates queued_moves to be in the order they should happen 
    """
    #TODO: some moves happen first regardless of speed
    move1,move2 = self._queued_moves[0][0], self._queued_moves[1][0]
    posh1,posh2 = self._queued_moves[0][1].active_poshimo, self._queued_moves[1][1].active_poshimo
    trainer1,trainer2 = self._queued_moves[0][1], self._queued_moves[1][1]
    
    if posh1.speed > posh2.speed:
      self._queued_moves = [(move1, trainer1), (move2, trainer2)]
    else:
      self._queued_moves = [(move2, trainer2), (move1, trainer1)]


  def enqueue_move(self, move:PoshimoMove, trainer:PoshimoTrainer):
    """ add a move to the queue. once the queue is full, the turn will process """
    self._queued_moves.append((move, trainer))

    logger.info(f"Adding to queued moves: {move} {trainer}")
    
    if self.battle_type == BattleTypes.HUNT:
      # pick computer move if this is a hunt
      self._queued_moves.append(( self.trainers[1].pick_move(), self.trainers[1] ))
    
    if len(self._queued_moves) == len(self.trainers):
      # everyone has input their moves, let's roll
      self.do_turn()

  def process_statuses(self,start=False,end=False):
    """ figure out if any poshimo need to deal with status effects """
    # add logs
    if start:
      pass # handle beginning of turn status
    if end:
      pass # handle end of turn status


  def apply_move(self, move:PoshimoMove, target:PoshimoTrainer, inflictor:PoshimoTrainer) -> str:
    """
    apply damage, effects, status from a move to a poshimo!
    this is the big kahuna
    this is where all the magic happens
    ----
    `move`: the move being performed

    `target`: the target of the move

    `inflictor`: who is doing the move?
    """
    # TODO:struggle
    # TODO:multiple hits
    # TODO:accuracy
    # TODO:keep track of last damaging move used against this poshimo
    # TODO:func codes
    # TODO:flags
    # TODO:weather mods?
    # TODO:special stuff???
    # TODO:AHHH
    
    poshimo = inflictor.active_poshimo # the poshimo doing the move
    victim = target.active_poshimo # the poshimo taking the move
    log_line = [] # the line we'll add to the log when this move is finished
    STAB = False
    CRIT = False

    if move.kind is MoveKinds.STATUS:
      damage = 0
      log_line.append(f"`{poshimo.display_name} used {move.display_name}! This isn't implemented yet.`")
      
    else:
      
      log_line.append(f"**{poshimo.display_name}** used `{move.display_name}` on **{victim.display_name}**!")
      
      # calculate the damage for this move!
      critical_hit = bool( min(255,int(floor(poshimo.speed/2))) > random.randint(0,256) ) # if speed/2 is greater than random(0,256) then the move is a crit - speed/2 can't be greater than 255
      # this crit formula might be busted, need to look into later gen crit formula
      damage, attack, defense = 0, 0, 0
      damage_modifier = 1
      
      if critical_hit:
        damage_modifier *= 1.5
        CRIT = True

      # random fluctuation in every attack
      damage_modifier *= random.uniform(0.85, 1.0)

      # STAB bonus (Same-Type-Attack-Bonus)
      # if a move is the same type as the poshimo it's hitting
      if move.type in victim.types:
        damage_modifier *= 1.5
        STAB = True
      
      power = move.power

      if move.kind == MoveKinds.SPECIAL:
        attack = poshimo.special_attack
        defense = victim.special_defense
      elif move.kind == MoveKinds.PHYSICAL:
        attack = poshimo.attack
        defense = victim.defense

      damage = (floor(floor(floor(((2 * int(poshimo.level)) / 5) + 2) * int(attack) * int(power) / int(defense)) / 50) + 2) # the base damage formula from pokemon
      damage = int(floor(damage * damage_modifier))

      if damage > 0:
        if CRIT:
          log_line.append("**Critical hit!**")
        if STAB:
          log_line.append("*It's particularly effective!*")
        log_line.append(f"It deals **{damage} damage!**")
        victim.hp = int(victim.hp) - int(damage)

    

    if move.function_codes:
      for func in move.function_codes:
        # figure out which functions to call
        effect_function = getattr(victim,func)
        if effect_function:
          effect_function() # not victim.effect_function() ?
    
    if victim.hp <= 0:
      # victim ded
      pass
    if poshimo.hp <= 0:
      # person who did the move ded (recoil, etc)
      pass
      
    # end of apply_move
    self.add_log(" ".join([line for line in log_line]))