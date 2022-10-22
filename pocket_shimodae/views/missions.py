from select import select
from common import *
from ..ui import *
from ..objects import AwayMission, get_available_missions, MissionTypes, Poshimo
from . import main_menu as mm

class ManageAwayMissions(PoshimoView):
  ''' 
  main away mission screen
  shows the status of any current missions
  has buttons for managing missions
  '''
  def __init__(self, cog, trainer):
    super().__init__(cog, trainer)
    fields = []
    active_missions = self.trainer.list_missions_in_progress()

    if active_missions:
      description = fill_embed_text("Your active away missions") 
      for m in active_missions:
        fields.append(
          discord.EmbedField(
            name=f"{m.poshimo.display_name} {m.get_emoji()}",
            value=m.get_status()
          )
        )
      
    else:
      description = fill_embed_text("No active away missions!")

    self.embeds = [
      discord.Embed(
        title="Away missions",
        description=description,
        fields=fields
      )
    ]

    self.add_item(StartAwayMissionButton(self.cog, self.trainer))
    self.add_item(AwayMissionResultsButton(self.cog, self.trainer))
    self.add_item(RecallPoshimoButton(self.cog, self.trainer))
    self.add_item(RefreshMissionsButton(self.cog, self.trainer))
    self.add_item(mm.BackToMainMenu(self.cog, self.trainer))


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
  
  - first they choose a poshimo
  - then they choose a mission type
  - then they get the women
  - then they choose a mission
  
  this view gets updated along the way, hopefully i can keep it that way...
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
  ''' choose a poshimo to send away - edits the staging view '''
  def __init__(self, cog, trainer, **kwargs):
    super().__init__(
      cog, 
      trainer, 
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
  ''' choose the type of away mission - edits the staging view '''
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
    self.view.item_slots["mission_select"] = AvailableMissionsSelect(self.cog, self.trainer, missions, self.poshimo)
    self.view.remove_item(self.view.item_slots["mission_type"])
    self.view.add_item(self.view.item_slots["mission_select"])
    await interaction.response.edit_message(view=self.view, embed=self.view.get_embed())


class RefreshMissionsButton(discord.ui.Button):
  ''' refresh the list of missions '''
  def __init__(self, cog, trainer):
    self.cog = cog
    self.trainer = trainer
    super().__init__(
      label="Refresh",
      emoji="🔃",
      row=2
    )
  async def callback(self, interaction: discord.Interaction):
    view = ManageAwayMissions(self.cog, self.trainer)
    await interaction.response.edit_message(view=view, embed=view.get_embed())


class AvailableMissionsSelect(discord.ui.Select):
  ''' selectmenu of the available missions - launches the staging view '''
  def __init__(self, cog, trainer, mission_list, poshimo):
    self.cog = cog
    self.trainer = trainer
    self.mission_list = mission_list
    self.poshimo = poshimo
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
    selected_mission:AwayMission = self.mission_list[int(self.values[0])]
    mission_id = selected_mission.begin(self.poshimo)
    self.poshimo.mission_id = mission_id
    self.trainer.send_poshimo_away(self.poshimo)
    view = ManageAwayMissions(self.cog, self.trainer)
    view.embeds[0].description = f"**{self.poshimo} sent on mission {mission_id}!**\n" + view.embeds[0].description
    await interaction.response.edit_message(view=view, embed=view.get_embed())


class AwayMissionResultsButton(discord.ui.Button):
  ''' button to check results for completed missions '''
  def __init__(self, cog, trainer):
    self.cog = cog
    self.trainer:PoshimoTrainer = trainer
    self.missions = self.trainer.list_missions_ready_to_resolve()
    super().__init__(
      label="Check results",
      emoji="✅",
      row=1,
      disabled=bool(len(self.missions) <= 0)
    )
  async def callback(self, interaction:discord.Interaction):
    view = AwayMissionsResults(self.cog, self.trainer, self.view)
    await interaction.response.edit_message(view=view, embed=view.get_embed())


class CompletedMissionSelect(discord.ui.Select):
  ''' choose a mission to resolve '''
  def __init__(self, cog, trainer):
    self.cog = cog
    self.trainer:PoshimoTrainer = trainer
    self.completed_missions = self.trainer.list_missions_ready_to_resolve()
    if self.completed_missions:
      disabled = False
      placeholder = "Which mission are you ready to resolve?"
      options = [
        discord.SelectOption(
          label=f"{m.poshimo.display_name}: {m.name}",
          value=f"{key}"
        ) for key,m in enumerate(self.completed_missions)
      ]
    else:
      placeholder = "No missions left to resolve."
      options = [discord.SelectOption(label="No poshimo", value="0")]
      disabled = True
    super().__init__(
      placeholder=placeholder,
      options=options,
      disabled=disabled
    )
  async def callback(self, interaction:discord.Interaction):
    selected_mission = self.completed_missions[int(self.values[0])]
    rewards = selected_mission.resolve()
    self.trainer.return_poshimo_from_mission(selected_mission.poshimo)
    view = AwayMissionsResults(self.cog, self.trainer)
    view.embeds = [
      discord.Embed(
        title="Mission complete!",
        description=f"{selected_mission.name} has been completed by {selected_mission.poshimo.display_name}!",
        fields=[
          discord.EmbedField(
            name=f"{r}",
            value=f"{v}",
            inline=True
          ) for r,v in rewards
        ]
      )
    ]
    await interaction.response.edit_message(view=view, embed=view.get_embed())
    


class AwayMissionsResults(PoshimoView):
  ''' list of away missions ready to review '''
  def __init__(self, cog, trainer, prev_view=None):
    super().__init__(cog, trainer)
    self.missions = self.trainer.list_missions_ready_to_resolve()
    desc = "Here are the missions you have ready to resolve:\n"
    if len(self.missions) <= 0:
      desc = "No more missions left to resolve!\n"
      self.embeds = [
        discord.Embed(
          title="No missions ready!",
          description=desc
        )
      ]
    else:
      self.embeds = [
        discord.Embed(
          title="Missions ready:",
          description=desc,
          fields=[
            discord.EmbedField(
              name=f"{m.poshimo.display_name} {m.get_emoji()}",
              value=m.get_status()
            ) for m in self.missions if self.missions
          ]
        )
      ]
    self.add_item(CompletedMissionSelect(self.cog, self.trainer))
    self.add_item(BackButton(ManageAwayMissions(self.cog, self.trainer), label="All missions"))   
    self.add_item(mm.BackToMainMenu(self.cog, self.trainer))
    #self.add_item(BackButton(self.previous_view, label="Cancel"))


class RecallPoshimoButton(discord.ui.Button):
  ''' end a mission early '''
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


