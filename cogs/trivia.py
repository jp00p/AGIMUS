from trivia import trivia

from common import *
from handlers.xp import increment_user_xp
from utils.check_channel_access import access_check

f = open(config["commands"]["trivia"]["data"])
trivia_data = json.load(f)
f.close()

#    _____                                     __________        __    __                 
#   /  _  \   ____   ________  _  __ __________\______   \__ ___/  |__/  |_  ____   ____  
#  /  /_\  \ /    \ /  ___/\ \/ \/ // __ \_  __ \    |  _/  |  \   __\   __\/  _ \ /    \ 
# /    |    \   |  \\___ \  \     /\  ___/|  | \/    |   \  |  /|  |  |  | (  <_> )   |  \
# \____|__  /___|  /____  >  \/\_/  \___  >__|  |______  /____/ |__|  |__|  \____/|___|  /
#         \/     \/     \/              \/             \/                              \/ 
categories = trivia_data["categories"]
category_choices = []
for category in categories.keys():
  category_choice = discord.OptionChoice(
      name=category,
      value=category
    )
  category_choices.append(category_choice)

class AnswerButton(discord.ui.Button):
  def __init__(self, cog, answer_index):
    self.cog = cog
    self.answer_index = answer_index
    super().__init__(
      label=f"{answer_index+1}",
      style=discord.ButtonStyle.secondary,
      row=0
    )

  async def callback(self, interaction: discord.Interaction):
    await self.cog.answer_button_callback(interaction, self.answer_index)
    await interaction.response.send_message(f"You guessed: **{self.answer_index + 1}**", ephemeral=True)


# ___________      .__      .__        
# \__    ___/______|__|__  _|__|____   
#   |    |  \_  __ \  \  \/ /  \__  \  
#   |    |   |  | \/  |\   /|  |/ __ \_
#   |____|   |__|  |__| \_/ |__(____  /
#                                   \/ 
class Trivia(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

    self.trivia_data = {}
    self.trivia_answers = {}
    self.trivia_message = None
    self.trivia_running = False
    self.original_response = None
  
  def clear_data(self):
    self.trivia_data = {}
    self.trivia_answers = {}
    self.trivia_message = None
    self.trivia_running = False
    self.original_response = None

  async def answer_button_callback(self, interaction, answer_index):
    logger.info("answer_button_callback fired")
    trivia_answer = {
      'user': interaction.user,
      'guess': answer_index
    }
    self.trivia_answers[interaction.user.id] = trivia_answer

  @commands.slash_command(
    name="trivia",
    description="Start a round of Trivia!"
  )
  @option(
    name="category",
    description="Which Category?",
    required=False,
    choices=category_choices
  )
  @commands.check(access_check)
  async def trivia(self, interaction, category:str):
    if self.trivia_running:
      await interaction.respond("Trivia is in progress, please wait!", ephemeral=True)
    else:
      await self.trivia_quiz.start(interaction, category)

  @tasks.loop(seconds=20,count=1)
  async def trivia_quiz(self, ctx:discord.ApplicationContext, category:str):
    try:
      self.trivia_running = True

      if category:
        selected_category_number = categories[category]
        question = await trivia.question(amount=1, quizType='multiple', category=selected_category_number)
      else:
        question = await trivia.question(amount=1, quizType='multiple')
      self.trivia_data = question[0]

      answers = self.trivia_data["incorrect_answers"]
      answers.append(self.trivia_data["correct_answer"])
      random.shuffle(answers)

      correct_answer_index = answers.index(self.trivia_data["correct_answer"])
      self.trivia_data["correct_choice"] = correct_answer_index

      embed = discord.Embed(
        title="Trivia Alert!".format(self.trivia_data["difficulty"]),
        description=f"Category: *{self.trivia_data['category']}*\n\n> **{self.trivia_data['question']}**"
      )
      thumb = discord.File(f"./images/{self.trivia_data['difficulty']}.png")
      embed.set_thumbnail(url=f"attachment://{self.trivia_data['difficulty']}.png")

      view = discord.ui.View()
      for idx, answer in enumerate(answers):
        embed.add_field(
          name="** **",
          value=f"**{idx+1}**: {answer}",
          inline=False
        )
        button = AnswerButton(self, idx)
        view.add_item(button)

      embed.set_footer(text="Select a button below with your answer!")
      # channel = bot.get_channel(config["channels"]["quizzing-booth"])
      self.original_response = self.trivia_message = await ctx.respond(
        embed=embed,
        file=thumb,
        view=view
      )
    except Exception as e:
      await ctx.respond(embed=discord.Embed(
        title="Error Encountered with Trivia! Sorry, we're on it!",
        color=discord.Color.red(),
        ephemeral=True
      ))
      logger.info(f">>> ENCOUNTERED ERROR WITH /trivia: {e}")
      logger.info(traceback.format_exc())


  @trivia_quiz.after_loop
  async def end_trivia(self):
    try:
      logger.info(f"{Fore.LIGHTYELLOW_EX}Trivia complete!{Fore.RESET}")
      rewards = {
        "easy" : 5,
        "medium" : 10,
        "hard" : 15
      }
      reward = rewards[self.trivia_data["difficulty"]]
      correct_guessers = []
      for key in self.trivia_answers.keys():
        trivia_answer = self.trivia_answers[key]
        if trivia_answer['guess'] == self.trivia_data["correct_choice"]:
          correct_guessers.append(trivia_answer)

      channel = bot.get_channel(config["channels"]["quizzing-booth"])
      embed = discord.Embed(
        title="Trivia Complete!",
        description="\n\nThe correct answer was:\n\n**{}**: {} \n \n{}\n\n ".format(self.trivia_data['correct_choice'] + 1, self.trivia_data["correct_answer"], " "*47)
        )
      if len(correct_guessers) > 0:
        for trivia_answer in correct_guessers:
          player = trivia_answer['user']
          embed.add_field(
            name=f"\n{player.display_name}",
            value=f"`{reward} point(s)`",
            inline=False
          )
          set_player_score(player, reward)
          await increment_user_xp(player, 1, "trivia_win", channel)
          
      else:
        embed.add_field(name="\nNo winners!", value="Nobody got it this time.", inline=False)
        embed.set_footer(text=f"Adding {reward} point(s) to the jackpot")
        increase_jackpot(reward)

      # Disable all the answer buttons now that the trivia session is over
      await self.original_response.edit_original_message(view=None)

      self.clear_data()

      await channel.send(embed=embed)
    except Exception as e:
      logger.info(f">>> ENCOUNTERED ERROR WITH end_trivia: {e}")
      logger.info(traceback.format_exc())