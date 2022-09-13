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
    logger.info(f"Running status for user: {self.trainer.__dict__}")
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
          discord.EmbedField(name="Belt buckles", value=f"{self.trainer.buckles}")
        ]
      )
    ]