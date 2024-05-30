import math
from re import S

from common import *
from handlers.xp import increment_user_xp
from utils.show_utils import get_show_embed
from utils.check_channel_access import access_check

command_config = config["commands"]["quiz start"]

# Load JSON Data
f = open(command_config["data"])
info_data = json.load(f)
f.close()

show_choices = []
show_keys = sorted(list(info_data.keys()), key=lambda k: info_data[k]['name'])
for show_key in show_keys:
  show_data = info_data[show_key]
  if show_data["enabled"]:
    show_choice = discord.OptionChoice(
      name=show_data["name"],
      value=show_key
    )
    show_choices.append(show_choice)

class HintButton(discord.ui.Button):
  def __init__(self, cog):
    self.cog = cog
    super().__init__(
      label="             Hint             ",
      style=discord.ButtonStyle.primary,
      row=0
    )

  async def callback(self, interaction: discord.Interaction):
    episode_description = self.cog.quiz_episode["description"]
    embed = discord.Embed(
      title="Episode Summary",
      description=episode_description,
      color=discord.Color.blurple()
    )
    embed.set_footer(text="Note that now that you've used a hint, if you get it correct the reward is reduced!")
    await interaction.response.send_message(embed=embed, ephemeral=True)
    self.cog.register_hint(interaction)

class Quiz(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

    self.quiz_running = False
    self.quiz_response = None
    self.quiz_channel = None
    self.log = []
    self.previous_episodes = {}

    self.quiz_episode = None
    self.quiz_index = -1
    self.correct_answers = {}
    self.fuzz = {}
    self.hint_users = []

    self.threshold = 72  # fuzz threshold

    self.shows = command_config["parameters"][0]["allowed"]

  quiz = discord.SlashCommandGroup("quiz", "Commands for interacting with the Quiz Game")

  @quiz.command(
    name="start",
    description="Start a Quiz round"
  )
  @option(
    name="show",
    description="Which Show?",
    required=False,
    choices=show_choices
  )
  @commands.check(access_check)
  async def start(self, ctx: discord.ApplicationContext, show:str):
    if self.quiz_running:
      await ctx.respond("There's already a round of Quiz happening! Play along with `/quiz answer`", ephemeral=True)
      return
    else:
      self.log = []
      self.quiz_channel = ctx.channel
      await self.quiz_start.start(ctx, show)


  @quiz.command(
    name="answer",
    description="Submit your Quiz answer"
  )
  @option(
    name="answer",
    description="Your answer:",
    required=True
  )
  @commands.check(access_check)
  async def answer(self, ctx: discord.ApplicationContext, answer:str):
    if not self.quiz_running:
      await ctx.respond("There's no current Quiz, try starting one with `/quiz start`!", ephemeral=True)
      return
    else:
      correct_answer = self.quiz_episode["title"].lower().strip()
      guess = answer.lower().strip()

      # remove all punctuation
      correct_answer = "".join(l for l in correct_answer if l not in string.punctuation).split()
      guess = "".join(l for l in guess if l not in string.punctuation).split()
      # remove common words
      stopwords = ["the", "a", "of", "is", "teh", "th", "eht", "eth", "of", "for", "part 1", "part 2", "part 3", "part i", "part ii", "part iii", "(1)", "(2)", "(3)", "in", "are", "an", "as", "and"]
      resultwords  = [word for word in correct_answer if word.lower() not in stopwords]
      guesswords = [word for word in guess if word.lower() not in stopwords]
      # rejoin the strings
      correct_answer = ' '.join(resultwords)
      guess = ' '.join(guesswords)
      # check ratios
      ratio = fuzz.ratio(correct_answer, guess)
      pratio = fuzz.partial_ratio(correct_answer, guess)
      # arbitrary single-number score
      normalness = round((ratio + pratio) / 2)

      # add message to the log for reporting
      if (ratio != 0) and (pratio != 0):
        self.log.append([ctx.author.display_name, guess, ratio, pratio])

      await ctx.respond("Answer registered! 👍", ephemeral=True)

      # check answer
      if (ratio >= self.threshold and pratio >= self.threshold) or (guess == correct_answer):
        # correct answer
        award = 1
        bonus = False
        if (ratio < 80 and pratio < 80):
          # bonus
          bonus = True
          award = 2
        id = ctx.author.id
        if id not in self.correct_answers:
          if not self.correct_answers:
            award *= 10
          else:
            award *= 5

          # Cut award in half if they used a hint
          used_hint = False
          if ctx.author.id in self.hint_users:
            used_hint = True
            award = math.ceil(award / 2)

          await set_player_score(ctx.author, award)
          await increment_user_xp(ctx.author, 1, "quiz_win", ctx.channel, "Winning a round of Quiz")

          if id not in self.fuzz:
            score_str = "`Correctitude: " + str(normalness) +"`"
            if not bonus:
              score_str += f" {get_emoji('combadge')}"
            else:
              score_str += f" {get_emoji('combadge_spin')}"
            self.fuzz[id] = score_str
          self.correct_answers[id] = { "user": ctx.author, "points": award, "score_str": score_str, "used_hint": used_hint }
      else:
        if (ratio >= self.threshold-6 and pratio >= self.threshold-6):
          await ctx.reply(f"{get_emoji('q_shocking')}", ephemeral=True)


  @quiz.command(
    name="report",
    description="See a report on the fuzziness of the last Quiz round"
  )
  @commands.check(access_check)
  async def report(self, ctx:discord.ApplicationContext):
    if len(self.log) != 0:
      embed = discord.Embed(
        title="Quiz Report",
        description="What was the fuzziness of the previous round's answers?",
        color=discord.Color.blurple()
      )
      for l in self.log:
        embed.add_field(
          name=f"{l[0]}",
          value=f"({l[1]} - {l[2]}:{l[3]})",
          inline=False
        )
      await ctx.respond(embed=embed)
    else:
      await ctx.respond("No log entries currently", ephemeral=True)


  @tasks.loop(seconds=35,count=1)
  async def quiz_start(self, ctx:discord.ApplicationContext, show:str):
    try:
      logger.info(f"{Fore.MAGENTA}Starting quiz!{Fore.RESET}")
      if not show:
        s = random.choice(self.shows)
        show = s["value"]

      self.show = show

      f = open(f"./data/episodes/{show}.json")
      self.show_data = json.load(f)
      f.close()

      # don't pick one of the same episodes we've played previously
      if show not in self.previous_episodes.keys():
        self.previous_episodes[show] = []

      # Reset previous episodes if we've run through _all_ of the show's episodes already
      if len(self.previous_episodes[show]) == len(self.show_data["episodes"]):
        self.previous_episodes[show] = []

      episode_index = random.randrange(len(self.show_data["episodes"]))
      while episode_index in self.previous_episodes[show]:
        episode_index = random.randrange(len(self.show_data["episodes"]))
      self.previous_episodes[show].append(episode_index)

      self.quiz_index = episode_index
      self.quiz_episode = self.show_data["episodes"][episode_index]
      # self.quiz_show = show

      image_url = random.choice(self.quiz_episode["stills"])
      r = requests.get(image_url, headers={'user-agent': 'Mozilla/5.0'})
      with open('./images/ep.jpg', 'wb') as f:
        f.write(r.content)

      file = discord.File("./images/ep.jpg", filename="image.jpg")
      embed = discord.Embed(
        title=f"Which episode of **{self.show_data['title']}** is this? {get_emoji('horgahn_dance')}",
        description=f"Use `/quiz answer` to submit your guess!",
        color=discord.Color.blurple()
      )
      embed.set_footer(text="Press the button below for a hint, but doing so will reduce your reward!")
      embed.set_image(url="attachment://image.jpg")
      view = discord.ui.View()
      view.add_item(HintButton(self))
      self.quiz_response = await ctx.respond(file=file, embed=embed, view=view)

      self.quiz_running = True
    except Exception as e:
      logger.info(traceback.format_exc())


  @quiz_start.after_loop
  async def quiz_finished(self):
    try:
      title = f"The episode title was: **{self.quiz_episode['title']}** (Season {self.quiz_episode['season']} Episode {self.quiz_episode['episode']})"
      embed = None
      if len(self.correct_answers) == 0:
        roll = random.randint(5,10)
        #todo: add random lose msgs
        embed = discord.Embed(
          title=title,
          description=f"Did you win? Hardly! Adding `{roll} point(s)` to the jackpot.",
          color=discord.Color.red()
        )
        await increase_jackpot(roll)
      else:
        #todo: add random win msgs
        embed = discord.Embed(
          title=title,
          description="Chula! These crewmembers got it:",
          color=discord.Color.green()
        )
        for key in self.correct_answers.keys():
          answer = self.correct_answers[key]
          user = answer["user"]
          msg = f"{answer['points']} Points! ({answer['score_str']})"
          if answer["used_hint"]:
            msg += " (Used a hint!)"
          embed.add_field(
            name=f"{user.display_name}",
            value=msg
          )

      show_embed = get_show_embed(self.show_data, self.quiz_index, self.show)
      await self.quiz_channel.send(embed=embed)
      await self.quiz_channel.send(embed=show_embed)

      # Remove the hint button now that the round is done
      original_response = await self.quiz_response.original_response()
      if original_response != None:
        await original_response.edit(view=None)

      self.reset_quiz()
    except Exception as e:
      logger.info(traceback.format_exc())

  def reset_quiz(self):
    # Cancel Loop
    self.quiz_start.cancel()

    # Reset round-specific data
    self.quiz_running = False
    self.quiz_channel = None

    self.quiz_episode = None
    self.quiz_index = -1
    self.correct_answers = {}
    self.hint_users = []
    self.fuzz = {}

  def register_hint(self, interaction):
    user_id = interaction.user.id
    if user_id not in self.hint_users:
      self.hint_users.append(user_id)
