from .common import *
from .info import get_show

emojis = config["emojis"]

QUIZ_EPISODE = False
QUIZ_INDEX = -1
LAST_SHOW = False
PREVIOUS_EPS = {}
CORRECT_ANSWERS = {}
FUZZ = {}


# quiz() - Entrypoint for !quiz command
# message[required]: discord.Message
# This function is the main entrypoint of the !quiz command
# and will start a quiz to see who can name an episode title based on a still images from the episode
async def quiz(message:discord.Message):
  global LOG
  if not QUIZ_EPISODE:
    await message.channel.send("Getting episode image, please stand by...")
    episode_quiz.start(message)
  else:
    threshold = 72  # fuzz threshold
    # lowercase and remove trailing spaces
    correct_answer = QUIZ_EPISODE["title"].lower().strip()
    guess = message.content.lower().replace("!quiz ", "").strip()
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
    #logger.info("ratio: " + str(ratio))
    #logger.info("pratio: " + str(pratio))
    # add message to the log for reporting
    if (ratio != 0) and (pratio != 0):
      LOG.append([guess, ratio, pratio])
    #logger.info("LOG: " + str(LOG))
    await message.add_reaction('\N{THUMBS UP SIGN}')
    # check answer
    if (ratio >= threshold and pratio >= threshold) or (guess == correct_answer):
      # correct answer      
      award = 1
      bonus = False
      if (ratio < 80 and pratio < 80):
        # bonus
        bonus = True
        award = 2
      id = message.author.id
      if id not in CORRECT_ANSWERS:
        if not CORRECT_ANSWERS:
          award *= 10
        else:
          award *= 5
        set_player_score(message.author, award)
        if id not in FUZZ:
          score_str = "`Correctitude: " + str(normalness) +"`"
          if not bonus:
            score_str += f" {emojis['combadge']}"
          else:
            score_str += f" {emojis['combadge_spin']}"
          FUZZ[id] = score_str
        CORRECT_ANSWERS[id] = { "name": message.author.mention, "points":award }
    else:
      if (ratio >= threshold-6 and pratio >= threshold-6):
        await message.add_reaction(EMOJI["shocking"])

@tasks.loop(seconds=31,count=1)
async def episode_quiz(message):
  global QUIZ_EPISODE, QUIZ_INDEX, TMDB_IMG_PATH, LAST_SHOW, QUIZ_SHOW, PREVIOUS_EPS, LOG
  quiz_channel = bot.get_channel(config["channels"]["quizzing-booth"])
  quiz_spl = message.content.lower().replace("!quiz ", "").split()
  # User selects tos|tng|ds9|voy|enterprise|disco etc
  logger.info(f"{Fore.LIGHTBLUE_EX}Selected Show:{Fore.RESET} {Style.BRIGHT}{quiz_spl[0]}{Style.RESET_ALL}")
  if quiz_spl[0] in config["commands"]["quiz"]["parameters"][0]["allowed"]:
    selected_show = quiz_spl[0]
  else:
    selected_show = random.choice(config["commands"]["quiz"]["parameters"][0]["allowed"])


  f = open("./data/episodes/" + selected_show + ".json")
  show_data = json.load(f)
  f.close()
  # don't pick the same episode as last time
  episode = random.randrange(len(show_data["episodes"]))
  if selected_show in PREVIOUS_EPS.keys():
    while episode == PREVIOUS_EPS[selected_show]:
      episode = random.randrange(len(show_data["episodes"]))
  PREVIOUS_EPS[selected_show] = episode
  QUIZ_INDEX = episode
  QUIZ_EPISODE = show_data["episodes"][episode]
  QUIZ_SHOW = selected_show # current show
  #logger.info("Correct answer: " + QUIZ_EPISODE["title"])
  #logger.debug(f"{QUIZ_EPISODE}")
  image = random.choice(QUIZ_EPISODE["stills"])
  r = requests.get(TMDB_IMG_PATH + image, headers={'user-agent': 'Mozilla/5.0'})
  with open('./images/ep.jpg', 'wb') as f:
    f.write(r.content)
  LOG = [] # reset the log
  await quiz_channel.send(file=discord.File("./images/ep.jpg"))
  await quiz_channel.send(f"Which episode of **__{show_data['title']}__** is this? {emojis['horgahn_dance']}\nTo answer type: `!quiz [your guess]`")


@episode_quiz.after_loop
async def quiz_finished():
  global QUIZ_EPISODE, QUIZ_INDEX, CORRECT_ANSWERS, FUZZ, QUIZ_SHOW, PREVIOUS_EPS
  #await asyncio.sleep(1)
  logger.info(f"{Fore.MAGENTA}Ending quiz!{Fore.RESET}")

  f = open("./data/episodes/" + QUIZ_SHOW + ".json")
  show_data = json.load(f)
  f.close()
  quiz_channel = bot.get_channel(config["channels"]["quizzing-booth"])
  msg = "The episode title was: **{0}** (Season {1} Episode {2})\n".format(QUIZ_EPISODE["title"].strip(), QUIZ_EPISODE["season"], QUIZ_EPISODE["episode"])
  if len(CORRECT_ANSWERS) == 0:
    roll = random.randint(5,10)
    #todo: add random lose msgs
    msg += "Did you win? Hardly! Adding `{} point(s)` to the jackpot.".format(roll)
    increase_jackpot(roll)
  else:
    #todo: add random win msgs
    msg += "Chula! These crewmembers got it:\n"
    for c in CORRECT_ANSWERS:
      msg += "{} - {} points - {}\n".format(CORRECT_ANSWERS[c]["name"], CORRECT_ANSWERS[c]["points"], FUZZ[c])
  await quiz_channel.send(msg)
  # embed = await get_show(show_data, QUIZ_INDEX)
  # await quiz_channel.send(embed=embed)
  display_embed = await get_show(show_data, QUIZ_INDEX, QUIZ_SHOW)
  embed=discord.Embed(title=display_embed["title"], url=display_embed["url"], description=display_embed["description"], color=0xFFFFFF)
  embed.set_thumbnail(url=display_embed["still"])
  await quiz_channel.send(embed=embed)

  # update the quiz stuff
  CORRECT_ANSWERS = {} # winners
  FUZZ = {} # fuzz report
  QUIZ_SHOW = False 
  QUIZ_EPISODE = False # the current episode
  QUIZ_INDEX = -1
  logger.info(f"{Fore.LIGHTMAGENTA_EX}Quiz finished!{Fore.RESET}")