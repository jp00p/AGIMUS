from enum import Enum, auto
from common import *
from ..poshimo import *
from typing import List

MAX_POSHIMO = 6 # the maximum poshimo a player can have
class TrainerStatus(Enum):
  IDLE = 0
  EXPLORING = 1
  BATTLING = 2
  def __str__(self):
    return f"{str(self.name).title()}"

# this will represent either a discord user or an npc
class PoshimoTrainer(object):
  def __init__(self, trainer_id=None):
    self.id = trainer_id
    self.discord_id = None
    self._poshimo_sac:list = []
    self._status = TrainerStatus.IDLE
    self._wins = 0
    self._losses = 0
    self._active_poshimo = None # current poshimo
    self._inventory = {} # all items
    self._location = "starting_zone" # where are you
    self._scarves = 0 # money
    self._buckles = "None" # these are like pokemon badges
    self.shimodaepedia = [] # aka pokedex, which poshimo has this player seen (list of ids)
    if self.id:
      self.load()

  def __str__(self) -> str:
    return f"TRAINER ID: {self.id}"

  def update(self, col_name, value=None) -> None:
    """ 
    update a col in the db for this trainer 
    HUMANS ONLY ew
    """
    logger.info(f"{Style.BRIGHT}Attempting to update trainer {self.id}'s {Fore.CYAN}{col_name}{Fore.RESET}{Style.RESET_ALL} with new value: {Fore.LIGHTGREEN_EX}{value}{Fore.RESET}")
    if not self.id:
      return
    with AgimusDB() as query:
      sql = f"UPDATE poshimo_trainers SET {col_name} = %s WHERE id = %s" # col_name is a trusted input or so we hope
      vals = (value, self.id)
      query.execute(sql, vals)
    

  def load(self):
    """ Load a human Trainer's data from DB """
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
      self._wins = trainer_data.get("wins")
      self._losses = trainer_data.get("losses")
      self._status = TrainerStatus(trainer_data.get("status"))
      
      
      
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

      self._inventory = trainer_data.get("inventory")
      self._scarves = trainer_data.get("scarves")
      self._buckles = trainer_data.get("buckles")
      self._shimodaepedia = trainer_data.get("discovered_poshimo")
    else:
      logger.info(f"There was an error loading trainer {self.id}'s info!")

  @property
  def wins(self):
    return self._wins
  
  @wins.setter
  def wins(self, amt):
    self._wins = amt
    self.update("wins", self._wins)

  @property
  def losses(self):
    return self._losses
  
  @losses.setter
  def losses(self, amt):
    self._losses = max(0, amt)
    self.update("losses", self._losses)

  @property
  def active_poshimo(self):
    return self._active_poshimo
  
  @active_poshimo.setter
  def active_poshimo(self, poshimo:Poshimo):
    self._active_poshimo = poshimo
    self.update("active_poshimo", poshimo.id)
  
  @property
  def inventory(self):
    return self._inventory

  @inventory.setter
  def inventory(self, value):
    self._inventory = value
    self.update("inventory", self._inventory)
    
  @property
  def location(self):
    return self._location

  @location.setter
  def location(self, value):
    self._location = value
    self.update("location", self._location)

  @property
  def scarves(self):
    return self._scarves

  @scarves.setter
  def scarves(self, amt):
    self._scarves = amt
    self.update("scarves", self._scarves)

  @property
  def status(self):
    return self._status

  @status.setter
  def status(self, val):
    self._status = val
    self.update("status", self._status)

  @property
  def buckles(self):
    return self._buckles

  @buckles.setter
  def buckles(self, obj):
    self._buckles = obj
    self.update("buckles", self._buckles)

  @property
  def poshimo_sac(self):
    return self._poshimo_sac

  @poshimo_sac.setter
  def poshimo_sac(self, obj):
    logger.info("Sac setter")
    self._poshimo_sac = obj
    if self._poshimo_sac:
      sac_json = json.dumps([i.id for i in self._poshimo_sac])
    else:
      sac_json = json.dumps([])
    self.update("poshimo_sac", sac_json)

  @property
  def shimodaepedia(self):
    return self._shimodaepedia
  
  @shimodaepedia.setter
  def shimodaepedia(self, obj):
    self._shimodaepedia = obj

  def add_poshimo(self, poshimo:Poshimo, set_active=False):
    """ 
    give this player a poshimo
    """
    poshimo.owner = self.id
    if poshimo.id:
      poshimo_id = poshimo.save()
    else:
      poshimo_id = poshimo.create()
    poshimo = Poshimo(id=poshimo_id)
    temp_sac = self.poshimo_sac
    if set_active: # if we're adding this as an active poshimo, put the current active poshimo in our sac
      if self.active_poshimo:
        temp_sac.append(self.active_poshimo)
        self.poshimo_sac = temp_sac
      self.active_poshimo = poshimo
    else:
      temp_sac.append(poshimo)
      self.poshimo_sac = temp_sac
    return poshimo

  def list_sac(self):
    temp_sac = self.poshimo_sac
    if self.active_poshimo in temp_sac:
      # dont show the active poshimo in the sac
      temp_sac.remove(self.active_poshimo)
    if len(temp_sac) <= 0:
      return "None"
    
    return "\n".join([p.display_name for p in temp_sac])

  def list_all_poshimo(self) -> List[Poshimo]:
    """ Get a list of all poshimo this Trainer owns """
    all_poshimo = [self._active_poshimo] + self._poshimo_sac
    logger.info(f"All this users poshimo: {all_poshimo}")
    return all_poshimo

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