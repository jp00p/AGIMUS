from common import *
from ..ui import *
from . import main_menu as mm
from pocket_shimodae.objects.world.crafting import get_all_crafting_levels, PoshimoRecipe

#TODO: what if there are more than 25 recipes for a level?  embedfields and optionselects will overflow

class CraftingMenu(PoshimoView):
  def __init__(self, cog, trainer, recipe_list:list=[], crafting:PoshimoRecipe=None, selected_level:int=None, selected_recipe:str=None, crafting_results:tuple=None):
    self.recipe_list = recipe_list
    self.crafting = crafting # the item we're attempting to craft
    self.selected_recipe = selected_recipe # the name of the recipe
    self.selected_level = selected_level
    self.crafting_results = crafting_results
    super().__init__(cog, trainer)
    
    # default embed
    self.embeds = [
      discord.Embed(
        title="Crafting station",
        description=fill_embed_text("Welcome to the crafting station. Choose an option from the menu below!")
      )
    ]

    # if they have chosen a recipe level
    if self.recipe_list:
      self.embeds = [
        discord.Embed(
          title="Choose a recipe to craft",
          description=fill_embed_text("Here are the recipes you have unlocked:"),
          fields=[
            discord.EmbedField(
              name=f"{recipe.name.title()}", 
              value=f"Number of different materials required: {len(recipe.list_mats())}", 
              inline=False
            ) for recipe in self.recipe_list
          ]
        )
      ]

    # if they have chosen a specific recipe
    if self.crafting:
      self.selected_recipe = self.crafting.name.lower()
      footer_text = "❌ You do not have all the materials to craft this yet."
      if self.trainer.has_recipe_mats(self.crafting):
        footer_text = "✅ You have all the required materials!"
      self.embeds = [
        discord.Embed(
          title=f"Selected recipe: {self.crafting.name.title()}",
          description=fill_embed_text(f"This will craft a: **{self.crafting.item.name.title()}**"),
          fields=[
            discord.EmbedField(
              name="Required materials",
              value="\n".join([f"{r[1]:0>2d} {'x':⠀<2} {r[0]}" for r in crafting.list_mats()]),
              inline=False
            ),
            discord.EmbedField(
              name="Difficulty",
              value=self.crafting.difficulty,
              inline=True
            ),
            discord.EmbedField(
              name="Est. XP",
              value=self.crafting.crafted_xp(self.trainer.crafting_level, only_base=True),
              inline=True
            ),
            
          ]
        ).set_footer(text=footer_text)
      ]

    # after they have attempted to craft
    if self.crafting_results is not None:
      
      crafting_success, crafting_xp = self.crafting_results
      footer = f"You gained {crafting_xp} crafting XP"

      if crafting_success:
        title = "Crafting success!"
        description = fill_embed_text(f"You created: **{self.crafting.item.name.title()}**") 
      else:
        title = "Crafting failed"
        description = "You tried your best, but it didn't come together."
        footer += " ...But your materials have been lost :("
      self.embeds = [
        discord.Embed(
          title=title,
          description=description
        ).set_footer(text=footer)
      ]
      
    # da buttons
    if len(self.trainer.recipes_unlocked) > 0 and self.crafting is None:
      self.add_item(RecipesByLevelDropdown(self.cog, self.trainer, selected_level=self.selected_level))
    if len(self.recipe_list) > 0:
      self.add_item(RecipesAvailableDropdown(self.cog, self.trainer, self.recipe_list, selected_recipe=self.selected_recipe, selected_level=self.selected_level))
    if self.crafting and self.crafting_results is None:
      self.add_item(CancelCrafting(self.cog, self.trainer, self.recipe_list, selected_level=self.selected_level))
      self.add_item(CraftButton(self.cog, self.trainer, self.recipe_list, self.crafting))
    self.add_item(mm.BackToMainMenu(self.cog, self.trainer))
   
   
class RecipesByLevelDropdown(discord.ui.Select):
  ''' show a list of recipe levels that are available to the trainer '''
  def __init__(self, cog, trainer:PoshimoTrainer, selected_level:int=None):
    self.cog = cog
    self.trainer = trainer
    self.selected_level = selected_level
    options = []
    levels = get_all_crafting_levels()
    
    for level in levels:
      if level <= self.trainer.crafting_level:
        options.append(discord.SelectOption(
          label=f"Level {level}",
          value=f"{level}",
          description=f"Craft items at level {level}",
          default=bool(self.selected_level == level)
        ))
    super().__init__(
      placeholder="Select a crafting level",
      options=options,
      row=0
    )
  async def callback(self, interaction: discord.Interaction):
    selected_level = int(self.values[0])
    recipe_list = list(filter(lambda x: x.level == selected_level, self.trainer.recipes_unlocked))
    view = CraftingMenu(self.cog, self.trainer, recipe_list=recipe_list, selected_level=selected_level)
    await interaction.response.edit_message(view=view, embeds=view.get_embeds())


class RecipesAvailableDropdown(discord.ui.Select):
  ''' show the recipes available to this trainer (for a given crafting level) '''
  def __init__(self, cog, trainer:PoshimoTrainer, recipe_list:list, selected_recipe:str=None, selected_level:int=None):
    self.cog = cog
    self.trainer = trainer
    self.recipe_list = recipe_list
    self.selected_recipe = selected_recipe
    self.selected_level = selected_level
    options = []
    for key,recipe in enumerate(self.recipe_list):
      options.append(
        discord.SelectOption(
          label=f"{recipe.name.title()}",
          value=f"{key}",
          description=f"Crafts: {recipe.item}\nDifficulty: {recipe.difficulty} - Estimated XP: {recipe.crafted_xp(self.trainer.crafting_level, only_base=True)}",
          default=bool(self.selected_recipe == recipe.name.lower())
        )
      )
    
    super().__init__(
      placeholder="Choose a recipe to craft",
      options=options,
      row=1
    )

  async def callback(self, interaction: discord.Interaction):
    recipe = self.recipe_list[int(self.values[0])]
    view = CraftingMenu(self.cog, self.trainer, recipe_list=self.recipe_list, crafting=recipe, selected_level=self.selected_level)
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
    crafting_results = self.trainer.craft_item(self.recipe)
    view = CraftingMenu(self.cog, self.trainer, crafting=self.recipe, crafting_results=crafting_results)
    await interaction.response.edit_message(view=view, embeds=view.get_embeds())

class CancelCrafting(discord.ui.Button):
  ''' cancel crafting '''
  def __init__(self, cog, trainer, recipe_list:list=[], selected_level:int=None, selected_recipe:str=None):
    self.cog = cog
    self.trainer = trainer
    self.recipe_list = recipe_list
    self.selected_level = selected_level
    self.selected_recipe = selected_recipe
    super().__init__(
      label="Cancel",
      emoji="🔙",
      style=discord.ButtonStyle.gray,
      row=3
    )
  async def callback(self, interaction: discord.Interaction):
    view = CraftingMenu(self.cog, self.trainer, recipe_list=self.recipe_list, selected_level=self.selected_level, selected_recipe=self.selected_recipe)
    await interaction.response.edit_message(view=view, embeds=view.get_embeds())