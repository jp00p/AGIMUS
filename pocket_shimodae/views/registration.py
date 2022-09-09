""" all the registration stuff, choosing a poshimo and other stuff """
from common import *
from pocket_shimodae.trainer import PoshimoTrainer
from ..ui import PoshimoView, Confirmation


class Welcome(PoshimoView):
  """ first message a new user sees """
  def __init__(self, cog):
    super().__init__(cog)
    self.embeds = [
      discord.Embed(
        title=f"Welcome to the world of Pocket Shimodae!",
        description="This is a brief description of the game. Let's go!"
      )
    ]


class StarterPoshimoConfirmation(Confirmation):
  """ confirmation for picking your starter poshimo """
  def __init__(self, cog, choice):
    super().__init__(cog, choice)
    self.embeds = [
      discord.Embed(
        title=f"You chose {choice.name}. Are you sure?",
        description="You can't undo this, but you can always find the other ones later!"
      )
    ]
    
  async def cancel_callback(self, button, interaction:discord.Interaction):
    await interaction.response.edit_message(content="Give it a good hard think and come back when you're ready! (Type `/ps start` to try again)", view=None, embed=None)
    self.stop()
    
  async def confirm_callback(self, button, interaction:discord.Interaction):
    # register player
    user = get_user(interaction.user.id)
    trainer = self.game.register_trainer(user["id"])
    view = StarterChosen(self.cog, self.choice, trainer)
    await interaction.response.edit_message(view=view, embeds=view.embeds)

class StarterPages(PoshimoView):
  """ The pages for choosing a starter poshimo """
  def __init__(self, cog):
    super().__init__(cog)
    self.starters = self.game.starter_poshimo
    self.welcome_embed = Welcome(self.cog).get_embed()
    
    for s in self.starters:
      """ list all the poshimo available as starters """
      embed = discord.Embed(
        title="Choose your starter Poshimo", 
        description=f"**{s.name}**", 
        fields=[
          discord.EmbedField(name="Types", value=f"{' and '.join([s.name for s in s.types])}"), 
          discord.EmbedField(name="Moves", value=f"{', '.join([m.display_name for m in s.move_list])}")]
      )
      self.pages.append(pages.Page(
        embeds=[self.welcome_embed, embed]
      ))
    
    self.paginator = pages.Paginator(
      pages=self.get_pages(),
      custom_view=self
    )

  @discord.ui.button(label="Choose this one", emoji="🟢", style=discord.ButtonStyle.blurple, row=2)
  async def button_callback(self, button, interaction:discord.Interaction):
    """ confirm their selection """
    pchoice = self.starters[self.paginator.current_page]
    view = StarterPoshimoConfirmation(self.cog, pchoice)
    
    await interaction.response.edit_message(view=view, embeds=view.embeds)

class StarterChosen(PoshimoView):
  """ when you have successfully chosen a starter """
  def __init__(self, cog, choice, trainer):
    self.choice = choice
    self.trainer = trainer
    super().__init__(cog)
    self.embeds = [
      discord.Embed(
        title=f"Congratulations TRAINER #{trainer.id}! You have selected your first poshimo: **{self.choice.name}**!", 
        description="Live long, and may the force prosper within you."
      )
    ]