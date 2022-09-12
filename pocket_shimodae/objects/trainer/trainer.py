from common import *
from ..poshimo import *

MAX_POSHIMO = 6 # the maximum poshimo a player can have
# this will represent either a discord user or an npc
class PoshimoTrainer(object):
  def __init__(self, trainer_id=None):
    self.id = trainer_id
    if self.id:
      self.load()
    else:
      self.discord_id = None
      self.user_id = None
      self._wins = 0
      self._losses = 0
      self._status = None # what are you doing
      self._active_poshimo = None # current poShimo
      self._poshimo_sac = [int] # all poShimo owned
      self._inventory = { "name": 99 } # all items
      self._location = None # where are you
      self._scarves = 0 # money
      self._buckles = [] # these are like pokemon badges
      self.shimodaepedia = [] # which poShimo has this player seen (list of ids)
      self.avatar = ""

  def __str__(self) -> str:
    return f"TRAINER ID: {self.id}"

  def update(self, col_name, value=None) -> None:
    """ 
    update a col in the db for this trainer 
    HUMANS ONLY ew
    """
    if not self.id: 
      return
    with AgimusDB() as query:
      sql = f"UPDATE poshimo_trainers SET {col_name} = %s WHERE id = %s" # col_name is a trusted input or so we hope
      vals = (value, self.id)
      query.execute(sql, vals)
      logger.info(f"Updated {self.id}'s {col_name} with new value {value}")

  def load(self):
    """ Load a human Trainer's data from DB """
    with AgimusDB(dictionary=True) as query:
      sql = '''
      SELECT * FROM poshimo_trainers 
        LEFT JOIN users ON poshimo_trainers.userid = users.id
        LEFT JOIN poshimodae ON owner_id = poshimo_trainers.id
      WHERE poshimo_trainers.id = %s
      '''
      vals = (self.id,)
      query.execute(sql, vals)
      trainer_data = query.fetchone()
    self._wins = trainer_data.get("wins")
    self._losses = trainer_data.get("losses")
    self._status = trainer_data.get("status")
    self._active_poshimo = self.get_active_poshimo()
    self._poshimo_sac = trainer_data.get("poshimo_sac")  
    self._inventory = trainer_data.get("inventory")
    self._location = trainer_data.get("location")
    self._scarves = trainer_data.get("scarves")
    self._buckles = trainer_data.get("buckles")
    self._shimodaepedia = trainer_data.get("discovered_poshimo")

  def get_active_poshimo(self):
    """ Get this trainer's active Poshimo """
    with AgimusDB(dictionary=True) as query:
      sql = "SELECT * FROM poshimodae LEFT JOIN poshimo_trainers ON poshimo_trainers.active_poshimo = poshimodae.id WHERE poshimo_trainers.id = %s"
      vals = (self.id,)
      query.execute(sql, vals)
      poshimo_data = query.fetchone() 
    if poshimo_data:
      return Poshimo(poshimo_data["name"]) # hmm
    else:
      return None

  @property
  def wins(self):
    return self._wins
  
  @wins.setter
  def wins(self, amt):
    self._wins = amt
    self.update("wins", self._wins)

  @property
  def losses(self):
    return self._losses
  
  @losses.setter
  def losses(self, amt):
    self._losses = max(0, amt)
    self.update("losses", self._losses)

  @property
  def active_poshimo(self):
    return self._active_poshimo
  
  @active_poshimo.setter
  def active_poshimo(self, poshimo:Poshimo):
    self._active_poshimo = poshimo
    self.update("active_poshimo", poshimo.id)
  
  @property
  def inventory(self):
    return self._inventory

  @inventory.setter
  def inventory(self, value):
    self._inventory = value
    self.update("inventory", self._inventory)
    
  @property
  def location(self):
    return self._location

  @location.setter
  def location(self, value):
    self._location = value
    self.update("location", self._location)

  @property
  def scarves(self):
    return self._scarves

  @scarves.setter
  def scarves(self, amt):
    self._scarves = amt
    self.update("scarves", self._scarves)

  @property
  def poshimo_sac(self):
    return self._poshimo_sac

  @poshimo_sac.setter
  def poshimo_sac(self, obj):
    self._poshimo_sac = obj
    sac_json = json.dumps([i.id for i in self._poshimo_sac])
    self.update("poshimo_sac", sac_json)

  @property
  def shimodaepedia(self):
    return self._shimodaepedia
  
  @shimodaepedia.setter
  def shimodaepedia(self, obj):
    self._shimodaepedia = obj

  def add_poshimo(self, poshimo:Poshimo):
    """ 
    add a new poshimo to the sac and save it to the db
    """
    poshimo.owner = self.id
    poshimo.save()
    self.poshimo_sac.append(poshimo)
    return poshimo

  def set_active_poshimo(self, poshimo):
    self.active_poshimo = poshimo

  def remove_poshimo(self, poshimo):
    # remove poshimo from sac
    pass

  def give_item(self, item):
    # give player an item
    pass

  def use_item(self, item):
    # use an item
    pass

  def remove_item(self, item):
    # remove item from inventory
    pass

  def update_db_column(self, column, value):
    # update player db info
    return