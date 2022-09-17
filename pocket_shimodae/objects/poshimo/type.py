from common import *
import csv

with open("pocket_shimodae/data/poshimo_types.csv") as file:
  csvdata = csv.DictReader(file)
  typedata = {}
  for row in csvdata:
    typedata[row["name"]] = {
      "name" : row["name"],
      "weakness" : row["weakness"] if row["weakness"] else None,
      "strength" : row["strength"] if row["strength"] else None
    }

class PoshimoType:
  def __init__(self, name):
    if not name:
      self.name = ""
    else:
      self.name = name
    self.weakness = None
    self.strength = None
    if self.name:
      self.typedata = typedata[self.name]
      self.weakness = self.typedata["weakness"]
      self.strength = self.typedata["strength"]
    else:
      self.weakness = None
      self.strength = None

  def __repr__(self):
    return f"{self.name.title()}"