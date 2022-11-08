from common import *
from pocket_shimodae.objects.poshimo.stat import PoshimoStat
from ..ui import *
from ..objects import Poshimo, PoshimoTrainer, PoshimoMove
from . import main_menu as mm

class ManageStart(PoshimoView):
  def __init__(self, cog, trainer):
    super().__init__(cog, trainer)
    self.embeds = [
      discord.Embed(
        title="Manage your Poshimo", 
        description=fill_embed_text("Swap, rename, release, or just examine your Poshimo.")
      )
    ]
    if len(self.trainer.list_all_poshimo()) > 0:
      self.add_item(ManageMenu(self.cog, self.trainer))
    else:
      self.embeds[0].description += f"\nHey, where are all your Poshimo??? WTF?"
    
    self.add_item(mm.BackToMainMenu(self.cog, self.trainer))

class ManageMenu(discord.ui.Select):
  """ 
  select menu for choosing which poshimo to manage 
  """
  def __init__(self, cog, trainer:PoshimoTrainer):
    self.cog = cog
    self.trainer = trainer
    options = []   
    trainers_poshimo = self.trainer.list_all_poshimo()

    for poshimo in trainers_poshimo:
      label = f"{poshimo.display_name}"
      emoji = None
      if self.trainer.active_poshimo and poshimo.id == self.trainer.active_poshimo.id:
        emoji = "🎀"
      
      options.append(discord.SelectOption(
        label=f"{label}",
        value=f"{poshimo.id}",
        emoji=emoji
      ))
    super().__init__(
      placeholder="Select the Poshimo to manage",
      options=options
    )
  async def callback(self, interaction:discord.Interaction):
    """ 
    user has chosen a poshimo to manage 
    """
    poshimo = Poshimo(id=int(self.values[0]))
    view = ManagePoshimoScreen(self.cog, poshimo, self.trainer)
    await interaction.response.edit_message(content=f"Now managing {poshimo.display_name}", view=view, embeds=view.get_embeds())

class MoveMenu(discord.ui.Select):
  """ 
  select a move to remove
  """
  def __init__(self, cog, poshimo:Poshimo, trainer:PoshimoTrainer):
    self.cog = cog
    self.trainer = trainer
    self.poshimo = poshimo
    options = []
    for num,move in enumerate(self.poshimo.move_list):
      if move and move != "":
        options.append(discord.SelectOption(
          label=f"{move.display_name}",
          value=f"{num}"
        ))
    super().__init__(
      placeholder="Choose the move to forget",
      options=options
    )
  async def callback(self, interaction:discord.Interaction):
    view = ForgetMove_PoshimoConfirmation(self.cog, self.poshimo, self.values[0], self.trainer)
    await interaction.response.edit_message(view=view, embed=view.get_embed())

class ForgetMove_PoshimoConfirmation(PoshimoConfirmation):
  """
  make sure they really want to forget this move
  """
  def __init__(self, cog:discord.Cog, poshimo:Poshimo, move_index, trainer:PoshimoTrainer):
    super().__init__(cog, trainer)
    self.poshimo = poshimo
    self.move_index = int(move_index)
    the_move = self.poshimo.move_list[self.move_index]
    self.embeds = [
      discord.Embed(
        title=f"Are you sure you want to forget this move?",
        description=f"> {the_move.display_name}\n> Stamina: {the_move.stamina}/{the_move.max_stamina}\n> {the_move.description}\n⚠ **This cannot be undone.** ⚠"
      )
    ]
  async def cancel_callback(self, button, interaction:discord.Interaction):
    """ go back to manage screen """
    view = ManagePoshimoScreen(self.cog, self.poshimo, self.trainer)
    await interaction.response.edit_message(view=view, embeds=view.get_embeds(), content="Canceled, nothing has been removed.")

  async def confirm_callback(self, button, interaction:discord.Interaction):
    """ remove the move and go back to manage screen """
    temp_list = self.poshimo.move_list
    temp_list.pop(self.move_index)
    self.poshimo.move_list = temp_list
    view = ManagePoshimoScreen(self.cog, self.poshimo, self.trainer)
    await interaction.response.edit_message(view=view, embeds=view.get_embeds(), content="Move reMoved!")

class ReleasePoshimo_PoshimoConfirmation(PoshimoConfirmation):
  """
  make sure they really want to release a Poshimo
  """
  def __init__(self, cog:discord.Cog, poshimo:Poshimo, trainer:PoshimoTrainer):
    super().__init__(cog)
    self.poshimo = poshimo
    self.trainer = trainer
    self.stats = self.poshimo.list_stats()
    self.embeds = [
      discord.Embed( # stats embed
        title=f"{poshimo.display_name}:", 
        description=f"{poshimo.show_types()}",
        fields=[
          discord.EmbedField(
            name=f"{statname.replace('_',' ').capitalize()}",
            value=f"{stat}",
            inline=True
          ) 
          for statname,stat in self.stats.items()] # fancy list here watch out
      ).set_thumbnail(url="https://i.imgur.com/lIBEIFL.jpeg"),
      discord.Embed(
        title=f"⚠ Are you sure you want to release this Poshimo into the wild? ⚠",
        description=fill_embed_text("You cannot undo this. You will lose this Poshimo __forever__... *presumably*.")
      )
    ]
  async def cancel_callback(self, button, interaction):
    view = ManagePoshimoScreen(self.cog, self.poshimo, self.trainer)
    view.add_notification("Canceled!","Canceled releasing, your Poshimo are safe with you ...for now.")
    await interaction.response.edit_message(view=view, embeds=view.get_embeds())

  async def confirm_callback(self, button, interaction):
    released_poshimo = self.poshimo
    self.trainer.release_poshimo(self.poshimo)
    view = ManageStart(self.cog, self.trainer.discord_id)
    view.embeds.append(
      discord.Embed(
        title="Farewell!",
        description=f"{released_poshimo.display_name} has been released into the wild. Goodbye lil friend 🙋‍♀️"
      )
    )
    await interaction.response.edit_message(view=view, embeds=view.get_embeds())
    

class PoshiModal_Rename(discord.ui.Modal):
  """ 
  modal that handles renaming poshimo 
  """
  def __init__(self, cog, poshimo:Poshimo, trainer, *args, **kwargs) -> None:
    super().__init__(*args, **kwargs)
    self.poshimo = poshimo
    self.cog = cog
    self.trainer = trainer
    self.add_item(discord.ui.InputText(label="New name:", placeholder=f"{self.poshimo.display_name}", min_length=3, max_length=48))

  async def callback(self, interaction: discord.Interaction):
    """ rename that poshimo """
    old_name = self.poshimo.display_name
    self.poshimo.display_name = self.children[0].value # magic
    view = ManagePoshimoScreen(self.cog, self.poshimo, self.trainer)
    view.add_notification("Renamed!", f"{old_name}'s name has been updated to {self.poshimo.display_name}!")
    await interaction.response.edit_message(view=view, embeds=view.get_embeds())

class ManagePoshimoScreen(PoshimoView):
  """ 
  view for managing a specific poshimo
  this one has all the buttons
  """
  def __init__(self, cog, poshimo:Poshimo, trainer:PoshimoTrainer):
    super().__init__(cog, trainer)
    self.poshimo = poshimo
    self.stats = self.poshimo.list_stats()
    self.unavailable = bool(self.poshimo.status is PoshimoStatus.AWAY or self.poshimo.status is PoshimoStatus.DEAD or self.poshimo.in_combat)
    self.embeds = [
      discord.Embed( # main embed
        title=f"{self.poshimo.display_name} ({poshimo.name})",
        description=fill_embed_text(f"{self.poshimo.show_types()}\n{self.poshimo.status}")
      )
    ]

    if self.unavailable:
      if self.poshimo.status is PoshimoStatus.DEAD:
        reason = "It's dead!"
      if self.poshimo.status is PoshimoStatus.AWAY:
        reason = "It's on an away mission!"
      if self.poshimo.in_combat:
        reason = "It's in combat!"
      self.embeds[0].description += f"\nYour Poshimo is currently unavailable to manage: **{reason}**"

    for stat, value in self.stats.items():
      val = f"{value}"
      if stat not in ["hp", "level", "personality", "xp"]:
        val = f"{value}\n{progress_bar(value.xp/100, num_bricks=5)}"
      elif stat == "hp":
        hpprog = (self.poshimo.hp / self.poshimo.max_hp)
        val = f"{value}\n{progress_bar(hpprog, num_bricks=5, filled='🟩')}"
      self.embeds[0].add_field(
        name=f"{stat.replace('_',' ').capitalize()}",
        value=val
      )

    #self.embeds[0].set_thumbnail(url="https://i.imgur.com/lIBEIFL.jpeg")
    self.embeds.append(
      discord.Embed( # moves embed
        title=f"{self.poshimo.display_name}'s moves:",
        description=f""
      )
    )
  
    move_mojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
    # add moves to fields
    
    self.embeds[1].fields += [
      discord.EmbedField(
        name=fill_embed_text(f"{move_mojis[i]} {move.display_name} ({move.stamina}/{move.max_stamina})"),
        value=f"**{move.type.name.title()}**-type move\n*{move.description}*",
        inline=False
      )
      for i,move in enumerate(poshimo.move_list)]

    self.add_item(ActivateButton(self.cog, self.trainer, self.poshimo, self.unavailable))
    self.add_item(RenameButton(self.cog, self.trainer, self.poshimo, self.unavailable))
    self.add_item(ForgetMoveButton(self.cog, self.trainer, self.poshimo, self.unavailable))
    self.add_item(ReleaseButton(self.cog, self.trainer, self.poshimo, self.unavailable))
    self.add_item(ManageCancel(self.cog, self.trainer))
    self.add_item(mm.BackToMainMenu(self.cog, self.trainer))

class ActivateButton(discord.ui.Button):
  def __init__(self, cog, trainer, poshimo, disabled=False):
    self.cog = cog
    self.trainer:PoshimoTrainer = trainer
    self.poshimo:Poshimo = poshimo
    super().__init__(
      label="Set to active",
      emoji="🎀",
      row=1,
      style=discord.ButtonStyle.green,
      disabled=bool(disabled or self.trainer.active_poshimo.id == self.poshimo.id)
    )
  async def callback(self, interaction: discord.Interaction):
    """ 
    activate the selected poshimo 
    """
    old_poshimo = self.trainer.set_active_poshimo(self.poshimo)
    message = f"✅ {self.poshimo.display_name} has been set to active!"
    if old_poshimo:
      message += f"\n{old_poshimo.display_name} has been returned to your sac."
    view = ManagePoshimoScreen(self.cog, self.poshimo, self.trainer)
    view.add_notification("Success", message)
    await interaction.response.edit_message(view=view, embeds=view.get_embeds())

class RenameButton(discord.ui.Button):
  def __init__(self, cog, trainer, poshimo, disabled=False):
    self.cog = cog
    self.trainer = trainer
    self.poshimo = poshimo
    super().__init__(
      label="Rename",
      emoji="✏",
      row=1,
      style=discord.ButtonStyle.blurple,
      disabled=disabled
    )
  async def callback(self, interaction: discord.Interaction):
    await interaction.response.send_modal(
      PoshiModal_Rename(
        title=f"Rename {self.poshimo.display_name}?",
        cog=self.cog,
        poshimo=self.poshimo,
        trainer=self.trainer
      )
    )

class ForgetMoveButton(discord.ui.Button):
  def __init__(self, cog, trainer, poshimo, disabled=False):
    self.cog = cog
    self.trainer = trainer
    self.poshimo = poshimo
    super().__init__(
      label="Forget a move",
      emoji="🚫",
      row=2,
      style=discord.ButtonStyle.danger,
      disabled=disabled
    )
  async def callback(self, interaction: discord.Interaction):
    view = ManagePoshimoScreen(self.cog, self.poshimo, self.trainer)
    if len(self.poshimo.move_list) <= 1:
      view.add_notification("Whoa!", "You cannot forget a Poshimo's last move!")
    else:
      view.add_item(MoveMenu(self.cog, self.poshimo, self.trainer))
      await interaction.response.edit_message(view=view, embeds=view.get_embeds())

class ReleaseButton(discord.ui.Button):
  def __init__(self, cog, trainer, poshimo, disabled=False):
    self.cog = cog
    self.trainer = trainer
    self.poshimo = poshimo
    super().__init__(
      label="Release this Poshimo",
      emoji="⚠",
      row=2,
      style=discord.ButtonStyle.danger,
      disabled=disabled
    )
  async def callback(self, interaction: discord.Interaction):
    if len(self.trainer.list_all_poshimo()) <= 1:
      view = ManagePoshimoScreen(self.cog, self.poshimo, self.trainer)
      view.add_notification("Hey now", "⚠ You cannot release your only Poshimo! What are you thinking?!") 
    else:
      view = ReleasePoshimo_PoshimoConfirmation(self.cog, self.poshimo, self.trainer)
    await interaction.response.edit_message(view=view, embeds=view.get_embeds())

class ManageCancel(discord.ui.Button):
  def __init__(self, cog, trainer):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      label="Cancel",
      emoji="🔙",
      row=4
    )
  async def callback(self, interaction: discord.Interaction):
    view = ManageStart(self.cog, self.trainer)
    await interaction.response.edit_message(view=view, embed=view.get_embed())