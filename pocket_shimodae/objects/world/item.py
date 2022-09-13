import json

# f = open("./data/poshimo_items.json")
# item_data = json.load(f) # load item data
# f.close()

# items can be used on pokemoda to do various things
# some items can also be held (maybe later release)
# some items are also just collectable/resources
class PoshimoItem:
  def __init__(self, name):
    #self.idata = item_data.get(name)
    if self.idata:
      pass
    self.type = None
    self.usable = None
    self.on_use = None