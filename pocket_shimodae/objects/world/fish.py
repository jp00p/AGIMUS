from common import *
import csv 

with open("pocket_shimodae/data/Fish.csv") as file:
  csvdata = csv.DictReader(file)
  fdata = {}
  for row in csvdata:
    fdata[row.get("name").lower()] = {
      "name":row.get("name", ""),
      "min_length":row.get("min_length",0.0),
      "max_length":row.get("max_length",0.0),
      "difficulty":row.get("difficulty",1),
      "emoji":row.get("emoji", "🐟")
    }
  ps_log(f"Fish: {len(fdata)}")

class PoshimoFish(object):
  def __init__(self, name:str,length:float=None):
    self.name = name.lower()
    self.fish_data = fdata[self.name]
    self.display_name = self.fish_data.get("name")
    self.min_length = float(self.fish_data["min_length"])
    self.max_length = float(self.fish_data["max_length"])
    self.difficulty = int(self.fish_data["difficulty"])
    self.emoji = self.fish_data["emoji"]
    if not length:
      self.length = round(random.uniform(self.min_length, self.max_length) + random.uniform(0.0, 5.0), 2)
    else:
      self.length = length

  def __str__(self):
    return f"{self.display_name}"

  