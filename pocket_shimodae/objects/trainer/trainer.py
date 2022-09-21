""" a Trainer is the base character of our game """
from enum import Enum
from common import *
from ..world import PoshimoBiome
from ..poshimo import Poshimo, PoshimoMove
from typing import List

class TrainerStatus(Enum):
  IDLE = 0
  EXPLORING = 1
  BATTLING = 2
  def __str__(self):
    return f"{str(self.name).title()}"

# this will represent either a discord user or an npc
class PoshimoTrainer(object):
  """
  The base Trainer object, either a real player or an NPC

  pass a `trainer_id` to load from the DB

  pass a `name` to generate a basic NPC
  """
  MAX_POSHIMO = 6 # the maximum poshimo a player can have
  def __init__(self, trainer_id:int=None, name:str=None):
    self.id:int = trainer_id
    self.discord_id:int = None
    self.name:str = name # for NPCs only for now
    self._poshimo_sac:List[Poshimo] = []
    self._status:TrainerStatus = TrainerStatus.IDLE
    self._wins:int = 0
    self._losses:int = 0
    self._active_poshimo:Poshimo = None # current poshimo
    self._inventory:dict = {} # all items
    self._location:str = "starting_zone" # where are you
    self._scarves:int = 0 # money
    self._buckles:int = None # these are like pokemon badges TBD
    self._locations_unlocked:set = set()
    self.shimodaepedia:list = [] # aka pokedex, which poshimo has this player seen (list of ids) TBD
    
    if self.id:
      self.load()

  def __repr__(self) -> str:
    return f"TRAINER ID: {self.id}"

  def update(self, col_name, value=None) -> None:
    """ 
    Internal only:
    update a col in the db for this trainer 
    """
    logger.info(f"{Style.BRIGHT}Attempting to update trainer {self.id}'s {Fore.CYAN}{col_name}{Fore.RESET}{Style.RESET_ALL} with new value: {Fore.LIGHTGREEN_EX}{value}{Fore.RESET}")
    if not self.id:
      return
    with AgimusDB() as query:
      sql = f"UPDATE poshimo_trainers SET {col_name} = %s WHERE id = %s" # col_name is a trusted input or so we hope
      vals = (value, self.id)
      query.execute(sql, vals)
    

  def load(self) -> None:
    """ 
    Internal only: 
    Load a human Trainer's data from DB 
    """
    logger.info(f"Loading trainer {self.id} from DB...")
    with AgimusDB(dictionary=True) as query:
      sql = '''
      SELECT * FROM poshimo_trainers
        LEFT JOIN users ON poshimo_trainers.user_id = users.id
      WHERE poshimo_trainers.id = %s LIMIT 1
      '''
      vals = (self.id,)
      query.execute(sql, vals)
      trainer_data = query.fetchone()
    logger.info(f"Trainer data: {Fore.LIGHTMAGENTA_EX}{trainer_data}{Fore.RESET} ")
    if trainer_data:
      # load all the trainer data from the DB here
      self._wins = trainer_data.get("wins")
      self._losses = trainer_data.get("losses")
      self._status = TrainerStatus(trainer_data.get("status"))
      self._location = trainer_data.get("location")
      self.discord_id = trainer_data.get("discord_id")
      sac_data = trainer_data.get("poshimo_sac")
      if sac_data:
        logger.info(f"SAC DATA: {sac_data}")
        sac_data = json.loads(sac_data)
        self._poshimo_sac = [Poshimo(id=p) for p in sac_data]
      else:
        self._poshimo_sac = []
      
      if trainer_data.get("active_poshimo"):
        self._active_poshimo = Poshimo(id=trainer_data.get("active_poshimo"))
      else:
        self._active_poshimo = None

      loc_data = trainer_data.get("locations_unlocked")
      if loc_data:
        loc_data = json.loads(loc_data)
        self._locations_unlocked = set(loc_data)

      self._inventory = trainer_data.get("inventory")
      self._scarves = trainer_data.get("scarves")
      self._buckles = trainer_data.get("buckles")
      self._shimodaepedia = trainer_data.get("discovered_poshimo")
    else:
      logger.info(f"There was an error loading trainer {self.id}'s info!")

  @property
  def wins(self) -> int:
    return self._wins
  
  @wins.setter
  def wins(self, amt):
    self._wins = max(0, amt)
    self.update("wins", self._wins)

  @property
  def losses(self) -> int:
    return self._losses
  
  @losses.setter
  def losses(self, amt):
    self._losses = max(0, amt)
    self.update("losses", self._losses)

  @property
  def active_poshimo(self) -> Poshimo:
    return self._active_poshimo
  
  @active_poshimo.setter
  def active_poshimo(self, poshimo:Poshimo):
    if isinstance(poshimo, Poshimo):
      self._active_poshimo = poshimo
      self.update("active_poshimo", poshimo.id)
    else:
      self._active_poshimo = None
      self.update("active_poshimo", None)
  
  @property
  def inventory(self) -> dict:
    return self._inventory

  @inventory.setter
  def inventory(self, obj:dict):
    self._inventory = obj
    self.update("inventory", self._inventory) # will probably need json
    
  @property
  def location(self) -> str:
    return self._location

  @location.setter
  def location(self, value):
    self._location = value
    self.update("location", self._location)

  @property
  def scarves(self) -> int:
    return self._scarves

  @scarves.setter
  def scarves(self, amt):
    self._scarves = max(0, amt)
    self.update("scarves", self._scarves)

  @property
  def status(self) -> TrainerStatus:
    return self._status

  @status.setter
  def status(self, val):
    self._status:TrainerStatus = val
    self.update("status", self._status.value)

  @property
  def buckles(self) -> int:
    return self._buckles

  @buckles.setter
  def buckles(self, val):
    self._buckles = val
    self.update("buckles", self._buckles) # TODO: all this

  @property
  def poshimo_sac(self) -> list:
    return self._poshimo_sac

  @poshimo_sac.setter
  def poshimo_sac(self, obj):
    self._poshimo_sac = obj
    if len(self._poshimo_sac) > 0:
      sac_json = json.dumps([i.id for i in self._poshimo_sac])
    else:
      sac_json = json.dumps([])
    self.update("poshimo_sac", sac_json)

  @property
  def shimodaepedia(self) -> list:
    return self._shimodaepedia
  
  @shimodaepedia.setter
  def shimodaepedia(self, obj):
    self._shimodaepedia = obj

  @property
  def locations_unlocked(self) -> list:
    return self._locations_unlocked
  
  @locations_unlocked.setter
  def locations_unlocked(self, obj):
    self._locations_unlocked = obj
    if self._locations_unlocked:
      loc_json = json.dumps(list(self._locations_unlocked))
    else:
      loc_json = json.dumps([])
    self.update("locations_unlocked", loc_json)

  def add_poshimo(self, poshimo:Poshimo, set_active=False) -> Poshimo:
    """ 
    give this player a new poshimo
    """
    new_poshimo = poshimo
    new_poshimo.owner = self.id # set poshimo owner
    poshimo_id = new_poshimo.save() # save this poshimo in the db

    new_poshimo = Poshimo(id=poshimo_id) # reinstance the object from the db
    new_poshimo.owner = self.id
    logger.info(f"Adding {str(new_poshimo)}")

    temp_sac = self.poshimo_sac
    if set_active: # if we're adding this as an active poshimo...
      if self.active_poshimo is not None:
        temp_sac.append(self.active_poshimo) # put the current active poshimo in our sac
      self.active_poshimo = new_poshimo # then make this new poshimo our active one
    else: 
      temp_sac.append(new_poshimo) # otherwise just put it in the sac
    self.poshimo_sac = temp_sac # have to do this to trigger the setter
    return new_poshimo

  def release_poshimo(self, poshimo:Poshimo) -> None:
    """ release a poshimo into the wild (remove ownership) """
    if poshimo.id == self.active_poshimo.id:
      self.active_poshimo = None
    temp_sac:List[Poshimo] = self.poshimo_sac
    for p in temp_sac:
      if poshimo.id == p.id:
        temp_sac.remove(p)
    self.poshimo_sac = temp_sac
    poshimo.owner = None # will fire update on the poshimo object

  def list_sac(self) -> str:
    """ list the contents of your sac """
    temp_sac:List[Poshimo] = self.poshimo_sac
    if self.active_poshimo in temp_sac:
      # dont show the active poshimo in the sac
      temp_sac.remove(self.active_poshimo)
    if len(temp_sac) <= 0:
      return "Empty sac"
    return "\n".join([p for p in temp_sac])

  def list_all_poshimo(self) -> List[Poshimo]:
    """ Get a list of all poshimo this Trainer owns """
    if self.active_poshimo:
      all_poshimo = list([self.active_poshimo] + self.poshimo_sac)
    else:
      all_poshimo = self.poshimo_sac
    logger.info(f"All this users poshimo: {','.join([str(p.id) for p in all_poshimo])}")
    return all_poshimo

  def pick_move(self) -> PoshimoMove:
    possible_moves = []
    for move in self.active_poshimo.move_list:
      if move.stamina > 0:
        possible_moves.append(move)
    
    if len(possible_moves) < 1:
      return PoshimoMove(name="struggle")
    return move

  def remove_poshimo(self, poshimo):
    # remove poshimo from sac
    pass

  def give_item(self, item):
    # give player an item
    pass

  def use_item(self, item):
    # use an item
    pass

  def remove_item(self, item):
    # remove item from inventory
    pass

  def update_db_column(self, column, value):
    # update player db info
    return