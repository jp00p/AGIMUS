from common import *
from typing import List
from enum import Enum
import pocket_shimodae.utils as utils
from ..poshimo import Poshimo, PoshimoMove
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
    self._queued_moves:List[PoshimoMove] = [] 
    self._state:BattleStates = BattleStates.ACTIVE
    self._current_turn:int = 0
    self._round:int = 1
    self.wild_poshimo:Poshimo = wild_poshimo
    self._logs:list = []
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
    self.update("turn", self._current_turn)

  @property
  def round(self) -> int:
    return self._round
  
  @round.setter
  def round(self, val:int):
    self._round = val
    self.update("round", self._round)

  @property
  def logs(self) -> list:
    return self._logs
  
  @logs.setter
  def logs(self, val:list):
    self._logs = val
    self.update("logs", json.dumps(self._logs))

  def add_log(self, logline) -> None:
    """ adds a line to the combat log """
    newline = {
      "log_entry" : logline,
      "turn" : self._current_turn,
      "timestamp" : 0
    }
    temp_logs = self._logs
    temp_logs.append(newline)
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
      sql = "UPDATE poshimo_battles SET %s = %s WHERE id = %s"
      vals = (col, val, self.id)
      query.execute(sql, vals)
      logger.info(f"Updated poshimo battle #{self.id}'s {col} with value {val}")
  
  def start(self) -> int:
    """ 
    register this battle in the database 
    returns the battle ID
    """
    for trainer in self.trainers:
      trainer.status = TrainerStatus.BATTLING
    
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
    """ Internal only: load battle from DB """
    if not self.id:
      return
    with AgimusDB(dictionary=True) as query:
      sql = "SELECT * FROM poshimo_battles WHERE id = %s"
      vals = (self.id,)
      query.execute(sql, vals)
      battle_data = query.fetchone()
    self._battle_type = BattleTypes[battle_data["battle_type"]]
    self._state = BattleStates[battle_data["state"]]
    self._current_turn = battle_data["turn"]
    self._round = battle_data["round"]
    self._logs = json.loads(battle_data["logs"])
    self.wild_poshimo = battle_data["wild_poshimo"]
    if self.wild_poshimo:
      self.wild_poshimo = Poshimo(id=self.wild_poshimo, is_wild=True) # load the wild poshimo
    for i,trainer in enumerate(["trainer_1", "trainer_2"]):
      if isinstance(int, trainer):
        self.trainers[i] = utils.get_trainer(trainer_id=trainer) # real trainer
      else:
        self.trainers[i] = self.load_npc(self.wild_poshimo, name=trainer) # npc trainer

  def do_turn(self):
    """ once both sides have input their moves, this will run """
    logger.info(f"Doing the turn!")
    self.current_turn += 1   
    self.turn_start() # apply status effects
    self.handle_actions() # if someone used an action, these happen first
    self.handle_moves() # process move effects
    self.turn_end() # more status effects

  def turn_start(self):
    self.process_statuses(start=True)

  def turn_end(self):
    self.process_statuses(end=True)
    pass

  def handle_actions(self):
    # add logs
    pass

  def handle_moves(self):
    # add logs
    """ process moves in order based on speed """
    first_move,target = self.calculate_speed()
    move = self._queued_moves.pop(first_move)
    target = self.trainers[target].active_poshimo
    results = target.apply_move(move)
    logger.info(results)
    self.add_log(results)

    second_target = 1
    if target == 1:
      second_target = 0
    
    second_move = self._queued_moves.pop()
    target = self.trainers[second_target].active_poshimo
    results = target.apply_move(second_move)
    logger.info(results)
    self.add_log(results)

  def calculate_speed(self) -> tuple:
    """ 
    returns a tuple (1,0) the first number being who goes first, second being their target
    using these numbers to access index in queued_moves and self.trainers 
    """
    posh1,posh2 = self.trainers[0].active_poshimo,self.trainers[1].active_poshimo
    if posh1.speed > posh2.speed:
      return (0,1)
    return (1,0)

  def enqueue_move(self, move:PoshimoMove):
    self._queued_moves.append(move)
    
    if self.battle_type == BattleTypes.HUNT:
      # pick computer move if this is a hunt
      self._queued_moves.append(self.trainers[1].pick_move())
    
    if len(self._queued_moves) == len(self.trainers):
      # everyone has input their moves, let's roll
      self.do_turn()

  def process_statuses(self,start=False,end=False):
    # add logs
    if start:
      pass # handle beginning of turn status
    if end:
      pass # handle end of turn status

