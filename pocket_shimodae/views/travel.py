import pocket_shimodae.utils as utils
from common import *
from ..ui import *
from . import main_menu as mm

direction_arrows = {
  "n": "⬆",
  "e": "➡",
  "s": "⬇",
  "w": "⬅"
}

direction_names = {
  "n": "north",
  "e": "east",
  "s": "south",
  "w": "west"
}

class LocationButton(discord.ui.Button):
  def __init__(self, cog, trainer, dir, location, location_key, row):
    self.cog = cog
    self.location = location
    self.location_key = location_key
    self.dir = dir
    self.row = row
    self.trainer = trainer
    super().__init__(
      label=direction_arrows[dir],
      row=self.row,
      style=discord.ButtonStyle.green
    )
  async def callback(self, interaction:discord.Interaction):
    self.trainer.location = self.location_key
    await interaction.response.edit_message(
      content=f"",
      view=None,
      embed=discord.Embed(
        title=f"You have moved to __{self.location.name}__",
        description=f"{self.location.description}",
        fields=[
          discord.EmbedField(
            name="Current weather",
            value=f"{self.location.weather.full_name()}"
          ),
          discord.EmbedField(
            name="Biome",
            value=f"{self.location.biome.name} {self.location.biome.emoji}"
          )
        ]
      )
    )

class TravelMenu(PoshimoView):
  """ when a trainer wants to travel, they'll see this first """
  def __init__(self, cog, trainer):
    super().__init__(cog, trainer)

    self.trainer_location = self.game.find_in_world(self.trainer.location)
    self.exits = {
    }

    self.exit_description = ""
    self.rows = [
      # build a grid of buttons
      ["nw", "n", "ne"],
      ["w", "x", "e"],
      ["sw", "s", "se"]
    ]
    logger.info(f"Unlocked locations: {self.trainer.locations_unlocked}")
    logger.info(f"Trainer's current location: {self.trainer.location}")
    # loop over all the paths at this location
    for dir,loc in self.trainer_location.paths.items():
      logger.info(f"{dir},{loc}")
      if loc in self.trainer.locations_unlocked and loc != self.trainer_location:
        # if the location is unlocked by the player, add it to the list of exits
        self.exits[dir] = loc  

    if len(self.exits) < 1:
      self.embeds = [
        discord.Embed(
          title="You haven't unlocked any locations connected to this one!", 
          description="You may need to do some questing, exploring, or other activities to find a new location to travel to.")
      ]
    else:
      # build the lil map
      exit_names = {
        'n': '',
        'e': '',
        's': '',
        'w': ''
      }
      wrapper = textwrap.TextWrapper(width=24)
      for dir, loc_key in self.exits.items():
        location = self.game.find_in_world(loc_key)
        locname = textwrap.dedent(location.name)
        exit_names[dir] = wrapper.fill(locname)

# LIL MAP ACTION ===============================================
#       exit_description = f"""```ansi
# {Fore.YELLOW}{'N'.center(48)}{Fore.RESET}
# {exit_names['n'].center(48)}
# {exit_names['w'].ljust(48)} 🧭 {exit_names['e'].rjust(48)}
# {exit_names['s']:^48}```"""
      map_top = PrettyTable()
      map_top.set_style(MARKDOWN)
      map_top.field_names = ["locname"]
      map_top.align["locname"] = "c"
      map_top.add_row([f"{exit_names['n']:^48}"])
      map_top.header = False
      map_top.border = False
      

      map_center = PrettyTable()
      map_center.set_style(MARKDOWN)
      map_center.field_names = ["locname_w", "x", "locname_e"]
      map_center.align["locname_w"] = "l"
      map_center.align["locname_e"] = "r"
      map_center.align["x"] = "c"
      map_center.add_row([
        f"{exit_names['w']:<20}", 
        f"{'^':^10}\n{'<':<4} {'>':>4}\n{'v':^10}", 
        f"{exit_names['e']:>20}"
        ])
      map_center.header = False
      map_center.border = False
      

      map_bottom = PrettyTable()
      map_bottom.set_style(MARKDOWN)
      map_bottom.field_names = ["locname"]
      map_bottom.align["locname"] = "c"
      map_bottom.add_row([f"{exit_names['s']:^50}"])
      map_bottom.header = False
      map_bottom.border = False
      exit_description = f"""```ansi
{map_top.get_string()}
{map_center.get_string()}
{map_bottom.get_string()}
```"""

# ==============================================================

      self.embeds = [
        discord.Embed(
          title="Where do you want to go today™?", 
          description=f"""Choose a location to move to:
          {exit_description}
          """
        )
      ]
    
    logger.info(f"Exits: {self.exits} || {self.exits.keys()}")    
    
    cur_row = 1
    for row in self.rows:
      for cell in row:
        if cell in self.exits.keys():
          location = self.game.find_in_world(self.exits[cell])
          self.add_item(LocationButton(
            cog=self.cog, trainer=self.trainer, dir=cell, 
            location=location, location_key=self.exits[cell], row=cur_row
          ))
        else:
          label = " "
          self.add_item(discord.ui.Button(label=label, row=cur_row, disabled=True))
      cur_row += 1
      
    self.add_item(mm.BackToMainMenu(self.cog, self.trainer))
