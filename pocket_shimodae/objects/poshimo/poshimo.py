from common import *
from math import sqrt, floor, log10
from typing import List
import csv
from . import PoshimoMove, PoshimoPersonality, PoshimoType
from .personality import PoshimoPersonality

with open("pocket_shimodae/data/shimodaepedia.csv") as file:
  # load the base poshimo data from file
  csvdata = csv.DictReader(file)
  pdata = {}
  for id,row in enumerate(csvdata):
    pdata[row["name"]] = {
      "name" : row["name"],
      "id" : id,
      "type1" : row["type1"],
      "type2" : row["type2"],
      "base_attack" : row["base_attack"],
      "attack" : row["base_attack"],
      "base_defense" : row["base_defense"],
      "defense" : row["base_defense"],
      "base_special_attack" : row["base_special_attack"],
      "special_attack" : row["base_special_attack"],
      "base_special_defense" : row["base_special_defense"],
      "special_defense" : row["special_defense"],
      "base_speed" : row["speed"],
      "base_evasion" : row["evasion"],
      "speed" : row["speed"],
      "evasion" : row["evasion"],
      "max_hp" : row["hp"],
      "hp" : row["hp"],
      "move_list" : [
        row["move1"], row["move2"], row["move3"], row["move4"]
      ]
    }
  logger.info(f"Poshimo data loaded!")


def getset(arg, proptype):
  """ 
  very sneaky util for making lots of getters/setters at once 
  arg: the variable name that should get the property wrapper
  proptype: what kind of property is this? only using "int" for now
  """
  logger.info(f"Adding getset for {arg}")
  @property
  def prop(self):
    _arg = '_' + arg
    return getattr(self, _arg)
  @prop.setter
  def prop(self, val):
    _arg = '_' + arg
    if proptype == "int":
      setattr(self, _arg, max(val, 0)) # dont let ints go below 0
      self.update(arg, max(val, 0))
    else:
      setattr(self, _arg, val)
      self.update(arg, val)
  return prop




MAX_LEVEL = 100

class Stats():
  """ 
  holds some info about a poshimo's stat definitions 
  ...i probably should have made all the stats part of this... 
  then i could have done self.stats = Stats(level=x) abd referred to stats with self.stats.whatever ugh
  maybe some other day!
  """
  def __init__(self):
    # these are the names of all the attrs that will get the basic getter/setter
    # NOTE: there's still custom setters/getters in Poshimo too!
    self.int_keys = [
      'owner',
      'max_hp', 
      'attack', 
      'defense', 
      'special_attack', 
      'special_defense', 
      'evasion', 
      'speed', 
      'base_attack', 
      'base_defense', 
      'base_special_attack', 
      'base_special_defense', 
      'base_evasion', 
      'base_speed', 
      'xp'
    ]

    self.str_keys = [
      'display_name', 
      'personality'
    ]


class Poshimo(object):
  """
  A Pocket Shimoda!\n
  We couldn't have a game without these.
  You do not create these from scratch, they are predefined in the CSV or DB.\n
  ----

  1. Get a specific Poshimo's base data or generate one for an NPC:
    `Poshimo(name="pikachu")` 
    or 
    `Poshimo(name="pikachu", level=5)`
  
  2. Load a Poshimo from DB:
    `Poshimo(id=12)`
 
  4. Get a random Poshimo:
    `Poshimo()` or `Poshimo(level=15)`
  """

  def __init__(self, name:str=None, level:int=1, id:int=None, owner:int=None):
    self.id:int = id
    self.name:str = name
    self.owner = self._owner = owner

    self.poshimodata = {} # this will hold our file and db stats eventually
    if self.name:
      self.poshimodata = pdata[self.name] # fire this up early if we have it
    
    # init this shit
    # these attrs use basic int setters
    self.max_hp = self._max_hp = 0
    self.attack = self._attack = 0
    self.defense = self._defense = 0
    self.special_attach = self._special_attack = 0
    self.special_defense = self._special_defense = 0
    self.base_attack = self._base_attack = 0
    self.base_defense = self._base_defense = 0
    self.base_special_attack = self._base_special_attack = 0
    self.base_special_defense = self._base_special_defense = 0
    self.base_evasion = self._base_evasion = 0
    self.base_speed = self._base_speed = 0
    self.evasion = self._evasion = 0
    self.speed = self._speed = 0
    self.xp = self._xp = 0
    # these attrs get special str setters
    self.display_name:str = None
    self._display_name:str = None
    self.personality:PoshimoPersonality = None
    self._personality:PoshimoPersonality = None
    
    # these attrs get special handmade setters (no need for double init)
    self._hp:int = 0
    self._level:int = level
    self._move_list:List[PoshimoMove] = []
    # done with the init shit
    
    if self.id:
      self.load()
    else:      
      if not self.name:
        self.poshimodata = pdata[self.name] # load the base poshimo data
      self._display_name = self.name # npc is always the proper name
      self._level = level # default is 1
      self._personality = PoshimoPersonality() # load random personality

    # we should now have self.poshimodata full of data
    # either a real poshimo or a freshly created one
    # now lets fill in the real stats!
    
    self.types = (
      PoshimoType(self.poshimodata["type1"]), 
      PoshimoType(self.poshimodata["type2"])
    ) # types never(?) change

    self._base_attack = self.poshimodata["base_attack"]
    self._base_defense = self.poshimodata["base_defense"]
    
    self._attack = self.poshimodata["attack"]
    self._defense = self.poshimodata["defense"]
    
    self._base_special_attack = self.poshimodata["base_special_attack"]
    self._base_special_defense = self.poshimodata["base_special_defense"]
    
    self._special_attack = self.poshimodata["special_attack"]
    self._special_defense = self.poshimodata["special_defense"]
    
    self._base_evasion = self.poshimodata["base_evasion"]
    self._base_speed = self.poshimodata["base_speed"]

    self._evasion = self.poshimodata["evasion"]
    self._speed = self.poshimodata["speed"]
    
    self._max_hp = self.poshimodata["hp"]
    self._hp = self.poshimodata["max_hp"]
    
    self._xp = 0
    
    self.status = None # TODO: Statuses

    for move in self.poshimodata["move_list"]:
      if move:
        self._move_list.append(PoshimoMove(move))
    
    if not self._owner and self._level > 1:
      pass # generate leveled up stats for this NPC pokemon

    self.set_setters_and_getters()

    # 
    # end of __init__ =====================================================
  
  def set_setters_and_getters(self):
    # register the setters and getters for the basic attrs (int_keys, str_keys)
    for proptype in ['int', 'str']:
      for key in getattr(Stats(), f"{proptype}_keys"):
        exec(f"{key} = getset('{key}', '{proptype}')")
        # what this does:
        # e.g.: for the key "xp" with proptype "int", it will create this:

        # @property
        # def xp(self):
        #  return self._xp
        # 
        # @xp.setter
        # def xp(self,val):
        #  self._xp = max(0, val)
        #  self.update("xp", val) 


  def load(self):
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
      results = query.fetchone()
      self.poshimodata = dict(results)
      temp_pdata = pdata[results["name"]] # load poshimo data from file
      temp_pdata["id"] = results["id"] # gotta update the original ID from the poshimodex
      self._owner = self.poshimodata["owner"]
      self.poshimodata.update(temp_pdata) # merge with db info (so its not a base poshimo)
      logger.info(f"POSHIMODATA: {self.poshimodata}")
      self._level = self.poshimodata["level"]
      self._name = self.poshimodata["name"]
      self._display_name = self.poshimodata["display_name"]
      self._personality = PoshimoPersonality(self.poshimodata["personality"])
      logger.info(f"Loaded poshimo: {Fore.GREEN}{self.poshimodata}{Fore.RESET}")
  
  def create(self):
    """ initialize a new poshimo for DB insertion """
    if not self.owner:
      return
    self.poshimodata = pdata[self.name] # base data
    self._level = 1 #TODO: levels
    self.name = self.poshimodata["name"]
    self._display_name = self.name # default name
    self._personality = PoshimoPersonality()
    logger.info(f"Attempting to insert poshimo into db: {self.poshimodata}")
    return self.save()

  def save(self) -> int:
    self.poshimodata = pdata[self.name] # base data
    """
    saves to the db or updates the db with this poshimo's data
    """
    with AgimusDB() as query:
      
      sql = """
      INSERT INTO poshimodae 
        (
          id, owner, name, display_name, level, xp, hp, max_hp,
          base_attack, base_defense, attack, defense,
          base_special_attack, base_special_defense, special_attack, special_defense,
          base_speed, base_evasion, speed, evasion,
          personality, move_list
        ) 
        VALUES 
          (
            %(id)s, %(owner)s, %(name)s, %(display_name)s, %(level)s, %(xp)s, %(hp)s, %(max_hp)s,            
            %(base_attack)s,%(base_defense)s,%(attack)s, %(defense)s, 
            %(base_special_attack)s, %(base_special_defense)s, %(special_attack)s, %(special_defense)s, 
            %(base_speed)s, %(base_evasion)s, %(speed)s, %(evasion)s,
            %(personality)s, %(move_list)s    
          ) 
      ON DUPLICATE KEY UPDATE 
        display_name=%(display_name)s, level=%(level)s, xp=%(xp)s, owner=%(owner)s, hp=%(hp)s, max_hp=%(max_hp)s,
        base_attack=%(base_attack)s, base_defense=%(base_defense)s, attack=%(attack)s, defense=%(defense)s, 
        base_special_attack=%(base_special_attack)s, base_special_defense=%(base_special_defense)s, special_attack=%(special_attack)s, special_defense=%(special_defense)s, 
        base_speed=%(base_speed)s, base_evasion=%(base_evasion)s, speed=%(speed)s, evasion=%(evasion)s,
        personality=%(personality)s, move_list=%(move_list)s
      """
      vals = {
        "id" : self.id,
        "owner" : self.owner,
        "name" : self.name,
        "display_name" : self.display_name,
        "personality" : self.personality.name.lower(),
        "level" : self.level,
        "xp" : self.xp,
        "hp" : self.hp,
        "max_hp" : self.max_hp,
        "base_attack" : self.base_attack,
        "base_defense" : self.base_defense,
        "attack" : self.attack,
        "defense" : self.defense,
        "base_special_attack":self.base_special_attack,
        "base_special_defense":self.base_special_defense,
        "special_attack":self.special_attack,
        "special_defense":self.special_defense,
        "base_speed":self.base_speed,
        "base_evasion":self.base_evasion,
        "speed":self.speed,
        "evasion":self.evasion,
        "personality":self.personality.name,
        "move_list":self.move_list_json()
      }
      logger.info(f"Attempting to save poshimo: {vals}")
      query.execute(sql, vals)
      logger.info(f"Saving poshimo: {vals}")
      poshi_row = query.lastrowid
      self.id = poshi_row
      logger.info(f"Save successful, Poshimo inserted or updated: {self.id}")
    return self.id

  def update(self, col_name, value=None) -> None:
    """ 
    update a col in the db for this poshimo 
    """
    if not self.id and not self.owner: # only human-owned poshimo please
      return

    logger.info(f"{Style.BRIGHT}💾 Attempting to update Poshimo {self.id}'s {Fore.CYAN}{col_name}{Fore.RESET}{Style.RESET_ALL} with new value: {Fore.LIGHTGREEN_EX}{value}{Fore.RESET}")
    
    with AgimusDB() as query:
      sql = f"UPDATE poshimodae SET {col_name} = %s WHERE id = %s" # col_name is a trusted input or so we hope
      vals = (value, self.id)
      query.execute(sql, vals)

  def move_list_json(self) -> str:
    ''' dump the move list into json '''
    return json.dumps([move.name if move else "" for move in self.move_list])


  @property
  def hp(self):
    return self._hp
  
  @hp.setter
  def hp(self, val):
    self._hp = max(0, min(val, self._max_hp)) # clamp hp between 0 and max_hp
    self.update("hp", self._hp)

  @property
  def level(self):
    return self._level

  @level.setter
  def level(self, val):
    '''TODO: handle level up stuff '''
    self._level = max(val, 0)
    self.update("level", self._level)

  @property
  def move_list(self) -> List[PoshimoMove]:
    return self._move_list
  
  @move_list.setter
  def move_list(self, obj:List[PoshimoMove]):
    ''' set move list and update json in db '''
    self._move_list = obj
    self.update("move_list", self.move_list_json())
  
  

  def list_stats(self) -> dict:
    """ returns a dictionary of this poshimo's stats """
    stats_to_display = [
      "level", "xp", "personality", 
      "hp", "attack", "defense", 
      "special_attack", "special_defense", 
      "speed", "evasion"
    ]
    stats = {}
    
    for stat in stats_to_display:
      stats[stat] = getattr(self, stat)
    # add hp.max_hp to our stats list
    stats["hp"] = f"{self.hp}/{self.max_hp}"    
    return stats

  def __str__(self) -> str:
    return f"{self._display_name}: ({[t for t in list(self.types)]})"
  


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
