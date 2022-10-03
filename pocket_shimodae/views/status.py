"""
this contains all the views for a player's status
"""
from common import *
from ..ui import PoshimoView, Confirmation
import pocket_shimodae.utils as utils

spacer = f"{'⠀'*53}" # fills out the embed to max width

class Status(PoshimoView):
  def __init__(self, cog, discord_id):
    super().__init__(cog)
    self.discord_id = discord_id
    self.trainer = utils.get_trainer(discord_id=self.discord_id)
    self.trainer_location = self.game.find_in_world(self.trainer.location)
    
    status_screen_buttons = [
      pages.PaginatorButton("prev", emoji="⏪"),
      pages.PaginatorButton("next", emoji="⏩")
    ]

    main_status_embed = discord.Embed(
      title=f"TRAINER #{self.trainer.id} STATUS",
      description=f"{spacer}",
      fields=[
        discord.EmbedField(name="Status", value=f"{self.trainer.status}"),
        discord.EmbedField(name="Wins/losses", value=f"{self.trainer.wins}/{self.trainer.losses}"),
        discord.EmbedField(name="Active Poshimo", value=f"{self.trainer.active_poshimo}"),
        discord.EmbedField(name="Poshimo in sac", value=f"{self.trainer.list_sac()}"),
        discord.EmbedField(name="Scarves", value=f"{self.trainer.scarves}"),
        discord.EmbedField(name="Belt buckles", value=f"{self.trainer.buckles}"),
        discord.EmbedField(name="Location", value=f"{self.trainer_location}", inline=False)
      ]
    )
    
    trainer_fishing_log = self.trainer.get_fishing_log()
    fields = [discord.EmbedField(name=f"{f.name}", value=f"{f.length}cm") for f in trainer_fishing_log]

    fishing_log_embed = discord.Embed(
      title=f"FISHING LOG",
      description=f"Your lengthiest fish:\n{spacer}",
      fields=fields[:10]
    )

    self.page_groups = [
      pages.PageGroup(
        pages=[pages.Page(embeds=[main_status_embed])],
        label="Basic status",
        description="Your overall details at a glance"
      ),
      pages.PageGroup(
        pages=[pages.Page(embeds=[fishing_log_embed])],
        label="Fishing log",
        description="Your fishing history"
      )
    ]

    self.paginator = pages.Paginator(
      pages=self.page_groups,
      show_menu=True,
      custom_view=self,
      show_disabled=False,
      loop_pages=False,
      show_indicator=False,
      use_default_buttons=False,
      custom_buttons=status_screen_buttons,
      menu_placeholder="Profile sections"
    )