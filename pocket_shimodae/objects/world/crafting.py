from common import *
from enum import Enum, auto
from typing import TypedDict
from . import PoshimoItem
import csv

with open("pocket_shimodae/data/poshimo_crafting.csv") as file:
  csvdata = csv.DictReader(file)
  recipe_data = {}
  for row in csvdata:
    recipe_data[row.get("name").lower()] = {
      "name": row.get("name", ""),
      "level" : int(row.get("level", 0)),
      "difficulty" : int(row.get("difficulty", 1)),
      "materials" : row.get("materials", ""),
      "item" : row.get("item", "")
    }
  ps_log(f"Recipes: {len(recipe_data)}")

def get_all_crafting_levels():
  return sorted(list(set([int(r["level"]) for r in recipe_data.values()])))

class PoshimoRecipe(object):
  def __init__(self, name:str):  
    self.name:str = name.lower()
    self.recipe_data = recipe_data[self.name]
    self.level:int = self.recipe_data["level"]
    self.difficulty:int = self.recipe_data["difficulty"]
    self.materials = self.recipe_data["materials"].split("|")
    self.item = PoshimoItem(self.recipe_data["item"])
    if self.materials:
      mat_list = [m.split(":") for m in self.materials]
      self.materials = [{"item":PoshimoItem(mat[0]), "amount":int(mat[1])} for mat in mat_list]

  def crafted_xp(self, crafters_level:int=0) -> int:
    ''' how much xp this recipe gives when crafted '''
    return round(((self.level+1 * self.difficulty)) / (crafters_level+1))

  def craft(self) -> bool:
    ''' roll to craft this item '''
    return random.random() >= self.difficulty

  def list_mats(self) -> list:
    return [(r["item"].name.title(), r["amount"]) for r in self.materials]