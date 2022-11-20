from common import *
from ..ui import *
from . import main_menu as mm
from pocket_shimodae.objects.world.crafting import get_all_crafting_levels, PoshimoRecipe

class CraftingMenu(PoshimoView):
  def __init__(self, cog, trainer, recipe_list:list=[], crafting:PoshimoRecipe=None):
    self.recipe_list = recipe_list
    self.crafting = crafting
    super().__init__(cog, trainer)
    
    self.embeds = [
      discord.Embed(
        title="Crafting station",
        description=fill_embed_text("Welcome to the crafting station. Choose an option from the menu below!")
      )
    ]
    if self.recipe_list:
      self.embeds = [
        discord.Embed(
          title="Choose a recipe to craft",
          description="Here are the recipes you have unlocked:",
          fields=[
            discord.EmbedField(
              name=f"{recipe.name.title()}", 
              value="\n".join([f"{r[0]} x{r[1]}" for r in recipe.list_mats()]), 
              inline=True
            ) for recipe in self.recipe_list
          ]
        )
      ]

    if self.crafting:
      self.embeds = [
        discord.Embed(
          title=f"Recipe: {self.crafting.name.title()}",
          description="Materials required:\n"+"\n".join([f"{r[0]} x{r[1]}" for r in crafting.list_mats()])
        )
      ]

    if len(self.trainer.recipes_unlocked) > 0:
      self.add_item(RecipesByLevelDropdown(self.cog, self.trainer))
    if len(self.recipe_list) > 0:
      self.add_item(RecipesAvailableDropdown(self.cog, self.trainer, self.recipe_list))
    if self.crafting:
      self.add_item(CraftButton(self.cog, self.trainer, self.recipe_list, self.crafting))
      self.add_item(CancelCrafting(self.cog, self.trainer, self.recipe_list))
    self.add_item(mm.BackToMainMenu(self.cog, self.trainer))
   
# dropdown that shows available crafting levels:
# - shows dropdown for available recipes in that level
# - cancel button
# - callback:
#   - attempt to craft
#   - show results 
# back to menu button

class RecipesByLevelDropdown(discord.ui.Select):
  ''' show a list of recipe levels that are available to the trainer '''
  def __init__(self, cog, trainer:PoshimoTrainer):
    self.cog = cog
    self.trainer = trainer
    options = []
    levels = get_all_crafting_levels()
    
    for level in levels:
      if level <= self.trainer.crafting_level:
        options.append(discord.SelectOption(
          label=f"Level {level}",
          value=f"{level}",
          description=f"Craft items at level {level}"
        ))
    super().__init__(
      placeholder="Select a crafting level",
      options=options,
      row=0
    )
  async def callback(self, interaction: discord.Interaction):
    selected_level = int(self.values[0])
    recipe_list = list(filter(lambda x: x.level == selected_level, self.trainer.recipes_unlocked))
    view = CraftingMenu(self.cog, self.trainer, recipe_list=recipe_list)
    await interaction.response.edit_message(view=view, embeds=view.get_embeds())


class RecipesAvailableDropdown(discord.ui.Select):
  ''' show the recipes available to this trainer (for a given crafting level) '''
  def __init__(self, cog, trainer:PoshimoTrainer, recipe_list:list):
    self.cog = cog
    self.trainer = trainer
    self.recipe_list = recipe_list
    options = []
    for key,recipe in enumerate(self.recipe_list):
      if recipe.level == self.trainer.crafting_level:
        options.append(
          discord.SelectOption(
            label=f"{recipe.name.title()}",
            value=f"{key}",
            description=f"Crafts: {recipe.item} - difficulty: {recipe.difficulty} - XP: {recipe.crafted_xp()}"
          )
        )
    super().__init__(
      placeholder="Choose a recipe to craft",
      options=options,
      row=1
    )
  async def callback(self, interaction: discord.Interaction):
    recipe = self.recipe_list[int(self.values[0])]
    view = CraftingMenu(self.cog, self.trainer, recipe_list=self.recipe_list, crafting=recipe)
    await interaction.response.edit_message(view=view, embeds=view.get_embeds())


class CraftButton(discord.ui.Button):
  ''' execute the crafting '''
  def __init__(self, cog, trainer:PoshimoTrainer, recipe_list:list, recipe:PoshimoRecipe):
    # disabled if they don't have the mats
    self.cog = cog
    self.recipe = recipe
    self.trainer = trainer
    self.recipe_list = recipe_list
    disabled = True
    if self.trainer.has_recipe_mats(self.recipe):
      disabled = False
    
    super().__init__(
      label="Craft!",
      emoji="🔨",
      disabled=disabled,
      style=discord.ButtonStyle.green,
      row=3
    )
  async def callback(self, interaction: discord.Interaction):
    pass

class CancelCrafting(discord.ui.Button):
  ''' cancel crafting '''
  def __init__(self, cog, trainer, recipe_list):
    self.cog = cog
    self.trainer = trainer
    self.recipe_list = recipe_list
    super().__init__(
      label="Cancel",
      emoji="🔙",
      style=discord.ButtonStyle.gray,
      row=3
    )
  async def callback(self, interaction: discord.Interaction):
    view = CraftingMenu(self.cog, self.trainer, recipe_list=self.recipe_list)
    await interaction.response.edit_message(view=view, embeds=view.get_embeds())