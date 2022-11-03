from common import *
from pocket_shimodae.objects.poshimo.stat import PoshimoStat
from ..ui import *
from . import main_menu as mm


base_heal_cost = 5
base_revive_cost = 50

class SummonEMH(PoshimoView):
  # EMH appears
  # choices: Heal one, heal all
  def __init__(self, cog, trainer):
    super().__init__(cog, trainer)
    
    self.eligible_heal_poshimo = self.trainer.list_all_poshimo(include=[PoshimoStatus.IDLE])
    self.eligible_revive_poshimo = self.trainer.list_all_poshimo(include=[PoshimoStatus.DEAD])
    poshimo_hp_cost = sum((p.max_hp - p.hp for p in self.eligible_heal_poshimo))
    total_heal_cost = poshimo_hp_cost * base_heal_cost

    self.embeds = [
      discord.Embed(
        title="The EMH appears before you",
        description=fill_embed_text("\"Please state the nature of the holo-emergency.\""),
        fields=[
          discord.EmbedField(
            name="Revive a Poshimo",
            value="Bring a Poshimo back to life"
          ),
          discord.EmbedField(
            name="Heal all Poshimo",
            value="Restores all HP and stamina (except away Poshimo)"
          ),
        ]
      ).set_footer(text="Pay me or I'll send Photonic Andy Dick after you!")
    ]
    
    self.add_item(ReviveButton(self.cog, self.trainer))
    self.add_item(HealAllButton(self.cog, self.trainer, label=f"Heal all Poshimo (cost: {total_heal_cost})"))
    self.add_item(mm.BackToMainMenu(self.cog, self.trainer))


class EMHCancelButton(discord.ui.Button):
  def __init__(self, cog, trainer):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      label="Cancel",
      style=discord.ButtonStyle.secondary,
      emoji="❌",
      row=1
    )
  async def callback(self, interaction:discord.Interaction):
    view = SummonEMH(self.cog, self.trainer)
    await interaction.response.edit_message(view=view, embed=view.get_embed())

class ReviveButton(discord.ui.Button):
  def __init__(self, cog, trainer):
    self.cog = cog
    self.trainer:PoshimoTrainer = trainer
    self.dead_poshimo = self.trainer.list_all_poshimo(include=[PoshimoStatus.DEAD])
    super().__init__(
      label="Revive a Poshimo",
      emoji="😇",
      disabled=bool(len(self.dead_poshimo)<=0)
    )
  async def callback(self, interaction: discord.Interaction):
    self.view.add_item(
      PoshimoSelect(self.cog, self.trainer, include=[PoshimoStatus.DEAD], custom_placeholder="Choose a Poshimo to revive")
    )
    self.view.add_item(EMHCancelButton(self.cog, self.trainer))
    await interaction.response.edit_message(view=self.view, embed=self.view.get_embed())

class HealAllButton(discord.ui.Button):
  def __init__(self, cog, trainer, **kwargs):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      emoji="💊",
      **kwargs
    )
  async def callback(self, interaction:discord.Interaction):
    pass
    # cost
    # cancel
    # confirm

class HealAll(PoshimoView):
  def __init__(self, cog, trainer):
    super().__init__(cog, trainer)

    base_cost = 10 # per HP lost
    