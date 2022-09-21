from common import *
from ..ui import PoshimoView, Confirmation 
from ..objects import Poshimo, PoshimoTrainer, PoshimoMove
import pocket_shimodae.utils as utils

class ManageStart(PoshimoView):
  """ 
  start of /ps manage command
  """
  def __init__(self, cog, discord_id):
    super().__init__(cog)
    self.discord_id = discord_id
    self.trainer = utils.get_trainer(discord_id=self.discord_id)
    self.embeds = [
      discord.Embed(
        title="Manage your Poshimo", 
        description="Swap, rename, release, or just examine your Poshimo."
      )
    ]
    self.add_item(ManageMenu(cog, self.trainer))

class ManageMenu(discord.ui.Select):
  """ 
  select menu for choosing which poshimo to manage 
  """
  def __init__(self, cog, trainer:PoshimoTrainer):
    self.cog = cog
    self.trainer = trainer
    options = []
    for i,poshimo in enumerate(self.trainer.list_all_poshimo()):
      label = f"{poshimo.display_name}"
      if poshimo.id == self.trainer.active_poshimo.id:
        label += f" (active)"
      options.append(discord.SelectOption(
        label=f"{label}",
        value=f"{poshimo.id}"
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
    view = ForgetMove_Confirmation(self.cog, self.poshimo, self.values[0], self.trainer)
    await interaction.response.edit_message(view=view, embed=view.get_embed())

class ForgetMove_Confirmation(Confirmation):
  """
  make sure they really want to forget this move
  """
  def __init__(self, cog:discord.Cog, poshimo:Poshimo, move_index, trainer:PoshimoTrainer):
    super().__init__(cog)
    self.poshimo = poshimo
    self.move_index = int(move_index)
    self.trainer = trainer
    self.embeds = [
      discord.Embed(
        title=f"Are you sure you want to forget this move?",
        description=f"```{self.poshimo.move_list[self.move_index]}```\n**This cannot be undone.**"
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

class ReleasePoshimo_Confirmation(Confirmation):
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
        description=f"{poshimo.types}",
        fields=[
          discord.EmbedField(
            name=f"{stat.replace('_',' ').capitalize()}",
            value=f"{value}",
            inline=True
          ) 
          for stat,value in self.stats.items()] # fancy list here watch out
      ).set_thumbnail(url="https://i.imgur.com/lIBEIFL.jpeg"),
      discord.Embed(
        title=f"⚠ Are you sure you want to release this Poshimo into the wild? ⚠",
        description=f"You cannot undo this. You will lose this Poshimo __forever__... *presumably*."
      )
    ]
  async def cancel_callback(self, button, interaction):
    view = ManagePoshimoScreen(self.cog, self.poshimo, self.trainer)
    await interaction.response.edit_message(view=view, embeds=view.get_embeds(), content="Canceled, your Poshimo are safe with you for now.")

  async def confirm_callback(self, button, interaction):
    released_poshimo = self.poshimo
    self.trainer.release_poshimo(self.poshimo)
    view = ManageStart(self.cog, self.trainer.discord_id)
    await interaction.response.edit_message(content=f"{released_poshimo.display_name} has been released into the wild. Goodbye lil friend 🙋‍♀️", view=view, embed=view.get_embed())
    

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
    await interaction.response.send_message(
      content=f"{old_name}'s name has been updated to {self.poshimo.display_name}!",
      view=view,
      embeds=view.get_embeds(),
      ephemeral=True
    )

class ManagePoshimoScreen(PoshimoView):
  """ 
  view for managing a specific poshimo
  this one has all the buttons
  """
  def __init__(self, cog, poshimo:Poshimo, trainer:PoshimoTrainer):
    super().__init__(cog)
    self.cog = cog
    self.poshimo = poshimo
    self.stats = self.poshimo.list_stats()
    self.trainer = trainer
    self.embeds = [
      discord.Embed( # stats embed
        title=f"{poshimo.display_name}:", 
        description=f"{poshimo.types}",
        fields=[
          discord.EmbedField(
            name=f"{stat.replace('_',' ').capitalize()}",
            value=f"{value}",
            inline=True
          ) 
          for stat,value in self.stats.items()] # fancy list here watch out
      ).set_thumbnail(url="https://i.imgur.com/lIBEIFL.jpeg"),
      
      discord.Embed( # moves embed
        title=f"{poshimo.display_name}'s moves:",
        description=f"{'-'*80}"
      )
    ]
    move_mojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
    # add moves to fields
    self.embeds[1].fields += [
      discord.EmbedField(
        name=f"{move_mojis[i]} {move.display_name} ({move.stamina}/{move.max_stamina})",
        value=f"**{move.type.name.title()}**-type move\n*{move.description}*",
        inline=False
      )
      for i,move in enumerate(poshimo.move_list)]
  
  @discord.ui.button(style=discord.ButtonStyle.primary,label="Set active", custom_id="activate", emoji="🤙", row=1)
  async def activate_callback(self, button, interaction:discord.Interaction):
    """ 
    activate the selected poshimo 
    """
    if self.trainer.active_poshimo:
      if int(self.poshimo.id) == int(self.trainer.active_poshimo.id):
        await interaction.response.edit_message(
          content="😂 This Poshimo is already active! 🤡"
        )
      else:
        # if they already have an active poshimo, move it into the sac
        temp_sac = self.trainer.poshimo_sac
        old_poshimo = self.trainer.active_poshimo
        
        self.trainer.active_poshimo = self.poshimo
        temp_sac.append(old_poshimo)
        for p in temp_sac:
          if p.id == self.poshimo.id:
            temp_sac.remove(p)
        self.trainer.poshimo_sac = temp_sac
        await interaction.response.edit_message(
          content=f"✅ {self.poshimo.display_name} has been set to active! {old_poshimo.display_name} has been stuffed into your sac."
        )
    else:
      self.trainer.active_poshimo = self.poshimo
      temp_sac = self.trainer.poshimo_sac
      for p in temp_sac:
        if p.id == self.poshimo.id:
          temp_sac.remove(p)
      self.trainer.poshimo_sac = temp_sac
      
      await interaction.response.edit_message(
        content=f"✅ {self.poshimo.display_name} has been set to active!"
      )

  @discord.ui.button(style=discord.ButtonStyle.green,label="Rename", custom_id="rename", emoji="✏", row=1)
  async def rename_callback(self, button, interaction:discord.Interaction):
    """ 
    rename the selected poshimo 
    """
    await interaction.response.send_modal(
      PoshiModal_Rename(
        title=f"Rename {self.poshimo.display_name}?",
        cog=self.cog,
        poshimo=self.poshimo,
        trainer=self.trainer
      )
    )

  @discord.ui.button(style=discord.ButtonStyle.danger,label="Forget move", custom_id="forget_move", row=1, emoji="🧠")
  async def forget_callback(self, button, interaction:discord.Interaction):
    """ 
    forget a move from the selected poshimo
    """
    if len(self.poshimo.move_list) <= 1:
      await interaction.response.edit_message(content="You cannot forget a Poshimo's last move!")
    else:
      self.add_item(MoveMenu(self.cog, self.poshimo, self.trainer))
      await interaction.response.edit_message(content="", view=self, embeds=self.embeds)
 
  @discord.ui.button(style=discord.ButtonStyle.danger,label="Release", custom_id="release", row=1, emoji="⚠")
  async def release_callback(self, button, interaction:discord.Interaction):
    """
    release selected poshimo into the wild
    """
    if len(self.trainer.list_all_poshimo()) <= 1:
      await interaction.response.edit_message(content="⚠ You cannot release your only Poshimo! What are you thinking?!", view=self, embeds=self.embeds)
    else:
      view = ReleasePoshimo_Confirmation(self.cog, self.poshimo, self.trainer)
      await interaction.response.edit_message(content="", view=view, embeds=view.get_embeds())
  
  @discord.ui.button(style=discord.ButtonStyle.gray,label="Back to list", custom_id="back", row=2, emoji="🔙")
  async def back_callback(self, button, interaction:discord.Interaction):
    """
    cancel managing this poshimo
    """
    view = ManageStart(self.cog, self.trainer.discord_id)
    await interaction.response.edit_message(content="", view=view, embed=view.get_embed())

  @discord.ui.button(style=discord.ButtonStyle.gray,label="Cancel", custom_id="cancel", row=2, emoji="✖")
  async def cancel_callback(self, button, interaction:discord.Interaction):
    """
    cancel managing this poshimo
    """
    await interaction.response.edit_message(content="Thanks for visiting your Poshimo! They will miss you.", view=None, embed=None)