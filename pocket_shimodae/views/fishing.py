from common import *
from typing import TypedDict
from ..ui import PoshimoView, Confirmation, PoshimoGame
from ..objects import PoshimoTrainer, PoshimoLocation, PoshimoFish, FishingShapeDict
import pocket_shimodae.utils as utils

trash_items = ["🦴", "🥾"]
trash_items += ["🟦"]*12

class FishingButton(discord.ui.Button):
  def __init__(self, cog, row, choice, water_contents, available_fish, fishing_shape):
    label = "⠀" #TODO: find a better label, maybe use water ripple emoji???
    self.choice = choice
    self.water_contents = water_contents
    self.cog = cog
    logger.info(self.water_contents)
    self.win = bool(self.water_contents[self.choice] and self.water_contents[self.choice] == "fish")
    self.available_fish = available_fish
    self.fishing_shape = fishing_shape
    super().__init__(
      label=label,
      row=row,
      style=discord.ButtonStyle.primary
    )
  async def callback(self, interaction):
    view = FishingResults(self.cog, self.win, self.choice, self.water_contents, self.available_fish, self.fishing_shape)
    await interaction.response.edit_message(view=view, embed=view.get_embed())

class FishingResults(PoshimoView):
  
  def __init__(self, cog, win:bool, choice:int, water_contents:list, fish:str, fishing_shape:FishingShapeDict):
    super().__init__(cog)
    self.title = ""
    self.description = ""
    self.fish = fish
    self.fishing_shape = fishing_shape
    fish_in_water = [PoshimoFish(name=f) for f in random.choices(self.fish, weights=None, k=self.fishing_shape["num_fish"])] # decide what the actual fish in the water are
    random.shuffle(fish_in_water)
    self.caught_fish = None 
    self.water_contents = water_contents # the flat list of what's in the water
    self.choice = choice

    if win:
      self.title = "You got a fish! 😊"
      self.caught_fish = fish_in_water.pop() # only if they won!
      self.description = "\n" + f"Fish caught: {self.caught_fish}"
      
    else:
      self.title = "You failed to catch a fish 😢"
      self.description = "Try the wide beam next time!"

    # scanner results if they win or lose    
    self.description += "\n__Fishing hole scanner results__\n\n"

    cell_counter = 0

    for row in self.fishing_shape["shape"]:
      for cell in row:
        if cell_counter == self.choice and win:
          self.description += "⠀✅⠀"
        elif cell_counter == self.choice:
          self.description += "⠀❌⠀"
        elif water_contents[cell_counter] == "fish":
          self.description += "⠀🐟⠀"
        elif water_contents[cell_counter] == "trash":
          self.description += f"⠀{random.choice(trash_items)}⠀"
        else:
          self.description += "⠀⬛⠀"
        cell_counter += 1
      self.description += "\n\n"

    logger.info(self.description)
    
    self.embeds = [
      discord.Embed(
        title=self.title,
        description=self.description
      )
    ]

class FishingGame(PoshimoView):
  def __init__(self, cog, trainer:PoshimoTrainer):
    super().__init__(cog)
    self.trainer = trainer
    fishing_spot = self.game.find_in_world(trainer.location)
    fishing_shape = fishing_spot.fishing_shape
    available_fish = fishing_spot.find_fish()
    if fishing_shape and len(available_fish) > 0:
      self.embeds = [
        discord.Embed(
          title=f"You begin fishing at the {fishing_shape['shape_name']} near {fishing_spot}",
          description="Choose where to cast your line:\n" + "⠀"*25
        )
      ]
      
      

      water_objects = ["fish"] * fishing_shape["num_fish"] # build array of ['fish','fish'...]
      flat_shape = [item for items in fishing_shape["shape"] for item in items]      
      logger.info(f"FLAT SHAPE: {flat_shape}")
      num_trash = flat_shape.count(1) - fishing_shape["num_fish"]
      logger.info(f"TRASH: {num_trash}")      
      water_objects += ["trash"] * num_trash # build array of ['trash',...]]
      random.shuffle(water_objects) # flat list of all the fish/trash
      
      water_contents = []
      for cell in flat_shape:
        if cell != 0:
          water_contents.append(water_objects.pop())
        else:
          water_contents.append(0)
      
      button_row = 0
      cell_number = 0

      for row in fishing_shape["shape"]:
        logger.info(f"{button_row}: {row}")
        cell_count = 0
        for cell in row:
          logger.info(f"CELL {cell_number}: {cell_count} {cell}")
          if cell != 0:
            self.add_item(FishingButton(self.cog, button_row, cell_number, water_contents, available_fish, fishing_shape))
          else:
            self.add_item(discord.ui.Button(label="⠀",style=discord.ButtonStyle.gray, disabled=True))
          cell_count += 1
          cell_number += 1
        button_row += 1

    else:
      # no fish available
      if not fishing_shape:
        description = "There's nowhere to fish in this location!"
      else:
        description = f"No fish are biting in this location right now. Maybe they don't like {random.choice(['the weather','this time of year'])}?"
      self.embeds = [
        discord.Embed(
          title="You couldn't find a good spot to fish.",
          description=description
        )
      ]