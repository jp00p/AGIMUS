''' a Trainer is the base character of our game, either a player or NPC '''
from common import *
from enum import Enum
from typing import List, Dict, TypedDict

from ..world.item import PoshimoItem, ItemTypes, FunctionCodes
from ..world.fish import PoshimoFish
from ..world.awaymissions import AwayMission
from ..poshimo import Poshimo, PoshimoMove, PoshimoStatus

InventoryDict = TypedDict('Inventory', {'item': PoshimoItem, 'amount': int})

class TrainerStatus(Enum):
  IDLE = 0
  EXPLORING = 1
  BATTLING = 2
  TRAVELING = 3
  def __str__(self):
    return f"{str(self.name).title()}"

# this will represent either a discord user or an npc
class PoshimoTrainer(object):
  '''
  The base Trainer object, either a real player or an NPC

  pass a `trainer_id` to load from the DB

  pass a `name` to generate a basic NPC
  '''
  MAX_POSHIMO = 9 # the maximum poshimo a player can have
  
  def __init__(self, trainer_id:int=None, name:str=None):
    self.id:int = trainer_id
    self.discord_id:int = None
    self.name:str = name
    self.display_name:str = name # real players will have their discord handle here
    self._poshimo_sac:List[Poshimo] = []
    self._away_poshimo: List[Poshimo] = []
    self._status:TrainerStatus = TrainerStatus.IDLE
    self._wins:int = 0
    self._losses:int = 0
    self._active_poshimo:Poshimo = None # current poshimo
    self._inventory:Dict[str,InventoryDict] = {} # all items
    self._location:str = "starting_zone" # where are you
    self._scarves:int = 0 # money
    self._buckles:int = None # these are like pokemon badges TBD
    self._locations_unlocked:set = set()
    
    self.shimodaepedia:list = [] # aka pokedex, which poshimo has this player seen (list of ids) TBD
    
    if self.id:
      self.load()

  def __str__(self) -> str:
    return self.display_name

  def update(self, col_name, value=None) -> None:
    '''
    Internal only:
    update a col in the db for this trainer 
    '''
    logger.info(f"{Style.BRIGHT}Attempting to update trainer {self.id}'s {Fore.CYAN}{col_name}{Fore.RESET}{Style.RESET_ALL} with new value: {Fore.LIGHTGREEN_EX}{value}{Fore.RESET}")
    if not self.id:
      return
    with AgimusDB() as query:
      sql = f"UPDATE poshimo_trainers SET {col_name} = %s WHERE id = %s" # col_name is a trusted input or so we hope
      vals = (value, self.id)
      query.execute(sql, vals)

  def load(self) -> None:
    ''' 
    Internal only: 
    Load a human Trainer's data from DB 
    '''
    logger.info(f"Loading trainer {self.id} from DB...")
    with AgimusDB(dictionary=True) as query:
      sql = '''
      SELECT * FROM poshimo_trainers
        LEFT JOIN users ON poshimo_trainers.user_id = users.id
      WHERE poshimo_trainers.id = %s LIMIT 1
      '''
      vals = (self.id,)
      query.execute(sql, vals)
      trainer_data:dict = query.fetchone()
    
    if trainer_data:
      # load all the trainer data from the DB here
      self._wins = trainer_data.get("wins")
      self._losses = trainer_data.get("losses")
      self._status = TrainerStatus(trainer_data.get("status"))
      self._location = trainer_data.get("location","").lower()
      self.discord_id = trainer_data.get("discord_id")
      self.display_name = trainer_data.get("name")
      sac_data = trainer_data.get("poshimo_sac")
      if sac_data:
        sac_data = json.loads(sac_data)
        self._poshimo_sac = [Poshimo(id=p) for p in sac_data]
      else:
        self._poshimo_sac = []
      
      away_data = trainer_data.get("away_poshimo")
      if away_data:
        away_data = json.loads(away_data)
        self._away_poshimo = [Poshimo(id=p) for p in away_data]
      else:
        self._away_poshimo = []

      if trainer_data.get("active_poshimo"):
        self._active_poshimo = Poshimo(id=trainer_data.get("active_poshimo"))
      else:
        self._active_poshimo = None

      loc_data = trainer_data.get("locations_unlocked")
      if loc_data:
        loc_data = json.loads(loc_data)
        self._locations_unlocked = set(loc_data)
        logger.info(self._locations_unlocked)
      
      item_data = trainer_data.get("inventory")
      if item_data:
        item_data = json.loads(item_data)
        for i in item_data:
          self._inventory[i[0]] = {
            "item":PoshimoItem(i[0]),
            "amount":i[1]
          }
      else:
        self._inventory = {}
      
      self._scarves = trainer_data.get("scarves")
      self._buckles = trainer_data.get("buckles")
      self._shimodaepedia = trainer_data.get("discovered_poshimo")
    else:
      logger.info(f"There was an error loading trainer {self.id}'s info!")



  def add_poshimo(self, poshimo:Poshimo, set_active=False) -> Poshimo:
    """ 
    put a poshimo in this player's sac (or active slot)
    """
    new_poshimo = poshimo
    new_poshimo.owner = self.id # set poshimo owner
    poshimo_id = new_poshimo.save() # save this poshimo in the db

    new_poshimo = Poshimo(id=poshimo_id) # reinstance the object from the db
    new_poshimo.owner = self.id
    #logger.info(f"Adding {str(new_poshimo)}")

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
    ''' release a poshimo into the wild (remove ownership but not actually delete it) '''
    if poshimo.id == self.active_poshimo.id:
      self.active_poshimo = None
    temp_sac = self.poshimo_sac
    for p in temp_sac:
      if poshimo.id == p.id:
        temp_sac.remove(p)
    self.poshimo_sac = temp_sac
    poshimo.owner = None # will fire update on the poshimo object

  def list_sac(self) -> str:
    ''' 
    list the contents of your sac 
    returns a formatted string
    '''
    temp_sac = self.poshimo_sac
    if self.active_poshimo in temp_sac:
      # dont show the active poshimo in the sac
      temp_sac.remove(self.active_poshimo)
    if len(temp_sac) <= 0:
      return "Empty sac"
    return "\n".join([p.display_name for p in temp_sac])

  def list_away(self) -> str:
    ''' 
    list the poshimo who are away right now 
    returns a formatted string
    '''
    if len(self._away_poshimo) <= 0:
      return "No Poshimo are away"
    return_str = ""
    for p in self._away_poshimo:
      mission = AwayMission(id=p.mission_id)
      return_str += f"{p.display_name} {mission.get_emoji()}"
    return return_str

  def list_inventory(self) -> str:
    ''' list all this players items '''
    #TODO: categorize
    inv_str = ""
    if len(self._inventory) > 0:
      for i in self._inventory.values():
        inv_str += f"{i['item'].name.title()} x{i['amount']}" + "\n"
    else:
      inv_str = "You have no items!"
    return inv_str

  def list_all_poshimo(self, include_away=False) -> List[Poshimo]:
    ''' 
    Get a list of all this trainer's poshimo
    '''
    all_poshimo = []
    all_poshimo += self._poshimo_sac
    if self._active_poshimo:
      all_poshimo += [self._active_poshimo]
    if include_away:
      all_poshimo += self._away_poshimo
    return all_poshimo

  def pick_move(self) -> PoshimoMove:
    '''
    pick a random move from the available moves
    used by NPCs
    '''
    possible_moves = []
    for move in self.active_poshimo.move_list:
      if move.stamina > 0:
        possible_moves.append(move)
    
    if len(possible_moves) < 1:
      move = PoshimoMove(name="struggle")
    else:
      move = random.choice(possible_moves)
    logger.info(f"NPC has picked {move.display_name}!")
    return move

  def get_eligible_poshimo_for_swap(self) -> List[Poshimo]:
    ''' return list of all poshimo eligible for swapping (must be alive) '''
    eligible_poshimo = []
    for poshimo in self._poshimo_sac:
      if poshimo.hp > 0:
        eligible_poshimo.append(poshimo)
    return eligible_poshimo
  
  def is_active_poshimo_ready(self) -> bool:
    ''' returns true if there is an active poshimo and its HP is greater than 0'''
    return self.active_poshimo and self.active_poshimo.hp > 0

  def random_swap(self):
    ''' do a random swap (when your active poshimo dies) '''
    eligible_poshimo = self.get_eligible_poshimo_for_swap()
    if len(eligible_poshimo) > 0:
      self.swap(random.choice(eligible_poshimo))
    else:
      return False

  def send_poshimo_away(self, poshimo:Poshimo) -> None:
    ''' send a poshimo on an away mission, stick it in your away sac '''
    temp_away_poshimo = self._away_poshimo
    poshimo.status = PoshimoStatus.AWAY
    if self._active_poshimo and poshimo.id is self._active_poshimo.id:
      self.active_poshimo = None
    else:
      temp_sac = self._poshimo_sac
      temp_sac.remove(poshimo)
      self.poshimo_sac = temp_sac
    temp_away_poshimo.append(poshimo)
    self.away_poshimo = temp_away_poshimo

  def return_poshimo_from_mission(self, poshimo:Poshimo):
    ''' put a poshimo back in your bag and set it to idle '''
    poshimo.status = PoshimoStatus.IDLE
    poshimo.mission_id = None
    away_poshimo = self._away_poshimo
    for p in away_poshimo:
      logger.info(p)
      logger.info(poshimo)
      if p.id == poshimo.id:
        away_poshimo.remove(p)
        break
    self.away_poshimo = away_poshimo
    temp_sac = self._poshimo_sac
    temp_sac.append(poshimo)
    self.poshimo_sac = temp_sac

  def list_missions_in_progress(self) -> List[AwayMission]:
    ''' return a list of all missions in progress for this trainer '''
    if len(self._away_poshimo) < 1:
      return None
    active_missions = []
    for p in self._away_poshimo:
      active_missions.append( AwayMission(id=int(p.mission_id)) )
    return active_missions
  
  def list_missions_ready_to_resolve(self) -> List[AwayMission]:
    ''' return a list of all missions ready to resolve for this trainer '''
    ready_missions = []
    if len(self._away_poshimo) < 1:
      return ready_missions
    for p in self._away_poshimo:
      mission = AwayMission(id=int(p.mission_id))
      if mission.complete:
        ready_missions.append(mission)
    return ready_missions

  def swap(self, poshimo:Poshimo) -> str:
    ''' swap out the active poshimo '''
    old_poshimo = self._active_poshimo
    self._poshimo_sac.append(self._active_poshimo)
    self._poshimo_sac.remove(poshimo)
    self.active_poshimo = poshimo # fire setters
    self.poshimo_sac = self._poshimo_sac
    return f"{self} swapped out {old_poshimo} for {poshimo}!"

  def catch_fish(self, fish) -> int:
    ''' add a fish to this player's log '''
    with AgimusDB() as query:
      sql = "INSERT INTO poshimo_fishing_log (trainer,fish,location,length) VALUES(%s,%s,%s,%s);"
      vals = (self.id, fish.name, self.location, fish.length)
      query.execute(sql,vals)
      last_id = query.lastrowid
    return last_id

  def get_fishing_log(self) -> List[PoshimoFish]:
    ''' get a list of the last 10 fish this trainer has caught, sorted by length '''
    with AgimusDB(dictionary=True) as query:
      sql = "SELECT fish, length FROM poshimo_fishing_log WHERE trainer = %s ORDER BY length DESC LIMIT 10"
      vals = (self.id,)
      query.execute(sql,vals)
      fishing_log = query.fetchall()
    final_log = []
    for fish in fishing_log:
      final_log.append(PoshimoFish(name=fish["fish"], length=fish["length"]))
    return final_log

  def add_item(self, item:PoshimoItem, amount:int=1):
    ''' 
    add an item to this trainer's inventory 
    pass `amount` to add multiple items!
    '''
    temp_inventory = self._inventory
    if temp_inventory.get(item.name.lower()):
      temp_inventory[item.name.lower()]["amount"] += amount
    else:
      temp_inventory[item.name.lower()] = {
        "item": item.name,
        "amount": amount
      }
    self.inventory = temp_inventory
  
  def remove_item(self, item:PoshimoItem):
    temp_inventory = self._inventory
    temp_inventory[item.name.lower()]["amount"] -= 1
    self.inventory = temp_inventory

  def use_item(self, item:PoshimoItem, poshimo:Poshimo=None, move:PoshimoMove=None):
    self.remove_item(item)
    item_type = item.type
    return_str = "```ansi\n"
    
    if poshimo:
      original_hp = poshimo.hp
    if move:
      original_stamina = move.stamina
    
    if item_type is ItemTypes.RESTORE:
      restore_type = item.function_code
      if restore_type == FunctionCodes.HP:
        poshimo.hp += item.power
        return_str += f"{Style.BRIGHT}{poshimo.display_name}{Style.RESET_ALL} regained {Fore.LIGHTGREEN_EX}{poshimo.hp - original_hp}{Fore.RESET} HP! 💖"
      if restore_type == FunctionCodes.HP_ALL:
        for p in self.list_all_poshimo():
          p.hp += item.power
        return_str += f"All your poshimo have regained {Fore.LIGHTGREEN_EX}{item.power}{Fore.RESET} HP! 💖"
      if restore_type == FunctionCodes.STAMINA:
        move.stamina += item.power
        return_str += f"{Style.BRIGHT}{poshimo.display_name}'s{Style.RESET_ALL} {Fore.CYAN}{move.display_name}{Fore.RESET} regained {Fore.LIGHTBLUE_EX}{move.stamina - original_stamina}{Fore.RESET} stamina! ✨"
      if restore_type == FunctionCodes.STAMINA_ALL:
        for p in self.list_all_poshimo():
          for m in p.move_list:
            m.stamina += item.power
        return_str += f"All your Poshimo's moves have regained {Fore.LIGHTBLUE_EX}{item.power}{Fore.RESET} stamina! ✨"

      return_str += "```"
      return return_str

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
  def losses(self, amt) -> None:
    self._losses = max(0, amt)
    self.update("losses", self._losses)

  @property
  def active_poshimo(self) -> Poshimo:
    return self._active_poshimo
  
  @active_poshimo.setter
  def active_poshimo(self, poshimo:Poshimo) -> None:
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
  def inventory(self, obj:Dict[str,InventoryDict]) -> None:
    for key,idata in list(obj.items()):
      if idata["amount"] > 0:
        self._inventory[key] = { "item": idata["item"], "amount": idata["amount"] }
      else:
        self._inventory.pop(key, None) # delete item from inventory if its 0 or less
    #self._inventory = obj
    if self._inventory:
      item_json = json.dumps([(i["item"].name, i["amount"]) for i in self._inventory.values()])
    else:
      item_json = json.dumps([])
    self.update("inventory", item_json) # will probably need json
    
  @property
  def location(self) -> str:
    return self._location

  @location.setter
  def location(self, value:str) -> None:
    self._location = value.lower()
    self.update("location", self._location)

  @property
  def away_poshimo(self) -> List[Poshimo]:
    return self._away_poshimo
  @away_poshimo.setter
  def away_poshimo(self, val):
    self._away_poshimo = val
    if len(self._away_poshimo) > 0:
      away_json = json.dumps([i.id for i in self._away_poshimo])
    else:
      away_json = json.dumps([])
    self.update("away_poshimo", away_json)

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
  def status(self, val) -> None:
    self._status:TrainerStatus = val
    self.update("status", self._status.value)

  @property
  def buckles(self) -> int:
    return self._buckles

  @buckles.setter
  def buckles(self, val) -> None:
    self._buckles = val
    self.update("buckles", self._buckles) # TODO: all this

  @property
  def poshimo_sac(self) -> list:
    return list(set(self._poshimo_sac))

  @poshimo_sac.setter
  def poshimo_sac(self, obj) -> None:
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
  def shimodaepedia(self, obj) -> None:
    self._shimodaepedia = obj

  @property
  def locations_unlocked(self) -> list:
    return self._locations_unlocked
  
  @locations_unlocked.setter
  def locations_unlocked(self, obj) -> None:
    self._locations_unlocked = obj
    if self._locations_unlocked:
      loc_json = json.dumps(list(self._locations_unlocked))
    else:
      loc_json = json.dumps([])
    self.update("locations_unlocked", loc_json)