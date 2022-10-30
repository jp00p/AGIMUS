from common import *
from ..objects import (FishingShapeDict, PoshimoFish, PoshimoLocation,
                       PoshimoTrainer)
from ..ui import *
from . import main_menu as mm

#trash_items = ["🦴", "🥾"]
trash_items = ["🟦"]*12

class FishingButton(discord.ui.Button):
  def __init__(self, cog, row, choice, water_contents, available_fish, fishing_shape, trainer):
    label = "⠀" #TODO: find a better label, maybe use water ripple emoji???
    self.choice = choice
    self.water_contents = water_contents
    self.cog = cog
    self.win = bool(self.water_contents[self.choice] and self.water_contents[self.choice] == "fish")
    self.available_fish = available_fish
    self.fishing_shape = fishing_shape
    self.trainer = trainer
    super().__init__(
      label=label,
      row=row,
      style=discord.ButtonStyle.primary
    )
  async def callback(self, interaction):
    view = FishingResults(self.cog, self.trainer, self.win, self.choice, self.water_contents, self.available_fish, self.fishing_shape)
    await interaction.response.edit_message(view=view, embed=view.get_embed())

class FishingResults(PoshimoView): 
  def __init__(self, cog, trainer, win:bool, choice:int, water_contents:list, fish:str, fishing_shape:FishingShapeDict):
    super().__init__(cog, trainer)
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
      self.trainer.catch_fish(self.caught_fish)
      self.description = "\n```ansi\n" + f"FISH: {Fore.CYAN}{self.caught_fish}{Fore.RESET}"
      self.description += "\n" + f"LENGTH: {Fore.YELLOW}{self.caught_fish.length}{Fore.RESET}cm" + "\n```\n"
      
    else:
      self.title = "You failed to catch a fish 😢"
      self.description = fill_embed_text("Try the wide beam next time!")

    # scanner results if they win or lose    
    self.description += "```ansi\n"+f"{Fore.MAGENTA}FISHING HOERL SCANNER{Fore.RESET} {Fore.YELLOW}Mk IV{Fore.RESET} [{Fore.GREEN}ONLINE{Fore.RESET}]"+"\n"
    self.description += "      SONAR SCAN RESULTS\n\n"
    cell_counter = 0
    
    for row in self.fishing_shape["shape"]:
      self.description += "         "
      for cell in row:
        if cell_counter == self.choice and win:
          self.description += "✅"
        elif cell_counter == self.choice:
          self.description += "❌"
        elif water_contents[cell_counter] == "fish":
          self.description += "🐟"
        elif water_contents[cell_counter] == "trash":
          self.description += f"{random.choice(trash_items)}"
        else:
          self.description += "⬛"
        cell_counter += 1
      self.description += "\n"
    self.description += "```"
    footer_text = "❌ = your cast\t 🐟 = fish\t 🟦 = water"
    if win:
      footer_text = "✅ = your cast\t 🐟 = fish\t 🟦 = water"
    self.embeds = [
      discord.Embed(
        title=self.title,
        description=self.description
      ).set_footer(text=footer_text)
    ]
    self.add_item(BackButton(FishingLog(self.cog, self.trainer), label="Fishing log"))
    self.add_item(mm.BackToMainMenu(self.cog, self.trainer))

class FishingGame(PoshimoView):
  def __init__(self, cog, trainer:PoshimoTrainer):
    super().__init__(cog, trainer)
    fishing_spot = self.game.find_in_world(trainer.location)
    fishing_shape = fishing_spot.fishing_shape
    available_fish = fishing_spot.find_fish()
    if fishing_shape and len(available_fish) > 0:
      self.embeds = [
        discord.Embed(
          title=f"You begin holo-fishing at the {fishing_shape['shape_name']} near {fishing_spot}",
          description="```ansi\n"+f"{Fore.MAGENTA}FISHING HOERL SCANNER{Fore.RESET} {Fore.YELLOW}Mk IV{Fore.RESET} [{Fore.BLACK}OFFLINE{Fore.RESET}]```"+"\n\n"
        ).set_footer(text="Choose where to cast your line:")
      ]

      water_objects = ["fish"] * fishing_shape["num_fish"] # build array of ['fish','fish'...]
      flat_shape = [item for items in fishing_shape["shape"] for item in items] # flatten shape into 2d list      
      num_trash = flat_shape.count(1) - fishing_shape["num_fish"]
      water_objects += ["trash"] * num_trash # build array of ['trash',...]]
      random.shuffle(water_objects) # the final, flat list of all the fish/trash
      
      water_contents = []
      for cell in flat_shape:
        if cell != 0:
          water_contents.append(water_objects.pop())
        else:
          water_contents.append(0)
      
      button_row = 0
      cell_number = 0

      for row in fishing_shape["shape"]:
        cell_count = 0
        for cell in row:
          if cell != 0:
            self.add_item(FishingButton(self.cog, button_row, cell_number, water_contents, available_fish, fishing_shape, trainer))
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
    
    # not enough room for this, too bad!
    #self.add_item(BackButton(FishingLog(self.cog, self.trainer), label="Fishing log"))

class FishingLog(PoshimoView):
  ''' the view for your fishinglog '''
  def __init__(self, cog, trainer):
    super().__init__(cog, trainer)
    trainer_fishing_log = self.trainer.get_fishing_log()
    fields = None
    description = f"Your lengthiest fish:"
    
    if len(trainer_fishing_log) > 0:
      fields = [discord.EmbedField(name=f"{f.name}", value=f"{f.length}cm") for f in trainer_fishing_log[:10]]
    else:
      description = f"You have no fish! 🤯"

    self.embeds = [
      discord.Embed(
        title=f"{self.trainer}'s fishing log",
        description=fill_embed_text(description),
        fields=fields
      )
    ]
    self.add_item(StartFishingButton(self.cog, self.trainer))
    self.add_item(mm.BackToMainMenu(self.cog, self.trainer))

class StartFishingButton(discord.ui.Button):
  ''' lets go fishing pa '''
  def __init__(self, cog, trainer, **kwargs):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      label="Go fishing",
      emoji="🎣",
      **kwargs
    )
  async def callback(self, interaction:discord.Interaction):
    view = FishingGame(self.cog, self.trainer)
    #view.add_item(BackButton(FishingLog(self.cog, self.trainer), label="Back to fishing log"))
    await interaction.response.edit_message(view=view, embed=view.get_embed())
