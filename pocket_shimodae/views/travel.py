from common import *
from ..ui import PoshimoView, Confirmation

class LocationButton(discord.ui.Button):
  def __init__(self, cog, trainer, dir, location, location_key, row):
    self.cog = cog
    self.location = location
    self.location_key = location_key
    self.dir = dir
    self.row = row
    self.trainer = trainer
    super().__init__(
      label=self.location.name,
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
  def __init__(self, cog, discord_id):
    super().__init__(cog)
    self.discord_id = discord_id
    self.trainer = self.game.get_trainer(self.discord_id)
    self.trainer_location = self.game.find_in_world(self.trainer.location)
    self.exits = {}
    self.rows = [
      # build a grid of buttons
      # maybe expand to 8 dirs someday
      ["nw", "n", "ne"],
      ["e", "x", "w"],
      ["sw", "s", "se"]
    ]
    
    # loop over all the paths at this location
    for dir,loc in self.trainer_location.paths.items():
      if loc in self.trainer.locations_unlocked and loc != self.trainer_location:
        # if the location is unlocked by the player, add it to the list of exits
        self.exits[dir] = loc
    
    if len(self.exits) < 1:
      self.embeds = [
        discord.Embed(title="You haven't unlocked any locations connected to this one!", description="You may need to do some questing, exploring, or other activities to find a new location to travel to.")
      ]
    else:
      self.embeds = [
        discord.Embed(title="Where do you want to go?", description="Choose a location to move to")
      ]
    
    logger.info(f"Exits: {self.exits} || {self.exits.keys()}")    
    cur_row = 1
    max_str_len = 0
    for row,r in enumerate(self.rows):
      for col,cell in enumerate(r):
        if cell in self.exits.keys():
          location = self.game.find_in_world(self.exits[cell])
          str_len = len(location.name)
          if str_len > max_str_len:
            max_str_len = str_len

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