# aka the player class
# this will represent either a discord user or an npc
class PoshimoTrainer():
  def __init__(self, is_human=False, discord_id=None, trainer_data={}):
    self.is_human = is_human
    self.discord_id = discord_id
    self.trainer_data = trainer_data
    self._wins = 0
    self._losses = 0
    self._active_poshimo = None # current poShimo
    self._shimoda_sac = [] # all poShimo owned
    self._inventory = []
    self._location = None

  @property
  def wins(self):
    return self._wins
  
  @wins.setter
  def wins(self, amt):
    self._wins = amt
    if self.is_human:
      pass
      #self.update_db_column(self)

  @property
  def losses(self):
    return self._losses
  
  @losses.setter
  def losses(self, amt):
    self._losses = max(0, amt)
    if self.is_human:
      pass
      #self.update_db_column(self)

  @property
  def active_poshimo(self):
    return self._active_poshimo
  
  @active_poshimo.setter
  def active_poshimo(self, poshimo):
    self._active_poshimo = poshimo
    if self.is_human:
      pass
      #self.update_db_column(self)
  
  @property
  def inventory(self):
    return self._inventory

  @inventory.setter
  def inventory(self, value):
    self._inventory = value
    if self.is_human:
      pass
      #self.update_db_column(self)
    
  @property
  def location(self):
    return self._location

  @location.setter
  def location(self, value):
    self._location = value
    if self.is_human:
      pass
      #self.update_db_column(self)

  def add_poshimo(self, poshimo):
    # add a poshimo to the sac
    pass

  def set_active_poshimo(self, poshimo):
    # set current active poshimo
    pass

  def give_item(self, item):
    # give player an item
    pass

  def update_db_column(self, column, value):
    # update player db info
    return
  