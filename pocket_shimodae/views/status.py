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
    trainer_dict = self.trainer.__dict__
    self.embeds = [
      discord.Embed(
        title=f"TRAINER #{self.trainer.id} STATUS",
        description=f"Here is your Trainer object:\n{trainer_dict}"
      )
    ]