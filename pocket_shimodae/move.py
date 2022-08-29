import json
import csv
from .type import PoshimoType

"""
glass table toss
barrel slam
lock door
frontier medicine
big dog
leg over chair
squint
axe handle
flail

"""


with open("pocket_shimodae/data/poshimo_moves.csv") as file:
  csvdata = csv.DictReader(file)
  movedata = {}
  for row in csvdata:
    movedata[row["name"]] = {
      "display_name" : row["display_name"],
      "type" : row["type"],
      "kind" : row["kind"],
      "power" : row["power"],
      "accuracy" : row["accuracy"],
      "max_stamina" : row["max_stamina"],
      "description" : row["description"]
    }

class PoshimoMove:
  """
  A poShimo move that can be used in attack
  """
  def __init__(self, name, stamina=None):
    self.movedata = movedata.get(name)
    self.display_name = self.movedata["display_name"]
    self.type = PoshimoType(self.movedata["type"])
    self.kind = self.movedata["kind"]
    self.power = self.movedata["power"]
    self.accuracy = self.movedata["accuracy"]
    self.max_stamina = self.movedata["max_stamina"]
    if stamina:
      self.stamina = stamina
    else:
      self.stamina = self.movedata["max_stamina"]
    self.description = self.movedata["description"]

  def __repr__(self):
    return f"""
    Name: {self.display_name}
    Type: {self.type}
    Kind: {self.kind}
    Power: {self.power}
    Accuracy: {self.accuracy}
    Stamina: {self.stamina}
    Description: {self.description}
    """

  def refill_stamina(self):
    self.stamina = self.max_stamina