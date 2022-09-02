from common import *
from .poshimo import Poshimo
from .move import PoshimoMove
from .trainer import PoshimoTrainer

# main poShimo game functionality
# probably some utility stuff too
class PoshimoGame:
  """
  The base poShimo game object
  
  Methods
  ----

  `register_trainer(trainer_info)`
    Register a new trainer to the database
  
  `get_all_trainers()`
    Returns a list of all trainers in the database

  `get_trainer(discord_id)`
    Get trainer details by Discord ID

  """
  def __init__(self):
    self.active_battles = [] # need to load any battles that were in progress
    self.starter_poshimo = [Poshimo("Worf"), Poshimo("Jim Shimoda"), Poshimo("Captain Picard")]

  def register_battle(self, contender_1, contender_2) -> int:
    # add contenders to the db
    # return ID (?)
    pass

  def get_all_trainers(self):
    db = getDB()
    sql = "SELECT users.discord_id FROM users LEFT JOIN poshimo_trainers ON poshimo_trainers.userid = users.id"
    query = db.cursor()
    query.execute(sql)
    all_trainers = [int(i[0]) for i in query.fetchall()]
    query.close()
    db.close()
    return all_trainers

  def get_trainer(self, discord_id):
    """Get trainer data from the database based on discord ID"""
    db = getDB()
    sql = "SELECT * FROM poshimo_trainers \
          LEFT JOIN users ON poshimo_trainers.userid = users.id \
          LEFT JOIN poshimodae ON owner_id = poshimo_trainers.id \
          WHERE users.discord_id = %s"
    vals = (discord_id,)
    query = db.cursor(dictionary=True)
    query.execute(sql, vals)
    trainer_data = query.fetchall()
    query.close()
    db.close()   
    return trainer_data

  def register_trainer(self, trainer_info:dict) -> int:
    """
    Register a new trainer to the database

    Parameters
    ----
    `trainer_info`:`dict`
      A dictionary of the user's info

    Returns
    ----
    - `int` The ID of user in the DB
    - `0` If the user is already registered or an error occurred
    """
    db = getDB()
    sql = "INSERT INTO poshimo_trainers (userid) VALUES (%s)"
    vals = (trainer_info.get("userid"),)
    query = db.cursor()
    query.execute(sql, vals)
    db.commit()
    insert_id = query.lastrowid
    query.close()
    db.close()
    logger.info(f"REGISTERING POSHIMO TRAINER: {trainer_info}")
    return insert_id

  # player wants to explore
  def start_exploration(self, player) -> None:
    pass

  # resolve and show results of player exploration
  def resolve_exploration(self, player) -> None:
    pass

  def test_moves(self) -> tuple:
    move1 = PoshimoMove("test")
    move2 = PoshimoMove("test2")
    return (move1, move2)