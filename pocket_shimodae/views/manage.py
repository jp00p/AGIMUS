from common import *
from ..ui import PoshimoView, Confirmation
from ..objects import Poshimo, PoshimoTrainer, PoshimoMove

class ManageStart(PoshimoView):
  """ 
  start of /ps manage command
  """
  def __init__(self, cog, discord_id):
    super().__init__(cog)
    self.discord_id = discord_id
    self.trainer = self.game.get_trainer(self.discord_id)
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
    for poshimo in self.trainer.list_all_poshimo():
      options.append(discord.SelectOption(
        label=f"{poshimo.display_name}",
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
    poshimo = Poshimo(id=self.values[0])
    view = ManagePoshimoScreen(self.cog, poshimo, self.trainer)
    embed = view.get_embed()
    await interaction.response.edit_message(content=f"Now managing {poshimo.display_name}", view=view, embed=embed)

class MoveMenu(discord.ui.Select):
  """ 
  select a move to remove
  """
  def __init__(self, cog, poshimo:Poshimo, trainer:PoshimoTrainer):
    self.cog = cog
    self.trainer = trainer
    self.poshimo = poshimo
    options = []
    for move in self.poshimo.move_list:
      if move and move != "":
        options.append(discord.SelectOption(
          label=f"{move.display_name}"
        ))
    super().__init__(
      placeholder="Forget which move?",
      options=options
    )
  async def callback(self, interaction:discord.Interaction):
    """
    user has selected a move to forget
    """
    pass

class ForgetMove_Confirmation(Confirmation):
  """
  make sure they really want to forget this move
  """
  def __init__(self, cog, poshimo, choice):
    super().__init__()
    self.embeds = [
      discord.Embed(
        title=f"Are you sure you want to forget this move?",
        description="This cannot be undone."
      )
    ]

class PoshiModal_Rename(discord.ui.Modal):
  """ 
  modal that handles renaming poshimo 
  """
  def __init__(self, cog, poshimo:Poshimo, trainer, *args, **kwargs) -> None:
    super().__init__(*args, **kwargs)
    self.poshimo = poshimo
    self.cog = cog
    self.trainer = trainer
    self.add_item(discord.ui.InputText(label="New name:", placeholder=f"{self.poshimo.display_name}"))

  async def callback(self, interaction: discord.Interaction):
    old_name = self.poshimo.display_name
    self.poshimo.display_name = self.children[0].value
    view = ManagePoshimoScreen(self.cog, self.poshimo, self.trainer)
    await interaction.response.send_message(
      content=f"{old_name}'s name has been updated to {self.poshimo.display_name}!",
      view=view,
      embed=view.get_embed(),
      ephemeral=True
    )

class ManagePoshimoScreen(PoshimoView):
  """ 
  view for managing a specific poshimo
  this one has all the buttons
  """
  def __init__(self, cog, poshimo:Poshimo, trainer:PoshimoTrainer):
    super().__init__(cog)
    self.poshimo = poshimo
    self.stats = poshimo.list_stats()
    self.trainer = trainer
    self.embeds = [
      discord.Embed(
        title=f"{poshimo.display_name}:", 
        description=f"{poshimo.types}",
        fields=[
          discord.EmbedField(
            name=f"{stat.replace('_',' ').capitalize()}",
            value=f"{value}",
            inline=True
          ) 
          for stat,value in self.stats.items()] # fancy list here watch out
      ).set_thumbnail(url="https://i.imgur.com/lIBEIFL.jpeg")
    ]
    move_mojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
    # add moves to fields
    self.embeds[0].fields += [
      discord.EmbedField(
        name=f"{move_mojis[i]} {move.display_name} ({move.stamina}/{move.max_stamina})",
        value=f"**{move.type.name.title()}**-type move\n*{move.description}*"
      )
      for i,move in enumerate(poshimo.move_list)]
  
  @discord.ui.button(style=discord.ButtonStyle.primary,label="Set active", custom_id="activate", emoji="🤙", row=1)
  async def activate_callback(self, button, interaction:discord.Interaction):
    """ 
    activate the selected poshimo 
    """
    if int(self.poshimo.id) == int(self.trainer.active_poshimo.id):
      await interaction.response.edit_message(
        content="😂 This Poshimo is already active! 🤡"
      )
    else:
      temp_sac = self.trainer.poshimo_sac
      old_poshimo = self.trainer.active_poshimo
      temp_sac.append(old_poshimo)
      self.trainer.active_poshimo = self.poshimo
      self.trainer.poshimo_sac = temp_sac
      await interaction.response.edit_message(
        content=f"✅ {self.poshimo.display_name} has been set to active! {old_poshimo} has been stuffed into your sac."
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
    await interaction.response.send_message(f"Nice button pressing {button.custom_id}")
 
  @discord.ui.button(style=discord.ButtonStyle.danger,label="Release", custom_id="release", row=1, emoji="⚠")
  async def release_callback(self, button, interaction:discord.Interaction):
    """
    release selected poshimo into the wild
    """
    logger.info(button.custom_id)
    await interaction.response.send_message(f"Nice button pressing {button.custom_id}")
  
  @discord.ui.button(style=discord.ButtonStyle.gray,label="Cancel", custom_id="cancel", row=2, emoji="🔙")
  async def cancel_callback(self, button, interaction:discord.Interaction):
    """
    cancel managing this poshimo
    """
    logger.info(button.custom_id)
    await interaction.response.send_message(f"Nice button pressing {button.custom_id}")