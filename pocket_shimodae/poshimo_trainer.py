import poshimo, item, location, quest

max_poshimo = 6 # the maximum poshimo a player can have

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
    self._inventory = [] # all items
    self._location = None
    self._scarves = 0
    self._poshimopedia = {} # which poShimo has this player seen

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

  @property
  def scarves(self):
    return self._scarves

  @scarves.setter
  def scarves(self, amt):
    self._scarves = amt
    if self.is_human:
      pass
      #self.update_db_column(self)

  def add_poshimo(self, poshimo):
    # add a poshimo to the sac
    pass

  def set_active_poshimo(self, poshimo):
    # set current active poshimo
    pass

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