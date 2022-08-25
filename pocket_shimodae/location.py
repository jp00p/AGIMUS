# places to find quests, items, new shimodae
class PoshimoLocation:
  def __init__(self, name):
    self.location_data = {} # pull from file based on name
    self.wild_poshimo = []
    self.description = ""
    self.quests = None
    self.shop = None