import math
import asyncio
import random
import unicodedata
from collections import defaultdict
from datetime import datetime

from common import *

from handlers.echelon_xp import *
from handlers.auto_promotion import handle_auto_promotions
from queries.wishlists import *
from utils.echelon_rewards import *
from utils.badge_utils import *
from utils.settings_utils import db_get_current_xp_enabled_value


# Separate lock for each user to prevent XP race conditions without global blocking
user_xp_locks = defaultdict(asyncio.Lock)

# Load level up messages
with open("./data/level_up_messages.json") as f:
  random_level_up_messages = json.load(f)

# Blocked source descriptions
blocked_level_up_sources = [
  "Personal Log",
  "Code 47",
  "Classified by Section 31"
]


# ____  _____________  .___                                                   __
# \   \/  /\______   \ |   | ____   ___________   ____   _____   ____   _____/  |_
#  \     /  |     ___/ |   |/    \_/ ___\_  __ \_/ __ \ /     \_/ __ \ /    \   __\
#  /     \  |    |     |   |   |  \  \___|  | \/\  ___/|  Y Y  \  ___/|   |  \  |
# /___/\  \ |____|     |___|___|  /\___  >__|    \___  >__|_|  /\___  >___|  /__|
#       \_/                     \/     \/            \/      \/     \/     \/
async def grant_xp(user: discord.User, amount: int, reason: str, channel = None, source = None):
  async with user_xp_locks[user.id]:
    """Award XP to a user through the Echelon XP system."""
    # Make sure that they actually want to participate in the XP system...
    xp_enabled = bool(await db_get_current_xp_enabled_value(user.id))
    if not xp_enabled:
      return

    if is_xp_doubled():
      amount *= 2
    # Award XP (This also handles Leveling Up if appropriate)
    new_level = await award_xp(user, amount, reason, channel)

    if new_level:
      await handle_user_level_up(user, new_level, source=source)

    return new_level

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
    await grant_xp(message.author, xp_amt, "posted_message", message.channel, source=message)
    await handle_auto_promotions(message)


async def handle_react_xp(reaction: discord.Reaction, user: discord.User):
  if reaction.message.author.bot or user.bot or user.id == reaction.message.author.id:
    return

  blocked_channels = get_channel_ids_list(config["handlers"]["xp"]["blocked_channels"])
  if reaction.message.channel.id in blocked_channels:
    return

  if not await _log_react_history(reaction, user):
    return  # Duplicate reaction

  # Grant XP to reactor and author
  await grant_xp(user, 1, "added_reaction", channel=reaction.message.channel, source=reaction)
  await grant_xp(reaction.message.author, 1, "got_single_reaction", channel=reaction.message.channel, source=reaction)
  await grant_bonusworthy_reaction_xp(reaction)


# Reaction Helpers
async def _log_react_history(reaction: discord.Reaction, user: discord.User) -> bool:
  async with AgimusDB() as db:
    try:
      emoji_str = normalize_reaction_string(reaction)
      await db.execute(
        "INSERT INTO reactions (user_id, user_name, reaction, reaction_message_id) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE user_id = user_id",
        (user.id, user.display_name, emoji_str, reaction.message.id)
      )
      return db.rowcount > 0
    except Exception as e:
      logger.warning(f"[XP] Reaction logging failed: {e}")
      return False

def normalize_reaction_string(reaction: discord.Reaction) -> str:
  """
  Returns a stable string representation for both custom and unicode emoji.
  Custom: "<:name:id>"
  Unicode: Normalized unicode string
  """
  emoji = reaction.emoji
  if isinstance(emoji, str):
    # Normalize unicode emoji to NFKC (Compatibility Decomposition, then Composition)
    return unicodedata.normalize("NFKC", emoji)
  else:
    # It's a custom emoji (discord.PartialEmoji or Emoji)
    return str(emoji)

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
          await grant_xp(reaction.message.author, xp_amt, "got_reactions", channel=reaction.message.channel, source=reaction)

        break


async def handle_event_creation_xp(event: discord.ScheduledEvent):
  creator = await bot.fetch_user(event.creator_id)
  location = event.location.value
  if type(location) == str:
    # Users might create an event that isn't a VoiceChannel
    return
  await grant_xp(creator, 45, "created_event", source="Started their Event!")
