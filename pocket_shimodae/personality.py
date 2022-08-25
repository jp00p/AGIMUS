import json

f = open("./data/poshimo_personalities.json")
personality_data = json.load(f) # load personality data
f.close()

# personality determines stat growth
class ShimodaPersonality:
  def __init__(self, name):
    self.pdata = personality_data.get(name)
    if self.pdata:
      self.name = name.title()
      self.bonus = self.pdata[0] # 10% increase to this stat
      self.penality = self.pdata[1] # 10% decreate to this stat

  def __str__(self):
    return self.name