import math
import asyncio
import random
from datetime import datetime

from common import *

from commands.badges import *
from handlers.eschelon_xp import *
from handlers.auto_promotion import handle_auto_promotions
from queries.wishlist import *
from utils.eschelon_rewards import *
from utils.badge_utils import *

# XP lock to prevent race conditions
xp_lock = asyncio.Lock()

# XP logging color rotation
xp_colors = [
  Fore.RED, Fore.LIGHTRED_EX, Fore.YELLOW, Fore.LIGHTYELLOW_EX,
  Fore.GREEN, Fore.LIGHTGREEN_EX, Fore.LIGHTCYAN_EX, Fore.CYAN,
  Fore.LIGHTBLUE_EX, Fore.BLUE, Fore.MAGENTA, Fore.LIGHTMAGENTA_EX
]
current_color = 0

# Load level up messages
with open("./data/level_up_messages.json") as f:
  random_level_up_messages = json.load(f)

# XP reasons
reason_descriptions = {
  "posted_message": "posting a message",
  "added_reaction": "adding a reaction",
  "got_single_reaction": "getting a reaction",
  "got_reactions": "getting lots of reactions",
  "intro_message": "posting an introduction in #first-contact",
  "starboard_post": "getting a post sent to the starboard",
  "used_computer": "using the computer",
  "used_wordcloud": "generating a wordcloud",
  "played_zork": "playing zork",
  "created_event": "creating an event",
  "tongo_loss": "losing badges in tongo"
}

# Blocked source descriptions
blocked_level_up_sources = [
  "Personal Log",
  "Code 47",
  "Classified by Section 31"
]

#    _____                           .___.__
#   /  _  \__  _  _______ _______  __| _/|__| ____    ____
#  /  /_\  \ \/ \/ /\__  \\_  __ \/ __ | |  |/    \  / ___\
# /    |    \     /  / __ \|  | \/ /_/ | |  |   |  \/ /_/  >
# \____|__  /\/\_/  (____  /__|  \____ | |__|___|  /\___  /
#         \/             \/           \/         \//_____/
async def grant_xp(user: discord.User, amount: int, reason: str, source = None):
  user_discord_id = user.id
  """Award XP to a user through the Eschelon XP system."""
  async with xp_lock:
    if is_xp_doubled():
      amount *= 2
    # Award XP (This also handles Leveling Up if appropriate)
    new_level = await award_xp(user_discord_id, amount, reason, source)
    if new_level:
      await handle_user_level_up(user_discord_id, new_level, reason, source)

def is_xp_doubled() -> bool:
  """Determine if XP doubling is active (currently based on weekends)."""
  return datetime.today().weekday() >= 4  # Friday-Sunday


# ___________                    __      ___ ___                    .___.__  .__
# \_   _____/__  __ ____   _____/  |_   /   |   \_____    ____    __| _/|  | |__| ____    ____
#  |    __)_\  \/ // __ \ /    \   __\ /    ~    \__  \  /    \  / __ | |  | |  |/    \  / ___\
#  |        \\   /\  ___/|   |  \  |   \    Y    // __ \|   |  \/ /_/ | |  |_|  |   |  \/ /_/  >
# /_______  / \_/  \___  >___|  /__|    \___|_  /(____  /___|  /\____ | |____/__|___|  /\___  /
#         \/           \/     \/              \/      \/     \/      \/              \//_____/
async def handle_message_xp(message: discord.Message):
  if message.guild is None or message.author.bot:
    return

  blocked_channels = get_channel_ids_list(config["handlers"]["xp"]["blocked_channels"])
  if message.channel.id in blocked_channels:
    return

  xp_amt = 0
  word_count = len(message.content.split())

  if word_count >= 3:
    xp_amt += 1
    if any(e in message.content for e in config["all_emoji"]):
      xp_amt += 1
  if word_count > 33:
    xp_amt += 1
  if word_count > 66:
    xp_amt += 1
  if message.attachments:
    xp_amt += 1

  if xp_amt > 0:
    await grant_xp(message.author, xp_amt, "posted_message")
    await handle_auto_promotions(message)


async def handle_react_xp(reaction: discord.Reaction, user: discord.User):
  if reaction.message.author.bot or user.bot or user.id == reaction.message.author.id:
    return

  blocked_channels = get_channel_ids_list(config["handlers"]["xp"]["blocked_channels"])
  if reaction.message.channel.id in blocked_channels:
    return

  reaction_already_counted = await _check_react_history(reaction, user)
  if reaction_already_counted:
    return

  await _log_react_history(reaction, user)
  await grant_xp(user, 1, "added_reaction")
  await grant_xp(reaction.message.author, 1, "got_single_reaction")
  await grant_bonusworthy_reaction_xp(reaction)


# Reaction Helpers
async def _check_react_history(reaction: discord.Reaction, user: discord.User):
  async with AgimusDB() as db:
    await db.execute(
      "SELECT id FROM reactions WHERE user_id = %s AND reaction = %s AND reaction_message_id = %s",
      (user.id, f"{reaction}", reaction.message.id)
    )
    return await db.fetchone()


async def _log_react_history(reaction: discord.Reaction, user: discord.User):
  async with AgimusDB() as db:
    await db.execute(
      "INSERT INTO reactions (user_id, user_name, reaction, reaction_message_id) VALUES (%s, %s, %s, %s)",
      (user.id, user.display_name, f"{reaction}", reaction.message.id)
    )


BONUSWORTHY_EMOJI_MATCHES = None
async def grant_bonusworthy_reaction_xp(reaction: discord.Reaction):
  global BONUSWORTHY_EMOJI_MATCHES

  if BONUSWORTHY_EMOJI_MATCHES is None:
    starboard_dict = config["handlers"]["starboard"]["boards"].copy()
    starboard_dict['bonusworth_emoji'] = config["handlers"]["xp"]["bonusworthy_emoji"]
    from handlers.starboard import generate_board_compiled_patterns
    starboard_emoji_matches = generate_board_compiled_patterns(starboard_dict).values()
    BONUSWORTHY_EMOJI_MATCHES = [match for sublist in starboard_emoji_matches for match in sublist]

  if hasattr(reaction.emoji, "name"):
    for match in BONUSWORTHY_EMOJI_MATCHES:
      if match.search(reaction.emoji.name.lower()) is not None:
        xp_amt = 0
        if 5 <= reaction.count < 10:
          xp_amt = 1
        elif 10 <= reaction.count < 20:
          xp_amt = 2
        elif reaction.count >= 20:
          xp_amt = 5

        if xp_amt > 0:
          await grant_xp(reaction.message.author, xp_amt, "got_reactions")

        break


async def handle_event_creation_xp(event: discord.ScheduledEvent):
  creator = await bot.fetch_user(event.creator_id)
  location = event.location.value
  if type(location) == str:
    # Users might create an event that isn't a VoiceChannel
    return
  await grant_xp(creator, 45, "created_event")


# _________                            .__            ____ ___   __  .__.__
# \_   ___ \  ____   ____   __________ |  |   ____   |    |   \_/  |_|__|  |   ______
# /    \  \/ /  _ \ /    \ /  ___/  _ \|  | _/ __ \  |    |   /\   __\  |  |  /  ___/
# \     \___(  <_> )   |  \\___ (  <_> )  |_\  ___/  |    |  /  |  | |  |  |__\___ \
#  \______  /\____/|___|  /____  >____/|____/\___  > |______/   |__| |__|____/____  >
#         \/            \/     \/                \/                               \/
def console_log_xp_history(user: discord.User, amt: int, reason: str):
  global current_color
  msg_color = xp_colors[current_color]
  reason_text = reason_descriptions .get(reason, reason)
  star = f"{msg_color}{Style.BRIGHT}*{Style.NORMAL}{Fore.RESET}"
  logger.info(f"{star} {msg_color}{user.display_name}{Fore.RESET} earns {msg_color}{amt} XP{Fore.RESET} for {Style.BRIGHT}{reason_text}{Style.RESET_ALL}! {star}")
  current_color = (current_color + 1) % len(xp_colors)

def console_log_level_up(user: discord.User, new_level: int):
  rainbow_l = f"{Back.RESET}{Back.RED} {Back.YELLOW} {Back.GREEN} {Back.CYAN} {Back.BLUE} {Back.MAGENTA}{Back.RESET}"
  rainbow_r = f"{Back.RESET}{Back.MAGENTA} {Back.BLUE} {Back.CYAN} {Back.GREEN} {Back.YELLOW} {Back.RED}{Back.RESET}"
  logger.info(f"{rainbow_l} {Style.BRIGHT}{user.display_name}{Style.RESET_ALL} reached Level {new_level}! {rainbow_r}")
