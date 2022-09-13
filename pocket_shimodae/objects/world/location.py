class PoshimoLocation:
  """ A location in our game world """
  def __init__(self, name):
    self.location_data = {} # pull from file based on name
    self.wild_poshimo = {}
    self.discoverable_items = {}
    self.description = None
    self.quests = None
    self.shop = None
    self.paths = {}