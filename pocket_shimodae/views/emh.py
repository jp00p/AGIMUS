from common import *
from pocket_shimodae.objects.poshimo import Poshimo
from pocket_shimodae.objects.poshimo.stat import PoshimoStat
from ..ui import *
from . import main_menu as mm

base_heal_cost = 10
base_revive_cost = 50

class SummonEMH(PoshimoView):
  ''' heal and revive poshimo!  basically an Inn, or pokecenter '''
  def __init__(self, cog, trainer):
    super().__init__(cog, trainer)
    
    self.eligible_heal_poshimo = self.trainer.list_all_poshimo(exclude=[PoshimoStatus.DEAD])
    self.eligible_revive_poshimo = self.trainer.list_all_poshimo(include=[PoshimoStatus.DEAD])
    poshimo_hp_cost = sum((p.max_hp - p.hp for p in self.eligible_heal_poshimo))
    poshimo_stam_cost = 0

    for p in self.eligible_heal_poshimo:
      stam = p.get_all_stamina()
      missing_stam = stam[1] - stam[0]
      poshimo_stam_cost += missing_stam

    total_heal_cost = (poshimo_hp_cost + poshimo_stam_cost) * base_heal_cost

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
      ).set_footer(text=f"Your scarves: {self.trainer.scarves}")
    ]
    
    self.add_item(ReviveButton(self.cog, self.trainer))
    self.add_item(HealAllButton(self.cog, self.trainer, label=f"Heal all Poshimo (cost: {total_heal_cost})", cost=total_heal_cost))
    self.add_item(mm.BackToMainMenu(self.cog, self.trainer))


class EMHCancelButton(discord.ui.Button):
  ''' cancel selection '''
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
  ''' revive a poshimo '''
  def __init__(self, cog, trainer):
    self.cog = cog
    self.trainer:PoshimoTrainer = trainer
    self.dead_poshimo = self.trainer.list_all_poshimo(include=[PoshimoStatus.DEAD])
    super().__init__(
      label="Revive a Poshimo",
      emoji="😇",
      disabled=bool(len(self.dead_poshimo)<=0),
      row=1
    )
  async def callback(self, interaction: discord.Interaction):
    self.view.add_item(SelectRevive(self.cog, self.trainer))
    self.view.add_item(EMHCancelButton(self.cog, self.trainer))
    await interaction.response.edit_message(view=self.view, embed=self.view.get_embed())

class SelectRevive(PoshimoSelect):
  ''' choose which poshimo to revive '''
  def __init__(self, cog, trainer:PoshimoTrainer, include=[PoshimoStatus.DEAD], custom_placeholder="Choose a Poshimo to revive"):
    poshimo_list = trainer.list_all_poshimo(include=include)
    # custom option list for this poshimoselect
    custom_options = [discord.SelectOption(label=f"{p.name} (cost: {p.level * base_revive_cost})", value=str(key)) for key,p in enumerate(poshimo_list)]
    super().__init__(cog, trainer, include=include, custom_placeholder=custom_placeholder, custom_options=custom_options, row=0)
  
  async def callback(self, interaction: discord.Interaction):
    self.get_selected_poshimo()
    cost = self.selected_poshimo.level * base_revive_cost
    self.trainer.scarves -= cost
    self.selected_poshimo.revive()
    self.selected_poshimo.full_restore()
    view = SummonEMH(self.cog, self.trainer)
    view.embeds.append(
      discord.Embed(
        title=f"{self.selected_poshimo} has been revived!",
        description=f"You paid {cost} scarves to revive them."
      ).set_footer(text=f"You have {self.trainer.scarves} scarves left.")
    )
    await interaction.response.edit_message(view=view, embeds=view.get_embeds())

class HealAllButton(discord.ui.Button):
  ''' heal all poshimo '''
  def __init__(self, cog, trainer, cost=0, **kwargs):
    self.cog = cog
    self.trainer = trainer
    self.cost = cost
    super().__init__(
      emoji="💊",
      disabled=bool(self.trainer.scarves <= self.cost or self.cost <= 0),
      row=1,
      **kwargs
    )
  async def callback(self, interaction:discord.Interaction):
    view = ConfirmHealAll(self.cog, self.trainer, cost=self.cost)
    await interaction.response.edit_message(view=view, embed=view.get_embed())

class ConfirmHealAll(PoshimoConfirmation):
  ''' heal all confirmation '''
  def __init__(self, cog, trainer, cost):
    super().__init__(cog, trainer)
    self.cost = cost
    self.embeds = [
      discord.Embed(
        title=f"Fully restore all your Poshimo, are you sure?",
        description=fill_embed_text(f"This will cost **{self.cost}** scarves.")
      )
    ]
  async def cancel_callback(self, button, interaction):
    view = SummonEMH(self.cog, self.trainer)
    await interaction.response.edit_message(view=view, embed=view.get_embed())
  
  async def confirm_callback(self, button, interaction):
    self.trainer.scarves -= self.cost
    report = []
    for p in self.trainer.list_all_poshimo(exclude=[PoshimoStatus.DEAD]):
      heal_amt = p.max_hp - p.hp
      p.full_restore()
      if heal_amt > 0:
        report.append((p.display_name, heal_amt))

    description = f"You paid {self.cost} scarves!\n"
    description += "\n".join([f"**{m[0]}**: healed {m[1]} hp!" for m in report])
    description += "\n...and all Poshimo's moves have had their stamina restored! (except any poor, dead Poshimo.)\nThank you for using the EMH."
    view = SummonEMH(self.cog, self.trainer)
    view.embeds.append(discord.Embed(
      title="All Poshimo healed!",
      description=description
    ))

    await interaction.response.edit_message(view=view, embeds=view.get_embeds())