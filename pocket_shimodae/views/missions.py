from select import select
from common import *
from ..ui import *
from ..objects import AwayMission, get_available_missions, MissionTypes, Poshimo

class ManageAwayMissions(PoshimoView):
  ''' 
  main away mission screen
  shows the status of any current missions
  has buttons for managing missions
  '''
  def __init__(self, cog, trainer):
    super().__init__(cog, trainer)

    self.embeds = [
      discord.Embed(
        title="Away missions",
        description="Manage your away missions [TODO: List poshimo on away missions]"
      )
    ]
    self.add_item(StartAwayMissionButton(self.cog, self.trainer))
    self.add_item(AwayMissionResultsButton(self.cog, self.trainer))
    self.add_item(RecallPoshimoButton(self.cog, self.trainer))


class StartAwayMissionButton(discord.ui.Button):
  def __init__(self, cog, trainer):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      label="Send",
      emoji="👋",
      row=1
    )
  async def callback(self, interaction:discord.Interaction):
    view = PrepareAwayMission(self.cog, self.trainer, previous_view=self.view)
    await interaction.response.edit_message(view=view, embed=view.get_embed())

class PrepareAwayMission(PoshimoView):
  ''' 
  the staging view for sending a poshimo on an away message
  first they choose a poshimo
  then they choose a mission type
  then they get the women
  then they choose a mission
  '''
  def __init__(self, cog, trainer, previous_view):
    super().__init__(cog, trainer, previous_view)
    
    self.embeds = [
      discord.Embed(
        title="Send a Poshimo on an away mission!",
        description="Which Poshimo you wanna send?"
      )
    ]
    self.item_slots = {
      "select_poshimo" : SelectPoshimoToSend(self.cog, self.trainer),
      "mission_type": None,
      "mission_select": None
    }
    self.add_item(self.item_slots["select_poshimo"])
    self.add_item(BackButton(self.previous_view, label="Cancel"))


class SelectPoshimoToSend(PoshimoSelect):
  def __init__(self, cog, trainer, **kwargs):
    super().__init__(
      cog, 
      trainer, 
      only_here=True, 
      only_alive=True, 
      custom_placeholder="Choose a Poshimo to send", 
      custom_id="MISSION_POSHIMO_SELECT",
      **kwargs
    )
  async def callback(self:PoshimoSelect, interaction:discord.Interaction):
    self.get_selected_poshimo()
    self.view.item_slots["mission_type"] = ChooseMissionTypeSelect(self.cog, self.trainer, self.selected_poshimo)
    self.view.add_item(self.view.item_slots["mission_type"])
    self.view.embeds[0].description = "Next, choose a mission type."
    self.view.remove_item(self.view.item_slots["select_poshimo"])
    await interaction.response.edit_message(view=self.view, embed=self.view.get_embed())


class ChooseMissionTypeSelect(discord.ui.Select):
  ''' choose the type of away mission '''
  def __init__(self, cog, trainer, selected_poshimo, **kwargs):
    self.cog = cog
    self.trainer:PoshimoTrainer = trainer
    self.poshimo:Poshimo = selected_poshimo
    placeholder = "Choose a mission type"
    options = [
      discord.SelectOption(
        label="Gathering",
        value="GATHERING"
      ),
      discord.SelectOption(
        label="Training",
        value="TRAINING"
      ),
    ]
    super().__init__(
      placeholder=placeholder,
      options=options,
      custom_id="MISSION_TYPE_SELECT",
      **kwargs
    )
  async def callback(self, interaction: discord.Interaction):
    ''' 
    once chosen: 

    - edit the embed with the list of missions
    - remove the mission type selector
    - add the final mission select menu
    '''
    mission_type = MissionTypes[self.values[0]]
    missions = get_available_missions(mission_type, self.poshimo.level)
    self.view.embeds[0].title = f"Select an away mission"
    self.view.embeds[0].description = f"Which mission do you want to send {self.poshimo.display_name} on?"
    self.view.embeds[0].fields = [
      discord.EmbedField(
        name=m.name.title(),
        value=m.description,
        inline=False
      ) for m in missions
    ]
    self.view.item_slots["mission_select"] = AvailableMissionsSelect(self.cog, self.trainer, missions)
    self.view.remove_item(self.view.item_slots["mission_type"])
    self.view.add_item(self.view.item_slots["mission_select"])
    await interaction.response.edit_message(view=self.view, embed=self.view.get_embed())


class AvailableMissionsSelect(discord.ui.Select):
  ''' selectmenu of the available missions '''
  def __init__(self, cog, trainer, mission_list):
    self.cog = cog
    self.trainer = trainer
    self.mission_list = mission_list
    options = [
      discord.SelectOption(
        label=m.name,
        value=str(key)
      ) for key,m in enumerate(self.mission_list)
    ]
    super().__init__(
      placeholder="Which mission?",
      options=options
    )
  async def callback(self, interaction:discord.Interaction):
    await interaction.response.send_message(self.values[0])


class AwayMissionResultsButton(discord.ui.Button):
  def __init__(self, cog, trainer):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      label="Check results",
      emoji="✅",
      row=1
    )
  async def callback(self, interaction:discord.Interaction):
    pass


class RecallPoshimoButton(discord.ui.Button):
  def __init__(self, cog, trainer):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      label="Recall",
      emoji="❌",
      row=1
    )
  async def callback(self, interaction:discord.Interaction):
    pass


class AwayMissionListing(PoshimoView):
  def __init__(self, cog, trainer):
    super().__init__(cog, trainer)
