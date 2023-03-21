""" Poshimo and their moves, types, stats and personalities """
from common import *
from math import sqrt, floor, log10
from typing import List
import csv
from enum import Enum, auto
from . import PoshimoMove, PoshimoPersonality, PoshimoType, PoshimoStat
from .experience import get_experience

MAX_POSHIMO_LEVEL = 99
STAT_NAMES = ["attack", "defense", "special_attack", "special_defense", "speed"]

with open("pocket_shimodae/data/Poshimodaepaedia.csv") as file:
  csvdata = csv.DictReader(file)
  base_poshimo_data = {}
  for id,row in enumerate(csvdata):
    base_poshimo_data[row["name"].lower()] = {
      "name" : row.get("name", ""),
      "dex_id" : row.get("id", int(id+1)),
      "type_1" : row.get("type_1", ""),
      "type_2" : row.get("type_2", ""),
      "attack" : (row.get("attack", 0),0,0),
      "defense" : (row.get("defense", 0),0,0),
      "special_attack" : (row.get("special_attack", 0),0,0),
      "special_defense" : (row.get("special_defense", 0),0,0),
      "speed" : (row.get("speed", 0),0,0),
      "hp" : row.get("hp",0),
      "max_hp" : row.get("hp",0),
      "leveling_type" : row.get("leveling_type", "medium_slow"),
      "move_list" : [
        row.get("move_1","").lower(),
        row.get("move_2","").lower(),
        row.get("move_3","").lower(),
        row.get("move_4","").lower()
      ]
    }
  ps_log(f"Total Poshimo: {len(base_poshimo_data)}")


class PoshimoStatus(Enum):
  IDLE = auto()
  DEAD = auto()
  AWAY = auto()
  WILD = auto()

  def __str__(self):
    return f"{str(self.name).title()}"


class Poshimo(object):
  """
  A Pocket Shimoda!
  ----
  We couldn't have a game without these.

  You do not create these from scratch, they are predefined in the CSV and DB.

  Pass a name or ID to retrieve your Poshimo
  """

  def __init__(self, name:str=None, level:int=1, id:int=None, owner:int=None, is_wild:bool=False):
    self.id:int = id
    self.name:str = name
    self._owner:int = owner
    self.is_wild:bool = is_wild
    self._in_combat = False
    self.types = []

    self._pending_moves = None
    self.levels_gained = []
    self.stat_increases = {}

    self._xp:int = 0
    self._display_name:str = self.name
    self._personality:PoshimoPersonality = PoshimoPersonality()
    self._level:int = level
    self._move_list:List[PoshimoMove] = []
    self._mission_id = None
    self._status = PoshimoStatus.IDLE
    self._held_item = None
    
    self.poshimodata:dict = {} # this will hold our file and db stats eventually
    
    if self.name:
      self.poshimodata = base_poshimo_data[self.name.lower()] # fire this up early if we have it
      # init base stats (no stage, no xp)
      self._attack:PoshimoStat = PoshimoStat(self.poshimodata["attack"][0], 0, 0)
      self._defense:PoshimoStat = PoshimoStat(self.poshimodata["defense"][0], 0, 0)
      self._special_attack:PoshimoStat = PoshimoStat(self.poshimodata["special_attack"][0], 0, 0)
      self._special_defense:PoshimoStat = PoshimoStat(self.poshimodata["special_defense"][0], 0, 0)
      self._speed:PoshimoStat = PoshimoStat(self.poshimodata["speed"][0], 0, 0)
      self._display_name = self.name # npc is always the proper name
      self._level = level # default is 1
      self._personality = PoshimoPersonality() # load random personality
      self._move_list = self.init_move_list()
      logger.info(f"INIT MOVE LIST")
      for move in self._move_list:
        logger.info(f"{move.name} {move.stamina}/{move.max_stamina}")

    if not self.id and is_wild:
      # new wild poshimo created
      self.id = self.save()
    
    if self.id:
      # load poshimo from db if it has an id
      self.load()
      self._owner = self.poshimodata["owner"]
    
    self._level:int = int(self.poshimodata.get("level", 1))
    self.name = self.poshimodata["name"]
    self._display_name:str = self.poshimodata.get("display_name")
    self._personality:PoshimoPersonality = PoshimoPersonality(self.poshimodata.get("personality"))
    self._hp:int = int(self.poshimodata.get("hp", 1))
    self.leveling_type:str = self.poshimodata["leveling_type"]
    self.next_level:int = get_experience(self.leveling_type, self._level+1)

    logger.info(f"Leveling type: {self.leveling_type} - Next level: {self.next_level}")

    if self._hp <= 0:
      self.status = PoshimoStatus.DEAD

    self._max_hp:int = self.poshimodata.get("max_hp", self._hp)

    for type in ["type_1", "type_2"]:
      if self.poshimodata[type]:
        self.types.append(PoshimoType(name=self.poshimodata[type]))

    logger.info(f"BASE XP: {self.base_xp()} XP GIVEN: {self.xp_given()}")
    self._last_damaging_move:PoshimoMove = None # TODO: implement

    # 
    # end of __init__ =====================================================


  def load(self) -> None:
    """ 
    load a human-controlled poshimo 
    assumes this poshimo has an id
    """
    #logger.info(f"Attempting to load poshimo: {self.id}")
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
    temp_base_poshimo_data = base_poshimo_data[results["name"].lower()] # load poshimo data from file
    
    temp_base_poshimo_data["id"] = results.get("id", 0) # gotta update the original ID from the poshimodex
    temp_base_poshimo_data["max_hp"] = results.get("max_hp")
    temp_base_poshimo_data["hp"] = results.get("hp")
    
    pstats = ["attack", "defense", "special_attack", "special_defense", "speed"]
    for stat in pstats:
      temp_base_poshimo_data[stat] = json.loads(results.get(stat, "[0,0,0]"))

    self.poshimodata.update(temp_base_poshimo_data) # merge with db info (so its not a base poshimo)
    self._move_list = self.load_move_list(results.get("move_list")) # unpack json moves
    self._mission_id:int = (self.poshimodata.get("mission_id", None))
    self._status = PoshimoStatus(int(self.poshimodata.get("status", 0))) 
    self._in_combat = bool(int(self.poshimodata.get("in_combat")))
    self.is_wild = bool(int(self.poshimodata.get("is_wild")))
    self._xp = int(self.poshimodata.get("xp", 0))

    # load the actual stats 
    self._attack:PoshimoStat = PoshimoStat(self.poshimodata["attack"][0], stage=self.poshimodata["attack"][1], xp=self.poshimodata["attack"][2])
    self._defense:PoshimoStat = PoshimoStat(self.poshimodata["defense"][0], stage=self.poshimodata["defense"][1], xp=self.poshimodata["defense"][2])
    self._special_attack:PoshimoStat = PoshimoStat(self.poshimodata["special_attack"][0], stage=self.poshimodata["special_attack"][1], xp=self.poshimodata["special_attack"][2])
    self._special_defense:PoshimoStat = PoshimoStat(self.poshimodata["special_defense"][0], stage=self.poshimodata["special_defense"][1], xp=self.poshimodata["special_defense"][2])
    self._speed:PoshimoStat = PoshimoStat(self.poshimodata["speed"][0], stage=int(self.poshimodata["speed"][1]), xp=int(self.poshimodata["speed"][2]))    
    #logger.info(f"Loaded poshimo: {Fore.GREEN}{self.poshimodata}{Fore.RESET}")


  def save(self) -> int:
    """ 
    save this poshimo to the db (when giving a trainer a Poshimo) 
    returns the ID of this poshimo in the db
    """
    self.poshimodata = base_poshimo_data[self.name.lower()] # base data
    self._level:int = self._level #TODO: leveling
    self._display_name:str = self.name
    self._personality:PoshimoPersonality = PoshimoPersonality()
    self._hp:int = self.poshimodata.get("hp", 1)
    self._max_hp:int = self._hp
    #logger.info(f"Preparing this poshimo for creation: DISPLAY NAME: {self._display_name} OWNER: {self.owner} PERSONALITY: {self._personality}")

    with AgimusDB() as query:
      
      sql = """
      INSERT INTO poshimodae 
        (id, owner, name, display_name, level, xp, hp, max_hp, attack, defense, special_attack, special_defense, speed, personality, move_list, status, in_combat)
        VALUES 
          (%(id)s, %(owner)s, %(name)s, %(display_name)s, %(level)s, %(xp)s, %(hp)s, %(max_hp)s, %(attack)s, %(defense)s, %(special_attack)s, %(special_defense)s, %(speed)s, %(personality)s, %(move_list)s, %(status)s, %(in_combat)s)
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
        "move_list":self.dump_move_list(),
        "status":self._status.value,
        "in_combat":self._in_combat,
        "is_wild":self.is_wild
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
    logger.info(f"{Style.BRIGHT}Attempting to update Poshimo {self.id}'s {Fore.CYAN}{col_name}{Fore.RESET}{Style.RESET_ALL} with new value: {Fore.LIGHTGREEN_EX}{value}{Fore.RESET}")
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
  def mission_id(self) -> int:
    return self._mission_id
  @mission_id.setter
  def mission_id(self, val:int):
    self._mission_id = val
    self.update("mission_id", self._mission_id)

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
  def attack(self, val, stage=None, xp=None):
    if not stage:
      stage = self._attack.stage
    if not xp:
      xp = self._attack.xp
    self._attack = PoshimoStat(max(0, val), stage, xp)
    self.update("attack", self._attack.to_json())

  @property
  def defense(self) -> PoshimoStat:
    return self._defense
  @defense.setter
  def defense(self, val, stage=None, xp=None):
    if not stage:
      stage = self._defense.stage
    if not xp:
      xp = self._defense.xp
    self._defense = PoshimoStat(max(0, val), stage, xp)
    self.update("defense", self._defense.to_json())

  @property
  def special_attack(self) -> PoshimoStat:
    logger.info(self._special_attack)
    return self._special_attack
  @special_attack.setter
  def special_attack(self, val, stage=None, xp=None):
    if not stage:
      stage = self._special_attack.stage
    if not xp:
      xp = self._special_attack.xp
    self._special_attack = PoshimoStat(max(0, val), stage, xp)
    self.update("special_attack", self._special_attack.to_json())

  @property
  def special_defense(self) -> PoshimoStat:
    return self._special_defense
  @special_defense.setter
  def special_defense(self, val, stage=None, xp=None):
    if not stage:
      stage = self._special_defense.stage
    if not xp:
      xp = self._special_defense.xp
    self._special_defense = PoshimoStat(max(0, val), stage, xp)
    self.update("special_defense", self._special_defense.to_json())    

  @property
  def speed(self) -> PoshimoStat:
    return self._speed
  @speed.setter
  def speed(self, val, stage=None, xp=None):
    if not stage:
      stage = self._speed.stage
    if not xp:
      xp = self._speed.xp
    self._speed = PoshimoStat(max(0, val), stage, xp)
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
    self._level = min(MAX_POSHIMO_LEVEL, max(0, val))
    self.update("level", self._level)

  @property
  def xp(self) -> int:
    return self._xp
  @xp.setter
  def xp(self, val:int):
    self._xp = max(0, int(val))
    self.update("xp", self._xp)
    while self._xp >= self.next_level:
      self.level_up()

  @property
  def status(self):
    return self._status
  
  @status.setter
  def status(self, status:PoshimoStatus):
    self._status = status
    self.update("status", self._status.value)

  @property
  def in_combat(self) -> bool:
    return self._in_combat

  @in_combat.setter
  def in_combat(self, val:bool):
    self._in_combat = val
    self.update("in_combat", self._in_combat)

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

  def reset_stat_stages(self) -> None:
    ''' reset stat stages to 0 '''
    for s in STAT_NAMES:
      stat:PoshimoStat = getattr(self, s)
      stat.stage = 0

  def show_types(self) -> str:
    """ a nicely formatted str of this poshimo's types """
    return "/".join([str(type) for type in self.types])

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
    temp_move_list:List[PoshimoMove] = []
    for move in self.poshimodata["move_list"]:
      logger.info(f"MOVE: {move}")
      if move is not None:
        temp_move_list.append(PoshimoMove(name=move))
    return temp_move_list

  def dump_move_list(self) -> str:
    """ 
    dump move list to json for DB insertion 
    returns a json string
    """
    db_move_list:list = []
    for move in self._move_list:
      if move:
        db_move_list.append(move.to_json())
    #logger.info(f"Dumping json: {db_move_list}")
    return json.dumps(db_move_list)
  
  def load_move_list(self, movelist) -> List[PoshimoMove]:
    """ 
    load move list from json 
    returns a list of PoshimoMoves
    """
    temp_move_list = []
    loaded_move_list = json.loads(movelist)
    for move in loaded_move_list:
      if move and move != "":
        dbmove = PoshimoMove(name=move["name"], stamina=move["stamina"], max_stamina=move["max_stamina"])
        temp_move_list.append(dbmove)
    return temp_move_list

  def get_all_stamina(self) -> tuple:
    ''' gets the stam/max stam from all this poshimo's moves '''
    moves = self._move_list
    stam = max_stam = 0
    for m in moves:
      max_stam += m.max_stamina
      stam += m.stamina
    return (stam, max_stam)

  def revive(self) -> None:
    ''' bring a poshimo back to life '''
    self.status = PoshimoStatus.IDLE
    self.hp += 1

  def restore_all_hp(self) -> None:
    ''' fully restores this poshimo's hp '''
    self.hp = self.max_hp
    
  def restore_all_stamina(self) -> None:
    ''' fully restore this poshimo's stamina '''
    moves = self._move_list
    for m in moves:
      m.stamina = m.max_stamina
    self.move_list = moves

  def full_restore(self) -> None:
    ''' full restore of hp and stamina '''
    self.restore_all_hp()
    self.restore_all_stamina()

  def base_xp(self) -> int:
    ''' 
    this poshimo's "BASE XP" used for determining levels and how much xp it gives out 
    combines their base stats and base max_xp and then averages them
    actually seems pretty close to original pokemon!
    '''
    pdata = base_poshimo_data[self.name.lower()]
    value = 0
    for stat in STAT_NAMES:
      value += int(pdata[stat][0])
    value += int(pdata["max_hp"])
    total_stats = len(STAT_NAMES) + 1
    return round(value/total_stats)

  def hp_gain_amount(self):
    ''' how much xp this poshimo gains when leveling up '''
    return round((((self.base_xp() + 50) * self.level) / 50) + 10) + random.randint(0,round(self.base_xp()/10))

  def xp_given(self) -> int:
    ''' the base amount of xp this poshimo will give out when defeated in combat '''
    wild_bonus = 1
    if self.is_wild:
      wild_bonus = 1.5
    return round(((self.base_xp() * self.level) * wild_bonus) / 7)

  def stat_xp_given(self) -> List[int]:
    ''' the amount of stat XP this poshimo gives when defeated '''
    stats = []
    for s in STAT_NAMES:
      stats.append( round((int(getattr(self, s)) / 10) + (self.level / 4)) )
    return stats

  def level_up(self):
    ''' level up this poshimo '''
    self.level += 1
    self.levels_gained.append(self._level)
    self.stat_increases = self.apply_stats_for_level_up()
    self.next_level = get_experience(self.leveling_type, self._level+1)

  def reset_level_up_notifications(self):
    self.levels_gained = []
    self.stat_increases = {}

  def apply_stats_for_level_up(self) -> dict:
    ''' gain stat points when you level (not xp) '''
    stat_increases = []
    for s in STAT_NAMES:
      gain = random.randint(1,4)
      if self.personality.bonus == s:
        gain *= 1.5
      if self.personality.penalty == s:
        gain *= 0.5
      gain = round(gain)
      stat:PoshimoStat = getattr(self, s)
      stat_increases.append(gain)
      stat.stat_value += gain
      setattr(self, s, stat) # actually update the stat
    stat_increases = dict(zip(STAT_NAMES, stat_increases))
    hp_gain = self.hp_gain_amount()
    stat_increases["max_hp"] = hp_gain
    self.max_hp += hp_gain
    logger.info(f"LEVEL UP STAT INCREASES: {stat_increases}")
    return stat_increases

  def apply_stat_xp(self, stat_xp:List[int]) -> list:
    ''' apply stat xp after combat '''
    logger.info(f"STAT XP REWARD: {stat_xp}")
    stat_increases = []
    for i,stat_name in enumerate(STAT_NAMES):
      logger.info(stat_xp[i])
      xp_value = stat_xp[i]
      if self.personality.bonus == stat_name:
        xp_value *= 1.5
      if self.personality.penalty == stat_name:
        xp_value *= 0.5
      updated_stat:PoshimoStat = getattr(self, stat_name)
      stat_increase = updated_stat.add_xp(xp_value)
      stat_increases.append(stat_increase)
      setattr(self, stat_name, updated_stat)
    return stat_increases