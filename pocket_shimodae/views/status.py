"""
this contains all the views for a player's status
"""
from common import *
from pocket_shimodae.game import PoshimoGame
from ..ui import PoshimoView, Confirmation

class Status(PoshimoView):
  def __init__(self, cog, discord_id):
    super().__init__(cog)
    self.discord_id = discord_id
    self.trainer = self.game.get_trainer(self.discord_id)
    self.trainer_location = self.game.find_in_world(self.trainer.location)
    self.embeds = [
      discord.Embed(
        title=f"TRAINER #{self.trainer.id} STATUS",
        description=f"Your details, my lord.",
        fields=[
          discord.EmbedField(name="Current status", value=f"{self.trainer.status}"),
          discord.EmbedField(name="Wins/losses", value=f"{self.trainer.wins}/{self.trainer.losses}"),
          discord.EmbedField(name="Active Poshimo", value=f"{self.trainer.active_poshimo}"),
          discord.EmbedField(name="Poshimo in sac", value=f"{self.trainer.list_sac()}"),
          discord.EmbedField(name="Scarves", value=f"{self.trainer.scarves}"),
          discord.EmbedField(name="Belt buckles", value=f"{self.trainer.buckles}"),
          discord.EmbedField(name="Location", value=f"{self.trainer_location.name}\n**weather**: {self.trainer_location.weather}\n**biome**: {self.trainer_location.biome}", inline=False)
        ]
      )