from time import time_ns
from common import *
from enum import Enum, auto
import csv 
from datetime import timedelta, datetime as dt
from ..world import PoshimoItem
from ..poshimo import Poshimo, PoshimoStatus, PoshimoStat

with open("pocket_shimodae/data/awaymissions_gathering_rewards.csv") as file:
  csvdata = csv.DictReader(file)
  gathering_rewards_data = {}
  '''
  {
    "investigate woods" : [
      { item_name, rarity, amounts, },
      { item_name, rarity, amounts, },
    ]
  }
  '''
  for row in csvdata:
    key = row.get("name").lower()
    if not gathering_rewards_data.get(key):
      gathering_rewards_data[key] = []

    gathering_rewards_data[key].append(
      {
        "item_name" : row.get("item_name", ""),
        "rarity" : row.get("rarity", 0),
        "amounts" : row.get("amounts", "").split(",")
      }
    )
  ps_log(f"Gathering rewards: {len(gathering_rewards_data)}")
  logger.info(gathering_rewards_data)

with open("pocket_shimodae/data/awaymissions_gathering.csv") as file:
  csvdata = csv.DictReader(file)
  gathering_data = {}
  for row in csvdata:
    gathering_data[row.get("name").lower()] = {
      "name" : row.get("name", ""),
      "description" : row.get("description", ""),
      "min_level" : row.get("min_level", 1),
      "length" : row.get("length", 5)
    }
  ps_log(f"Gathering away missions: {len(gathering_data)}")

with open("pocket_shimodae/data/awaymissions_training.csv") as file:
  csvdata = csv.DictReader(file)
  training_data = {}
  for row in csvdata:
    training_data[row.get("name").lower()] = {
      "name" : row.get("name", ""),
      "description" : row.get("description", ""),
      "min_level" : row.get("min_level", 1),
      "length" : row.get("length", 5),
      "stat": row.get("stat", ""),
      "increase": row.get("increase", 0)
    }
  ps_log(f"Training away missions: {len(training_data)}")

class MissionTypes(Enum):
  TRAINING = auto()
  GATHERING = auto()
  EXPLORATION = auto()

  def __str__(self):
    return str(self.name.title())

class RewardTypes(Enum):
  STATS = auto()
  MATS = auto()
  LOCATIONS = auto()

def get_available_missions(mission_type:MissionTypes, poshimo_level:int) -> list:
  ''' get a list of possible missions for a given poshimo_level '''
  mission_data = gathering_data
  if mission_type is MissionTypes.TRAINING:
    mission_data = training_data
  if mission_type is MissionTypes.EXPLORATION:
    pass
  available_missions = []
  for mission in mission_data.values():
    if int(mission["min_level"]) <= poshimo_level:
      available_missions.append( AwayMission(name=mission["name"], mission_type=mission_type) )
  return available_missions

class AwayMission(object):
  ''' a mission that a poshimo can go on!  takes real time, poshimo is unavailable until it's complete '''
  def __init__(self, name:str=None, id:int=None, mission_type:MissionTypes=None):
    self.id = id
    self.mission_type = mission_type
    self.mission_data = None
    self.name = name
    self.start_time = None
    self.end_time = None
    self.time_left = None
    self.complete = False
    self.poshimo = None
    if self.id:
      mission_db_data = self.load()
      self.mission_type = MissionTypes(int(mission_db_data["mission_type"]))
      self.start_time = mission_db_data["time_started"]
      self.end_time = mission_db_data["time_ends"]
      self.time_left:timedelta = self.end_time - dt.now()
      self.complete = bool(self.time_left.total_seconds() <= 0.0)
      name = mission_db_data["mission_name"]
      self.poshimo = Poshimo(id=mission_db_data["poshimo_id"])

    if self.mission_type is MissionTypes.TRAINING:
      self.mission_data = training_data[name.lower()]
      self.reward_type = RewardTypes.STATS
    elif self.mission_type is MissionTypes.GATHERING:
      self.mission_data = gathering_data[name.lower()]
      self.reward_type = RewardTypes.MATS
    elif self.mission_type is MissionTypes.EXPLORATION:
      self.reward_type = RewardTypes.LOCATIONS
      pass

    self.name = self.mission_data["name"]
    self.mission_length = int(self.mission_data["length"])
    self.description = self.mission_data["description"]
    
  def __str__(self):
    return f"{self.name.title()}"

  def load(self):
    ''' load an active mission '''
    return self.get_mission_log(self.id)

  def get_mission_log(self, log_id:int) -> dict:
    ''' get the details for a single mission log from the db '''
    results = None
    with AgimusDB(dictionary=True) as query:
      sql = "SELECT * FROM poshimo_mission_logs WHERE id = %s"
      vals = (log_id,)
      query.execute(sql, vals)
      results = query.fetchone()
    return results

  def begin(self, poshimo:Poshimo) -> int:
    ''' 
    starts an away mission for a given poshimo
    returns mission log id
    '''
    current_time = dt.now()
    end_time = current_time + timedelta(minutes=self.mission_length)
    with AgimusDB() as query:
      sql = "INSERT INTO poshimo_mission_logs (poshimo_id, mission_name, mission_type, time_started, time_ends) VALUES (%s, %s, %s, %s, %s)"
      vals = (poshimo.id, self.name, self.mission_type.value, current_time, end_time)
      query.execute(sql, vals)
    return query.lastrowid

  def get_status(self) -> str:
    ''' retruns a nicely formatted string of this away mission's status '''
    time_left_str = "__Complete!__"
    if not self.complete:
      time_left_str = str(self.time_left).split(".")[0]
    return f"**Mission:** {self.name.title()}\n**Mission type:** {self.mission_type} ({self.mission_length} min)\n**Time left:** {time_left_str}"

  def get_emoji(self):
    ''' represents if the mission is complete or not '''
    if self.complete:
      return "✅"
    return "⏳"

  def resolve(self, trainer) -> str:
    from ..trainer import PoshimoTrainer
    trainer:PoshimoTrainer = trainer
    ''' 
    determine rewards
    set to resolved in the db
    hand out rewards 
    return poshimo to trainer
    return results str
    '''
    final_rewards = []
    
    if self.reward_type is RewardTypes.MATS:
      # mats/scarves
      rewards = gathering_rewards_data[self.name.lower()]
      final_rewards = self.roll_for_mats(rewards)

    if self.reward_type is RewardTypes.STATS:
      # stats and hp
      stat = self.mission_data["stat"]
      stat_bonuses = self.mission_data["increase"].split("-")
      stat_increase = random.randint(int(stat_bonuses[0]), int(stat_bonuses[1]))
      final_rewards = [(stat, stat_increase)]

    if len(final_rewards) < 1:
      final_rewards = [("Nothing", None, None)]
    else:
      final_rewards = self.hand_out_rewards(trainer, final_rewards)
    
    results = json.dumps(final_rewards)
    
    with AgimusDB() as query:
      sql = "UPDATE poshimo_mission_logs SET active = false, results = %s WHERE id = %s"
      vals = (results, self.id)
      query.execute(sql, vals)

    trainer.return_poshimo_from_mission(self.poshimo)
    return final_rewards


  def hand_out_rewards(self, trainer, rewards:list) -> list:
    ''' 
    this takes the rewards list from resolve() and actually gives out the rewards 
    returns a list of tuples that contains (name of stat, amount gained, new total/level up for stats)
    '''
    from ..trainer import PoshimoTrainer
    trainer:PoshimoTrainer = trainer
    final_rewards = [] # [(name of stat, amount gained, new total/level up increase)]
    
    if self.reward_type is RewardTypes.STATS:
      statname = rewards[0][0]
      statval = int(rewards[0][1])
      logger.info(statname)
      if statname == "max_hp":
        self.poshimo.max_hp = self.poshimo.max_hp + statval
        final_rewards.append(("max_hp", statval, self.poshimo.max_hp))
      else:
        updated_stat:PoshimoStat = getattr(self.poshimo, statname)
        stat_increase = updated_stat.add_xp(statval)
        setattr(self.poshimo, statname, updated_stat)
        final_rewards.append((statname, statval, stat_increase))
        logger.info(f"Added stat xp: {statname} +{statval} ({stat_increase} stat points gained)")

    if self.reward_type is RewardTypes.MATS:
      for mat,amt in rewards:
        if mat == "scarves":
          trainer.scarves += amt
          final_rewards.append(("scarves", amt, trainer.scarves))
        else:
          item = PoshimoItem(mat)
          trainer.add_item(item, amount=amt)
          item_total = int(trainer.inventory[item.name.lower()]["amount"])
          final_rewards.append((item.name, amt, item_total))
    return final_rewards


  def roll_for_mats(self, mat_rewards):
    ''' 
    roll for mat rewards, based on rarity
    100 is a guaranteed item
    50 has a 50/50 chance of appearing, etc
    '''
    roll_results = []
    for reward in mat_rewards:
      item = reward["item_name"]
      rarity = int(reward["rarity"]) # rarity=100 is a guaranteed item
      amounts = reward["amounts"]

      roll = random.randint(1,100) # roll the die
      if rarity >= roll:
        amount = random.randint(int(amounts[0]), int(amounts[1]))
        roll_results.append((item, int(amount)))
    return roll_results

  def recall(self, trainer):
    from ..trainer import PoshimoTrainer
    trainer:PoshimoTrainer = trainer
    ''' end a mission early, no rewards '''
    recall_results = "Recalled"
    with AgimusDB() as query:
      sql = "UPDATE poshimo_mission_logs (active, results) VALUES (%s, %s) WHERE id = %s"
      vals = (False, recall_results, self.poshimo.mission_id)
    trainer.return_poshimo_from_mission(self.poshimo)