from asyncio import gather
from common import *
from enum import Enum, auto
import csv 
import datetime
from ..poshimo import Poshimo, PoshimoStatus

with open("pocket_shimodae/data/awaymissions_gathering.csv") as file:
  csvdata = csv.DictReader(file)
  gathering_data = {}
  for row in csvdata:
    gathering_data[row.get("name").lower()] = {
      "name" : row.get("name", ""),
      "description" : row.get("description", ""),
      "min_level" : row.get("min_level", 1),
      "length" : row.get("length", 5),
      "rewards": row.get("possible_rewards", "")
    }
  ps_log(f"Gathering away missions: {len(gathering_data)} MISSIONS")

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
  ps_log(f"Training away missions: {len(training_data)} MISSIONS")

class MissionTypes(Enum):
  TRAINING = auto()
  GATHERING = auto()
  EXPLORATION = auto()

class RewardTypes(Enum):
  STATS = auto()
  MATS = auto()
  LOCATIONS = auto()

def get_available_missions(mission_type:MissionTypes, poshimo_level:int) -> list:
  ''' get a list of possible missions for a given poshimo_level '''
  mission_data = gathering_data
  logger.info(f"MISSION TYPE: {mission_type}")
  if mission_type is MissionTypes.TRAINING:
    mission_data = training_data
  if mission_type is MissionTypes.EXPLORATION:
    pass
  available_missions = []
  for mission in mission_data.values():
    if int(mission["min_level"]) <= poshimo_level:
      available_missions.append( AwayMission(mission["name"], mission_type) )
  return available_missions

class AwayMission(object):
  ''' a mission that a poshimo can go on!  takes real time, poshimo is unavailable until it's complete '''
  def __init__(self, name:str, mission_type:MissionTypes):
    self.mission_type = mission_type
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
    self.mission_length = self.mission_data["length"]
    self.description = self.mission_data["description"]

  def __str__(self):
    return f"{self.name.title()}"

  def get_mission_log(self, log_id:int) -> dict:
    ''' get the details for a single mission log from the db '''
    results = None
    with AgimusDB(dictionary=True) as query:
      sql = "SELECT * FROM poshimo_mission_logs WHERE id = %s"
      vals = (log_id,)
      query.execute(sql, vals)
      results = query.fetchone()
    return results

  def send(self, poshimo:Poshimo) -> int:
    ''' 
    send a poshimo on an away mission 
    returns mission log id
    '''
    poshimo.status = PoshimoStatus.AWAY
    current_time = datetime.datetime.now()
    end_time = current_time + datetime.timedelta(minutes=self.len)
    
    with AgimusDB() as query:
      sql = "INSERT INTO poshimo_mission_logs (poshimo_id, mission_name, mission_type, time_ends) VALUES (%s, %s, %s, %s)"
      vals = (poshimo.id, self.name, self.mission_type, end_time)
      query.execute(sql, vals)
    return query.lastrowid

  def get_status(self, poshimo:Poshimo) -> str:
    ''' retruns a nicely formatted string of this poshimo's away mission status '''
    status = self.get_mission_log(poshimo.mission_id)
    current_time = datetime.datetime.now()
    time_left = datetime.strftime(status["time_ends"]) - current_time
    return f"Mission: {status['mission_name'].title()}\nMission type:{status['mission_type']}\nTime left: {time_left.total_seconds()}"

  def resolve(self, poshimo:Poshimo):
    # resolve an away mission
    # only if they are ready
    pass

  def recall(self, poshimo:Poshimo):
    ''' end a mission early '''
    recall_results = "Recalled"
    with AgimusDB() as query:
      sql = "UPDATE poshimo_mission_logs (active, results) VALUES (%s, %s) WHERE id = %s"
      vals = (False, recall_results, poshimo.mission_id)
    poshimo.status = PoshimoStatus.IDLE
    poshimo.mission_id = None