from common import *
import csv

with open("pocket_shimodae/data/poshimo_personalities.csv") as file:
  csvdata = csv.DictReader(file)
  idata = {}
  for id,row in enumerate(csvdata):
    pass
  
# personality determines stat growth
class PoshimoPersonality:
  def __init__(self, name):
    self.name = name
    # self.pdata = personality_data.get(name)
    # if self.pdata:
    #   self.name = name.title()
    #   self.bonus = self.pdata[0] # 10% increase to this stat
    #   self.penality = self.pdata[1] # 10% decreate to this stat

  def __str__(self):
    return self.name