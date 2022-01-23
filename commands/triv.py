from trivia import trivia
from .common import *
from .jackpot import get_jackpot
from .poker import *

@tasks.loop(seconds=20,count=1)
async def trivia_quiz(category=None):
  global TRIVIA_DATA, TRIVIA_RUNNING, TRIVIA_MESSAGE
  if category:
    question = await trivia.question(amount=1, quizType='multiple', category=category)
  else:
    question = await trivia.question(amount=1, quizType='multiple')
  TRIVIA_DATA = question[0]
  logger.info("Using category " + str(category))
  logger.info("correct answer: " + TRIVIA_DATA["correct_answer"])
  answers = TRIVIA_DATA["incorrect_answers"]
  answers.append(TRIVIA_DATA["correct_answer"])
  random.shuffle(answers)
  correct_answer_index = answers.index(TRIVIA_DATA["correct_answer"])
  embed = discord.Embed(title="Trivia Alert!".format(TRIVIA_DATA["difficulty"]), description="Category: *{}* \n⠀\n> **{}**\n⠀".format(TRIVIA_DATA["category"],TRIVIA_DATA["question"]))
  thumb = discord.File("./images/{}.png".format(TRIVIA_DATA["difficulty"]))
  embed.set_thumbnail(url="attachment://{}.png".format(TRIVIA_DATA["difficulty"]))
  i = 0
  reactions = ["1️⃣","2️⃣","3️⃣","4️⃣"]
  TRIVIA_DATA["correct_emoji"] = reactions[correct_answer_index]
  for ans in answers:
    maybe_newline = ""
    if i == 3:
      maybe_newline = "\n ** ** \n"
    embed.add_field(name="** **", value="{}: {} {}".format(reactions[i],ans,maybe_newline), inline=False)
    i += 1
  embed.set_footer(text="React below with your answer!")
  channel = client.get_channel(config["commands"]["triv"]["channels"][0])
  TRIVIA_MESSAGE = await channel.send(embed=embed, file=thumb)
  for react in reactions:
    await TRIVIA_MESSAGE.add_reaction(react)
  
@trivia_quiz.after_loop
async def end_trivia():
  global TRIVIA_ANSWERS, TRIVIA_DATA, TRIVIA_RUNNING, TRIVIA_MESSAGE
  logger.info("Trivia complete!")
  rewards = {
    "easy" : 5,
    "medium" : 10,
    "hard" : 15
  }
  reward = rewards[TRIVIA_DATA["difficulty"]]
  correct_guessers = []
  for ans in TRIVIA_ANSWERS:
    if TRIVIA_ANSWERS[ans] == TRIVIA_DATA["correct_emoji"]:
      correct_guessers.append(get_player(ans))
  channel = client.get_channel(config["commands"]["triv"]["channels"][0])
  embed = discord.Embed(title="Trivia Complete!", description="⠀\n⠀\nThe correct answer was:\n {} **{}**\n⠀\n⠀{}".format(TRIVIA_DATA["correct_emoji"], TRIVIA_DATA["correct_answer"], " "*47))
  if len(correct_guessers) > 0:
    for player in correct_guessers:
      embed.add_field(name=player["name"], value="`{} point(s)`".format(reward), inline=False)
      set_player_score(player["discord_id"], reward)
  else:
    embed.add_field(name="No winners!", value="Nobody got it this time.", inline=False)
    embed.set_footer(text="Adding {} point(s) to the jackpot".format(reward))
    increase_jackpot(reward)
  TRIVIA_DATA = {}
  TRIVIA_ANSWERS = {}
  TRIVIA_RUNNING = False
  TRIVIA_MESSAGE = None
  await channel.send(embed=embed)


@client.event
async def on_raw_reaction_add(payload:discord.RawReactionActionEvent):
  global TRIVIA_ANSWERS, POKER_GAMES
  if payload.user_id != client.user.id:
    # poker reacts
    if payload.message_id in POKER_GAMES:
      if payload.user_id == POKER_GAMES[payload.message_id]["user"]:
        if payload.emoji.name == "✅":
          await resolve_poker(payload.message_id)
      else:
        user = await client.fetch_user(payload.user_id)
        await POKER_GAMES[payload.message_id]["message"].remove_reaction(payload.emoji,user)
    # trivia reacts
    if TRIVIA_MESSAGE and payload.message_id == TRIVIA_MESSAGE.id:
      #emoji = await discord.utils.get(TRIVIA_MESSAGE.reactions, emoji=payload.emoji.name)
      user = await client.fetch_user(payload.user_id)
      await TRIVIA_MESSAGE.remove_reaction(payload.emoji, user)
      TRIVIA_ANSWERS[payload.user_id] = payload.emoji.name


# triv() - Entrypoint for !triv command
# message[required]: discord.Message
# This function is the main entrypoint of the !triv command
# and will display the possible trivia trivia
async def triv(message:discord.Message):
  f = open(config["commands"]["categories"]["data"])
  trivia_data = json.load(f)
  f.close()
  if TRIVIA_RUNNING:
    await message.channel.send("Trivia is in progress, please wait!")
  else:
    trivia_category = message.content.lower().replace("!triv ", "").strip()
    if trivia_category.isnumeric() and int(trivia_category) > 0 and int(trivia_category) < len(trivia_data["categories"]):
      
      trivia_cat_id = int(trivia_category)
      logger.info("Starting category trivia quiz ", trivia_cat_id)
      await trivia_quiz.start(category=trivia_cat_id)
    else:
      await trivia_quiz.start()


