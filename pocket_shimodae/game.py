from dis import disco
from common import *
from .objects import *
import pocket_shimodae.utils as utils

class PoshimoGame(object):
  """
  The base Poshimo game object
  This handles initialization of the game along with
  almost all of the functionality exposed to the cog
  It is useful!
  
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
      "Worf", 
      "Riker", 
      "Q"
    ]
    ps_log("Game is ready to go! HIT IT")
    
  def find_in_world(self, location_name) -> PoshimoLocation:
    """ find a location in the world based on the location name """
    return self.world.locations[location_name.lower()]

  def resume_battle(self, trainer:PoshimoTrainer) -> PoshimoBattle:
    ''' resume a battle in progress '''
    #TODO: this will probably get ripped out for dueling
    with AgimusDB(dictionary=True) as query:
      sql = "SELECT id FROM poshimo_battles WHERE trainer_1 = %s or trainer_2 = %s ORDER BY id DESC LIMIT 1"
      vals = (trainer.id, trainer.id)
      query.execute(sql, vals)
      results = query.fetchone()
    if not results:
      return None
    old_battle = PoshimoBattle(id=results["id"])
    return old_battle

  def start_hunt(self, trainer:PoshimoTrainer) -> PoshimoBattle:
    """ begins a hunt for this user! """
    location = self.find_in_world(trainer.location)
    found_poshimo = location.find_poshimo()

    #TODO: scale level
    hunt = PoshimoBattle(
      battle_type=BattleTypes.HUNT,
      trainer_1=trainer, 
      wild_poshimo=Poshimo(name=found_poshimo, is_wild=True)
    )
    return hunt

  def admin_give_random_poshimo(self, trainer:PoshimoTrainer):
    sample_poshimo = random.choice([
        Poshimo(name="Picard"),
        Poshimo(name="Worf"),
        Poshimo(name="Obrien"),
        Poshimo(name="Wesley"),
        Poshimo(name="Pulaski"),
        Poshimo(name="Data"),
      ]
    )
    return trainer.add_poshimo(sample_poshimo)
    

  def admin_clear_db(self):
    with AgimusDB(multi=True) as query:
      sql = ["DELETE FROM poshimo_fishing_log WHERE id > 0;", "DELETE FROM poshimo_mission_logs WHERE id > 0;", "DELETE FROM poshimo_trainers WHERE id > 0;","DELETE FROM poshimo_battles WHERE id > 0;", "DELETE FROM poshimodae WHERE id > 0;"]
      for truncate in sql:
        query.execute(truncate)
    self.cog.all_trainers = []

  def test_fish_log(self, discord_id):
    trainer = utils.get_trainer(discord_id=discord_id)
    log = trainer.get_fishing_log()
    logger.info(f"FISHING LOG: {log}")

  def test_give_item(self, discord_id):
    trainer = utils.get_trainer(discord_id=discord_id)
    items = ["hypospray", "raw vertion", "Photonic Remodulator", "isolinear chip", "self sealing stem bolt", "power pill", "mug of root beer"]
    for i in items:
      item = PoshimoItem(i)
      trainer.add_item(item, random.randint(10,55))
    trainer.add_item(PoshimoItem("Hypospray Recipe"))
    trainer.add_item(PoshimoItem("Key to Forest of Forever"))
    return trainer.list_inventory()