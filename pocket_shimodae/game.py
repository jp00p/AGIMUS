from common import *
from .objects import *

class PoshimoGame:
  """
  The base poShimo game object
  
  Methods
  ----

  `register_trainer(user_id)`
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

  def get_all_trainers(self) -> list:
    with AgimusDB() as query:
      sql = "SELECT users.discord_id, poshimo_trainers.id FROM poshimo_trainers LEFT JOIN users ON poshimo_trainers.userid = users.id"
      query.execute(sql)
      all_trainers = [int(i[0]) for i in query.fetchall()]
    return all_trainers

  def get_trainer(self, discord_id) -> PoshimoTrainer:
    """
    Get trainer data from the database based on discord ID
    returns a PoshimoTrainer()
    """
    logger.info(f"Attempting lookup on poshimo trainer {discord_id}")
    with AgimusDB(dictionary=True) as query:
      sql = '''SELECT *, poshimo_trainers.id as trainer_id FROM poshimo_trainers 
            LEFT JOIN users ON poshimo_trainers.userid = users.id 
            WHERE users.discord_id = %s'''
      vals = (discord_id,)
      query.execute(sql, vals)
      trainer_data = query.fetchone()
      logger.info(f"Trainer found: {trainer_data}")
    return PoshimoTrainer(trainer_id=trainer_data["trainer_id"])

  def register_trainer(self, user_id) -> PoshimoTrainer:
    """
    Register a new trainer to the database

    Parameters
    ----
    `user_id`:`int`
      the users ID from the `users` table

    Returns
    ----
    PoshimoTrainer
    """
    logger.info(f"Attempting to register new trainer {user_id}")
    with AgimusDB() as query:
      sql = "INSERT INTO poshimo_trainers (userid) VALUES (%s)"
      vals = (user_id,)    
      query.execute(sql, vals)
      trainer_id = query.lastrowid
      if trainer_id:
        logger.info(f"Success! new trainer ID: {trainer_id}")
    return PoshimoTrainer(trainer_id)

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