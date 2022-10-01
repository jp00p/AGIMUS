""" Poshimo and their moves, types and personalities """
from common import *
from math import sqrt, floor, log10
from typing import List
import csv
from ..poshimo import PoshimoMove,PoshimoPersonality, PoshimoType, PoshimoStat

MAX_POSHIMO_LEVEL = 99

with open("pocket_shimodae/data/shimodaepedia.csv") as file:
  # load the base poshimo data from file
  # will eventually get merged with DB data for "real" poshimo
  csvdata = csv.DictReader(file)
  pdata = {}
  for row in csvdata:
    pdata[row["name"].lower()] = {
      "name" : row.get("name", ""),
      "dex_id" : row.get("id", 0),
      "type_1" : row.get("type_1", ""),
      "type_2" : row.get("type_2", ""),
      "attack" : (row.get("attack", 0),0),
      "defense" : (row.get("defense", 0),0),
      "special_attack" : (row.get("special_attack", 0),0),
      "special_defense" : (row.get("special_defense", 0),0),
      "speed" : (row.get("speed", 0),0),
      "hp" : row.get("hp",0),
      "move_list" : [
        row.get("move_1","").lower(), 
        row.get("move_2","").lower(), 
        row.get("move_3","").lower(), 
        row.get("move_4","").lower()
      ]
    }
  logger.info(f"{Back.LIGHTMAGENTA_EX}{Fore.LIGHTYELLOW_EX}Poshimo {Style.BRIGHT}BASE POSHIMO DATA{Style.RESET_ALL} loaded!{Fore.RESET}{Back.RESET}")

class Poshimo(object):
  """A Pocket Shimoda!
  ----
  We couldn't have a game without these.

  You do not create these from scratch, they are predefined in the CSV and DB.
  """

  def __init__(self, name:str=None, level:int=1, id:int=None, owner:int=None, is_wild:bool=False):
    self.id:int = id
    self.name:str = name
    self._owner:int = owner
    self.is_wild:bool = is_wild

    self.poshimodata:dict = {} # this will hold our file and db stats eventually
    if self.name:
      self.poshimodata = pdata[self.name.lower()] # fire this up early if we have it
    
    self._attack:PoshimoStat = PoshimoStat(0)
    self._defense:PoshimoStat = PoshimoStat(0)
    self._special_attack:PoshimoStat = PoshimoStat(0)
    self._special_defense:PoshimoStat = PoshimoStat(0)
    self._speed:PoshimoStat = PoshimoStat(0)
    
    self._xp:int = 0
    self._display_name:str = self.name
    self._personality:PoshimoPersonality = PoshimoPersonality()
    self._level:int = level
    self._move_list:List[PoshimoMove] = [] 
    
    if self.name:
      # loading base poshimo data from file
      self._display_name = self.name # npc is always the proper name
      self._level = level # default is 1
      self._personality = PoshimoPersonality() # load random personality
      self._move_list = self.init_move_list()

    if is_wild and not self.id:
      # create new wild poshimo in the db (so it can be persistent in case bot restarts)
      self.id = self.save()

    if self.id:
      # load poshimo from db if it has an id
      self.load()
      self._owner = self.poshimodata["owner"]
    
    # poshimodata should be fully loaded now, if not ... wha happen???
    
    self._level = self.poshimodata.get("level", 1)
    self._name = self.poshimodata["name"]
    self._display_name = self.poshimodata.get("display_name")
    self._personality = PoshimoPersonality(self.poshimodata.get("personality"))
    self._hp = self.poshimodata.get("hp", 1)
    self._max_hp = self.poshimodata.get("max_hp", self._hp) # only real poshimo have max_hp
    
    self.types = (
      self.poshimodata["type_1"],
      self.poshimodata["type_2"]
      #PoshimoType(self.poshimodata["type1"]), 
      #PoshimoType(self.poshimodata["type2"])
    ) # types never(?) change

    self._attack:PoshimoStat = PoshimoStat(self.poshimodata["attack"][0], self.poshimodata["attack"][1])
    self._defense:PoshimoStat = PoshimoStat(self.poshimodata["defense"][0], self.poshimodata["defense"][1])
    self._special_attack:PoshimoStat = PoshimoStat(self.poshimodata["special_attack"][0], self.poshimodata["special_attack"][1])
    self._special_defense:PoshimoStat = PoshimoStat(self.poshimodata["special_defense"][0], self.poshimodata["special_defense"][1])
    self._speed:PoshimoStat = PoshimoStat(self.poshimodata["speed"][0], self.poshimodata["speed"][1])
    self._xp:int = 0
    self._last_damaging_move:PoshimoMove = None
    self.status = None # TODO: Statuses      

    # 
    # end of __init__ =====================================================
  
  def load_wild(self) -> None:
    """ 
    load a wild poshimo (computer controlled) 
    assumes this poshimo has an id
    """
    with AgimusDB(dictionary=True) as query:
      sql = """
      SELECT * FROM poshimodae WHERE id = %s LIMIT 1
      """
      vals = (self.id,)
      query.execute(sql, vals)
      results = query.fetchone()
    self.poshimodata = dict(results)
    temp_pdata = pdata[results["name"].lower()]
    temp_pdata["id"] = results["id"]
    self.poshimodata.update(temp_pdata)
    self._move_list = self.load_move_list(results["move_list"])
    logger.info(f"Loaded wild poshimo: {Fore.YELLOW}{self.poshimodata}{Fore.RESET}")

  def load(self) -> None:
    """ 
    load a human-controlled poshimo 
    assumes this poshimo has an id
    """
    logger.info(f"Attempting to load poshimo: {self.id}")
    with AgimusDB(dictionary=True) as query:
      sql = '''
      SELECT poshimodae.*, poshimo_trainers.id as owner FROM poshimodae
        LEFT JOIN poshimo_trainers
        ON poshimo_trainers.id = poshimodae.owner 
      WHERE poshimodae.id = %s LIMIT 1
      '''
      vals = (self.id,)
      query.execute(sql, vals)
      results:dict = query.fetchone()
    self.poshimodata = dict(results)
    logger.info(f"What's goin on here: {self.poshimodata}")
    temp_pdata = pdata[results["name"].lower()] # load poshimo data from file
    
    temp_pdata["id"] = results.get("id", 0) # gotta update the original ID from the poshimodex
    temp_pdata["max_hp"] = results.get("max_hp")
    temp_pdata["hp"] = results.get("hp")
    
    self.poshimodata.update(temp_pdata) # merge with db info (so its not a base poshimo)
    self._move_list = self.load_move_list(results.get("move_list")) # unpack json moves
    #logger.info(f"Loaded poshimo: {Fore.GREEN}{self.poshimodata}{Fore.RESET}")
  
  def save(self) -> int:
    """ 
    save this poshimo to the db (when giving a trainer a Poshimo) 
    returns the ID of this poshimo in the db
    """
    self.poshimodata = pdata[self.name.lower()] # base data
    self._level = 1 #TODO: leveling
    self._display_name = self.name
    self._personality = PoshimoPersonality()
    self._hp = self.poshimodata.get("hp", 1)
    self._max_hp = self._hp
    logger.info(f"Preparing this poshimo for creation: DISPLAY NAME: {self._display_name} OWNER: {self.owner} PERSONALITY: {self._personality}")

    with AgimusDB() as query:
      
      sql = """
      INSERT INTO poshimodae 
        (id, owner, name, display_name, level, xp, hp, max_hp, attack, defense, special_attack, special_defense, speed, personality, move_list) 
        VALUES 
          (%(id)s, %(owner)s, %(name)s, %(display_name)s, %(level)s, %(xp)s, %(hp)s, %(max_hp)s, %(attack)s, %(defense)s, %(special_attack)s, %(special_defense)s, %(speed)s, %(personality)s, %(move_list)s)
      """
      vals = {
        "id" : self.id,
        "owner" : self.owner,
        "name" : self.name,
        "display_name" : self._display_name,
        "level" : self._level,
        "xp" : self._xp,
        "hp" : self._hp,
        "max_hp" : self._hp,
        "attack" : self._attack.to_json(),
        "defense" : self._defense.to_json(),
        "special_attack" : self._special_attack.to_json(),
        "special_defense" : self._special_defense.to_json(),
        "speed":self._speed.to_json(),
        "personality":self._personality.name.lower(),
        "move_list":self.dump_move_list()
      }
      query.execute(sql, vals)
      #logger.info(f"Saving poshimo: {vals}")
      poshi_row = query.lastrowid
      self.id = poshi_row
      logger.info(f"Save successful, Poshimo inserted into DB: {self.id}")
    return self.id

  def update(self, col_name, value=None) -> None:
    """ 
    update a col in the db for this poshimo
    used by setters to do their magic
    """
    if not self.id: # only update poshimo in the DB
      return
    #logger.info(f"{Style.BRIGHT}Attempting to update Poshimo {self.id}'s {Fore.CYAN}{col_name}{Fore.RESET}{Style.RESET_ALL} with new value: {Fore.LIGHTGREEN_EX}{value}{Fore.RESET}")
    with AgimusDB() as query:
      sql = f"UPDATE poshimodae SET {col_name} = %s WHERE id = %s" # col_name is a trusted input or so we hope
      vals = (value, self.id)
      query.execute(sql, vals)

  @property
  def owner(self) -> int:
    return self._owner
  @owner.setter
  def owner(self, val):
    self._owner = val
    self.update("owner", self._owner)
  
  @property
  def max_hp(self) -> int:
    return int(self._max_hp)

  @max_hp.setter
  def max_hp(self,val:int):
    self._max_hp = int(max(1, int(val))) # max_hp can't go below 1
    self.update("max_hp", self._max_hp)

  @property
  def attack(self) -> PoshimoStat:
    return self._attack
  @attack.setter
  def attack(self, val, stage=None):
    if not stage:
      stage = self._attack.stage
    self._attack = PoshimoStat(max(0, val), stage)
    self.update("attack", self._attack.to_json())

  @property
  def defense(self) -> PoshimoStat:
    return self._defense
  @defense.setter
  def defense(self,val,stage=None):
    if not stage:
      stage = self._defense.stage
    self._defense = PoshimoStat(max(0, val), stage)
    self.update("defense", self._defense.to_json())

  @property
  def special_attack(self) -> PoshimoStat:
    return self._special_attack
  @special_attack.setter
  def special_attack(self,val,stage=None):
    if not stage:
      stage = self._special_attack.stage
    self._special_attack = PoshimoStat(max(0, val), stage)
    self.update("special_attack", self._special_attack.to_json())

  @property
  def special_defense(self) -> PoshimoStat:
    return self._special_defense
  @special_defense.setter
  def special_defense(self,val,stage=None):
    if not stage:
      stage = self._special_defense.stage
    self._special_defense = PoshimoStat(max(0, val), stage)
    self.update("special_defense", self._special_defense)    

  @property
  def speed(self) -> PoshimoStat:
    return self._speed
  @speed.setter
  def speed(self,val,stage=None):
    if not stage:
      stage = self._speed.stage
    self._speed = PoshimoStat(max(0, val), 0)
    self.update("speed", self._speed.to_json())

  @property
  def hp(self) -> int:
    return int(self._hp)
  
  @hp.setter
  def hp(self, val:int):
    self._hp = max(0, min(int(val), int(self._max_hp))) # clamp hp between 0 and max_hp
    self.update("hp", self._hp)

  @property
  def level(self) -> int:
    return self._level

  @level.setter
  def level(self, val):
    '''TODO: handle level up stuff '''
    self._level = min(MAX_POSHIMO_LEVEL, max(0, val))
    self.update("level", self._level)

  @property
  def xp(self) -> int:
    return self._xp
  @xp.setter
  def xp(self, val:int):
    self._xp = max(0, int(val))
    self.update("xp", self._xp)

  @property
  def move_list(self) -> List[PoshimoMove]:
    return self._move_list
  
  @move_list.setter
  def move_list(self, obj:List[PoshimoMove]):
    ''' set move list and update json in db '''
    if not isinstance(obj,list):
      return
    self._move_list = obj
    self.update("move_list", self.dump_move_list())

  @property
  def display_name(self) -> str:
    return self._display_name

  @display_name.setter
  def display_name(self, val):
    self._display_name = val[0:48] # don't let them have infinite names
    self.update("display_name", self._display_name)

  @property
  def personality(self) -> PoshimoPersonality:
    return self._personality
  @personality.setter
  def personality(self, val:PoshimoPersonality):
    self._personality = val
    self.update("personality", self._personality.name)

  def list_stats(self, for_battle=False) -> dict:
    """ returns a dictionary of this poshimo's stats """
    stats:dict = {}
    if not for_battle:
      stats_to_display = [
        "level", "xp", "personality", 
        "hp", "attack", "defense", 
        "special_attack", "special_defense", 
        "speed",
      ]
      for stat in stats_to_display:
        stats[stat] = getattr(self, stat)
    # add hp.max_hp to our stats list
    stats["hp"] = f"{self.hp}/{self.max_hp}"
    return stats

  def __str__(self) -> str:
    if self.id:
      return f"{self._display_name} {self.id}"
    else:
      return f"{self._display_name}"

  def init_move_list(self) -> List[PoshimoMove]:
    """ 
    initialize a movelist from file 
    returns a list of PoshimoMoves
    """
    temp_move_list:list = []
    for move in self.poshimodata["move_list"]:
      if move is not None:
        temp_move_list.append(PoshimoMove(name=move))
    #logger.info(f"Move list init: {temp_move_list}")
    return temp_move_list

  def dump_move_list(self) -> str:
    """ 
    dump move list to json for DB insertion 
    returns a json string
    """
    db_move_list:list = []
    for move in self.move_list:
      if move:
        db_move_list.append(move.to_json())
    #logger.info(f"Dumping json: {db_move_list}")
    return json.dumps(db_move_list)
  
  def load_move_list(self, movelist) -> List[PoshimoMove]:
    """ 
    load move list from json 
    returns a list of PoshimoMoves
    """
    #logger.info(f"Move list to load from JSON: {movelist}")
    temp_move_list = []
    loaded_move_list = json.loads(movelist)
    for move in loaded_move_list:
      if move and move != "":
        dbmove = PoshimoMove(name=move["name"], stamina=move["stamina"], max_stamina=move["max_stamina"])
        #logger.info(f"Loading {move['name']} from DB: {dbmove}")
        temp_move_list.append(dbmove)
    return temp_move_list


""" from ultranurd 
  
import sys
import math
​
class Experience:
    def slow(self, level):
        return 5 * level3 / 4
​
    def medium_slow(self, level):
        return 6 * level3 / 5 - 15 * level2 + 100 * level - 140
​
    def medium_fast(self, level):
        return level3
​
    def fast(self, level):
        return 4 * level3 / 5
​
    def fluctuating(self, level):
        if level < 15:
            factor = (math.floor((level + 1)/3.0) + 24)/50
        elif level < 36:
            factor = (level + 14)/50
        elif level < 100:
            factor = (math.floor(level/2.0) + 32)/50
        return factor * level3
​
    def erratic(self, level):
        if level < 50:
            factor = (100 - level)/50
        elif level < 68:
            factor = (150 - level)/100
        elif level < 98:
            factor = math.floor((1911 - 10level)/3.0)/500
        elif level < 100:
            factor = (160 - level)/100
        return factor level*3
​
def experience(leveling, level):
    print(getattr(Experience(), leveling)(int(level)))
​
if name == "main":
    experience(sys.argv[1:])
  
  """
