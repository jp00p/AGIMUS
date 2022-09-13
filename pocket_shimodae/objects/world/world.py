from .location import PoshimoLocation

class PoshimoWorld(object):
  """ The world of Poshimo! """
  def __init__(self):
    self.all_biomes = {}
    
    self.all_locations = {
      "starting_zone" : PoshimoLocation("Starting Location")
    }