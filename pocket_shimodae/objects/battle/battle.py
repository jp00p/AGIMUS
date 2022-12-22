from common import *
from math import floor
import pickle
from typing import List, Tuple, Dict
from enum import Enum
from pocket_shimodae.objects.battle import effect
import pocket_shimodae.utils as utils
from ..poshimo import Poshimo, PoshimoMove, MoveKinds, MoveTargets, PoshimoStatus
from ..trainer import PoshimoTrainer, TrainerStatus
from . import move_functions

class BattleStates(Enum):
  ACTIVE = 0
  FINISHED = 1

class BattleTypes(Enum):
  HUNT = 0
  NPC = 1
  DUEL = 2

class BattleOutcomes(Enum):
  FAINTED = 0
  CAPTURED = 1
  FLED = 2

class PoshimoBattle(object):
  """ a poshimo battle between two trainers or a trainer and a wild poshimo """
  def __init__(self, battle_type:BattleTypes=None, trainer_1:PoshimoTrainer=PoshimoTrainer, trainer_2:PoshimoTrainer=None, wild_poshimo:Poshimo=None, id:int=None) -> None:
    self.id:int = id
    self._battle_type:BattleTypes = battle_type
    self.trainers:List[PoshimoTrainer] = [trainer_1, trainer_2] # trainer 1 should always be the initiator of the battle, trainer 2 is optional and will be a dummy trainer if not specified
    self._queued_moves:List[Tuple[PoshimoMove,PoshimoTrainer,str]] = [] 
    self._queued_actions:list = []
    self._state:BattleStates = BattleStates.ACTIVE
    self._current_turn:int = 0
    self._round:int = 1
    self._outcome:BattleOutcomes = None
    self.wild_poshimo:Poshimo = wild_poshimo
    self._logs:Dict[int,List[dict]] = {}
    self.battle_actions:list = ["item", "swap", "flee"] # the base actions for the actions menu
    self._can_flee = True
    self.dead_bodies:List[Tuple[Poshimo, PoshimoTrainer]] = []
    
    if self._battle_type is BattleTypes.HUNT:
      self.trainers[1] = self.load_npc(self.wild_poshimo, name="Test NPC") # create the fake NPC

    if self.id:
      # battle in progress
      self.load()
    else:
      # new battle
      self.id = self.start()
      self.logs[self.current_turn] = []
      self.add_log(f"The battle between {self.trainers[0]} and {self.trainers[1]} begins!")
    if self._battle_type is BattleTypes.HUNT:
      self.add_snatch()
    
  def add_snatch(self):
    """ add capture to actions menu """
    self.battle_actions.insert(-1, "snatch")

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

  @property
  def outcome(self) -> BattleOutcomes:
    return self._outcome
  
  @outcome.setter
  def outcome(self, val:BattleOutcomes) -> None:
    self._outcome = val
    self.update("outcome", self._outcome.value)

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
    #TODO: generate random name
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
      trainer.active_poshimo.in_combat = True
    
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
    logger.info(f"{Fore.LIGHTRED_EX}Loaded battle {self.id} ({self._battle_type})!{Fore.RESET}")
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
    self.turn_start() # update turn, apply status effects
    self.handle_moves() # process moves
    self.handle_dead_bodies() # test
    self.turn_end() # more status effects
    

  def turn_start(self):
    """ handle things that happen at the start of the turn """
    self.current_turn = self.current_turn + 1
    self._logs[self.current_turn] = [] # init the log list (this won't trigger a db update yet)
    #self.add_log(f"Turn {self.current_turn} starts!")
    self.process_statuses(start=True)

  def turn_end(self):
    """ handle things that happen at the end of the turn """
    #self.add_log(f"Turn {self.current_turn} is over!")
    self.process_statuses(end=True)
    self._queued_actions = [] # empty queues
    self._queued_moves = []

  def handle_moves(self):
    """ 
    determine the order of operations and determine the outcome for each poshimo
    """
    self.calculate_speed() # determine which move goes first
    final_moves:List[Tuple[PoshimoMove, PoshimoTrainer, PoshimoTrainer]] = [] # final move list after speed and other calcs
    logger.info(self._queued_moves)
    
    # first move
    move1,trainer1 = self._queued_moves[0][0], self._queued_moves[0][1],
    target1 = self._queued_moves[1][1]
    if len(self._queued_moves[0]) > 2: # action log
      self.add_log(self._queued_moves[0][2])
    final_moves.append((move1, target1, trainer1))

    # second move!
    move2,trainer2 = self._queued_moves[1][0], self._queued_moves[1][1]
    target2 = self._queued_moves[0][1]
    if len(self._queued_moves[1]) > 2: # action log
      self.add_log(self._queued_moves[1][2])
    final_moves.append((move2, target2, trainer2))

    # now we have both moves in order, apply them to each poshimo in order!
    for move,target,trainer in final_moves:
      if move != "action":
        results = self.apply_move(move,target,trainer)
        self.add_log(results)
        if target.active_poshimo.hp <= 0:
          logger.info("Poshimo fainted!")
          self.dead_bodies.append((target.active_poshimo, target))
          break # if someone dies, moves stop


  def handle_dead_bodies(self):
    for poshimo,trainer in self.dead_bodies:
      self.add_log(f"{trainer}'s {poshimo} fainted!")
      # attempt swap
      swap = trainer.random_swap()
      if not swap:
        self.end_battle(loser=trainer)
        return
      else:
        self.add_log(f"{trainer} frantically swapped out {poshimo} for {trainer.active_poshimo}")


  def end_battle(self,loser:PoshimoTrainer):
    ''' 
    end of battle (someone lost or won, all poshimo fainted, or captured) 
    reset states, hand out rewards, etc
    '''
    self.state = BattleStates.FINISHED
    for trainer in self.trainers:
      trainer.end_combat()
    temp_trainers = self.trainers.copy()
    temp_trainers.remove(loser)
    winner = temp_trainers.pop()

    xp_gained = loser.active_poshimo.xp_given()
    winner.active_poshimo.xp += xp_gained
    stat_xp = loser.active_poshimo.stat_xp_given()
    winner.active_poshimo.apply_stat_xp(stat_xp)

    if self.battle_type is BattleTypes.DUEL:
      loser.losses += 1
      winner.wins += 1

    self.add_log(f"Battle is over! {loser} was unable to overcome {winner}'s raw strength and tactical prowess.")

  def calculate_speed(self) -> None:
    """ 
    updates queued_moves to be in the order they should happen 
    """
    #TODO: some moves happen first regardless of speed
    move1,move2 = self._queued_moves[0][0], self._queued_moves[1][0]
    posh1,posh2 = self._queued_moves[0][1].active_poshimo, self._queued_moves[1][1].active_poshimo
    trainer1,trainer2 = self._queued_moves[0][1], self._queued_moves[1][1]
    
    if move1 == "action" or posh1.speed > posh2.speed:
      self._queued_moves = [self._queued_moves[0], self._queued_moves[1]]
    elif move2 == "action" or posh2.speed > posh1.speed:
      self._queued_moves = [self._queued_moves[1], self._queued_moves[0]]
    
    logger.info(self._queued_moves)

  def enqueue_move(self, move:PoshimoMove, trainer:PoshimoTrainer, logline:str=None):
    """ add a move to the queue. once the queue is full, the turn will process """
    self._queued_moves.append((move, trainer, logline))

    logger.info(f"Adding to queued moves: {move} {trainer}")
    
    if self.battle_type == BattleTypes.HUNT:
      # pick computer move if this is a hunt
      self._queued_moves.append(( self.trainers[1].pick_move(), self.trainers[1] ))
    
    if (len(self._queued_moves)+len(self._queued_actions)) == len(self.trainers):
      # everyone has input their moves, let's roll
      self.do_turn()

  def enqueue_action(self, action:str, trainer:PoshimoTrainer, logline:str):
    """ if a trainer does an action, it takes up their turn """
    self.enqueue_move(move="action", trainer=trainer, logline=logline)
    #self.add_log(logline)
    
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
    # TODO:multiple hits
    # TODO:accuracy <--
    # TODO:keep track of last damaging move used against this poshimo
    # TODO:flags
    
    poshimo = inflictor.active_poshimo # the poshimo doing the move
    victim = target.active_poshimo # the poshimo taking the move
    log_line = [] # the line we'll add to the log when this move is finished
    
    STAB = False # same type attack bonus
    CRIT = False # critical hit
    WEAK = False # target is weak against
    BUFF = False # target is strong against

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
      
      if move.type.is_strong_against(victim.types):
        damage_modifier *= 2
        BUFF = True
      
      if move.type.is_weak_against(victim.types):
        damage_modifier *= 0.5
        WEAK = True

      power = move.power

      if move.kind == MoveKinds.SPECIAL:
        attack = poshimo.special_attack.value()
        defense = victim.special_defense.value()
      elif move.kind == MoveKinds.PHYSICAL:
        attack = poshimo.attack.value()
        defense = victim.defense.value()

      damage = (floor(floor(floor(((2 * int(poshimo.level)) / 5) + 2) * int(attack) * int(power) / int(defense)) / 50) + 2) # the base damage formula from pokemon
      damage = int(floor(damage * damage_modifier))

      if damage > 0:
        if CRIT: # CRITICAL HIT
          log_line.append("**Critical hit!**")
        if STAB and not BUFF and not WEAK: # SAME TYPE ATTACK
          log_line.append("*It's particularly effective!*")
        if STAB and BUFF and not WEAK: # SAME TYPE, AND STRONG AGAINST
          log_line.append("*It's insanely effective!*")
        if not STAB and BUFF and not WEAK: # NOT SAME TYPE, BUT STRONG AGAINST
          log_line.append("*It works rather well!*")
        if WEAK: # WEAK AGAINST (OVERRIDES STAB)
          log_line.append("*The effacaciousness of the move seems diminished.*")
        log_line.append(f"It deals **{damage} damage!**")
        victim.hp = int(victim.hp) - int(damage)
      
      if damage == 0:
        log_line.append("It seems to have no effect!")   

    if move.function_code:
      move_details = {
        "damage" : damage
      }
      ''' apply function code if there is one '''
      move_method = getattr(move_functions, move.function_code) # pulls function from move_functions.py
      params = move.function_params
      if move.function_target == "self":
        effect_target = poshimo
      else:
        effect_target = victim
      result = move_method(*params, chance=move.proc_chance, target=effect_target, move_details=move_details) # fire function
      if result:
        log_line.append(f"**{result}**")
         
    # end of apply_move
    self.add_log(" ".join([line for line in log_line]))