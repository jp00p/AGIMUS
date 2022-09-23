from common import *
from .objects import *
import pocket_shimodae.utils as utils

class PoshimoGame:
  """
  The base Poshimo game object
  This handles initialization of the game along with
  almost all of the functionality exposed to the cog
  
  Methods
  ----

  `register_trainer(user_id)`
    Register a new trainer to the database
  
  `get_all_trainers()`
    Returns a list of all trainers in the database

  `get_trainer(discord_id=None|int, trainer_id=None|int)`
    Get trainer details by Discord ID

  """
  def __init__(self, cog):
    self.cog = cog
    self.world = PoshimoWorld() 
    self.active_battles = [] 
    self.starter_poshimo = [
      "Bulbasaur", 
      "Charmander", 
      "Squirtle"
    ]
    logger.info(f"{Back.LIGHTMAGENTA_EX}{Fore.LIGHTYELLOW_EX}Poshimo game loaded and ready to play!{Fore.RESET}{Back.RESET}")
    
  def find_in_world(self, location_name) -> PoshimoLocation:
    """ find a location in the world based on the location name """
    return self.world.locations[location_name]

  # def get_all_trainers(self) -> list:
  #   """ get a list of discord ids from all the registered trainers """
  #   with AgimusDB() as query:
  #     sql = "SELECT users.discord_id, poshimo_trainers.id FROM poshimo_trainers LEFT JOIN users ON poshimo_trainers.user_id = users.id"
  #     query.execute(sql)
  #     all_trainers = [int(i[0]) for i in query.fetchall()]
  #   return all_trainers

  # def get_trainer(self, discord_id=None, trainer_id=None) -> PoshimoTrainer:
  #   """
  #   Get a PoshimoTrainer object from the database based on discord ID or Trainer ID
  #   """
  #   logger.info(f"Attempting lookup on poshimo trainer {discord_id}...")
  #   with AgimusDB(dictionary=True) as query:
  #     if discord_id:
  #       sql = '''SELECT *, poshimo_trainers.id as trainer_id FROM poshimo_trainers 
  #             LEFT JOIN users ON poshimo_trainers.user_id = users.id 
  #             WHERE users.discord_id = %s'''
  #       vals = (discord_id,)
  #     elif trainer_id:
  #       sql = '''SELECT *, poshimo_trainers.id as trainer_id FROM poshimo_trainers 
  #             LEFT JOIN users ON poshimo_trainers.user_id = users.id 
  #             WHERE poshimo_trainers.id = %s'''
  #       vals = (trainer_id,)
  #     query.execute(sql, vals)
  #     trainer_data = query.fetchone()
  #     logger.info(f"Trainer found!")
  #     logger.info(trainer_data)
  #   return PoshimoTrainer(trainer_data["trainer_id"])

  def start_hunt(self, discord_id):
    """ begins a hunt for this user! """
    hunter = utils.get_trainer(discord_id=discord_id)
    location = self.find_in_world(hunter.location)
    location_poshimo = location.wild_poshimo
    logger.info(f"{location.wild_poshimo}")
    weights, poshimo = [[i for i,j in location_poshimo],
                        [j for i,j in location_poshimo]]
    found_poshimo = random.choices(poshimo, weights, k=1)[0]
    logger.info(f"Found this poshimo: {found_poshimo}")
    #TODO: scale level
    hunt = PoshimoBattle(
      battle_type=BattleTypes.HUNT,
      trainer_1=hunter, 
      wild_poshimo=Poshimo(name=found_poshimo, is_wild=True)
    )
    return hunt

  # def register_trainer(self, user_id) -> PoshimoTrainer:
  #   """
  #   Register a new trainer to the database

  #   Parameters
  #   ----
  #   `user_id`:`int`
  #     the users ID from the `users` table

  #   Returns
  #   ----
  #   PoshimoTrainer
  #   """
  #   logger.info(f"Attempting to register new trainer {user_id}")
  #   with AgimusDB() as query:
  #     sql = "INSERT INTO poshimo_trainers (user_id) VALUES (%s)"
  #     vals = (user_id,)    
  #     query.execute(sql, vals)
  #     trainer_id = query.lastrowid
  #     if trainer_id:
  #       logger.info(f"Success! new trainer ID: {trainer_id}")
  #   return PoshimoTrainer(trainer_id)

  def _old_test(self, discord_id):
    trainer = utils.get_trainer(discord_id=discord_id)
    trainer.add_poshimo(random.choice(self.starter_poshimo))
    trainer.wins += 5
    trainer.scarves += 69

  def test_unlock_loc(self, discord_id, location_name):
    trainer = utils.get_trainer(discord_id=discord_id)
    trainer_locs = trainer.locations_unlocked
    trainer_locs.add(location_name)
    trainer.locations_unlocked = trainer_locs

  def test_give_poshimo(self, discord_id):
    trainer = utils.get_trainer(discord_id=discord_id)
    sample_poshimo = random.choice([
      Poshimo(name="Worf"), 
      Poshimo(name="Captain Picard"), 
      Poshimo(name="Jim Shimoda")]
    )
    new_poshimo = trainer.add_poshimo(sample_poshimo)
    return new_poshimo

  def test_clear_db(self):
    with AgimusDB() as query:
      sql = "DELETE FROM poshimo_trainers WHERE id > 0;"
      query.execute(sql)
    self.cog.all_trainers = []