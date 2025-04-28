# handlers/eschelon_xp.py
from common import *

from queries.eschelon_xp import *
from utils.eschelon_rewards import award_level_up_badge, award_possible_crystal_buffer_pattern
from utils.image_utils import generate_badge_preview

# Load level up messages
with open("./data/level_up_messages.json") as f:
  random_level_up_messages = json.load(f)

blocked_level_up_sources = [
  "Personal Log",
  "Code 47",
  "Classified by Section 31"
]

# ____  _____________     _____                           .___.__
# \   \/  /\______   \   /  _  \__  _  _______ _______  __| _/|__| ____    ____
#  \     /  |     ___/  /  /_\  \ \/ \/ /\__  \\_  __ \/ __ | |  |/    \  / ___\
#  /     \  |    |     /    |    \     /  / __ \|  | \/ /_/ | |  |   |  \/ /_/  >
# /___/\  \ |____|     \____|__  /\/\_/  (____  /__|  \____ | |__|___|  /\___  /
#       \_/                    \/             \/           \/         \//_____/
async def award_xp(user_discord_id: str, amount: int, reason: str, source = None):
  """
  Award XP to a user, check if they level up, update their record, and log the award.
  Main entry point called by normal XP gain events.
  """
  current = await db_get_eschelon_progress(user_discord_id)

  if current:
    new_total_xp = current['current_xp'] + amount
  else:
    new_total_xp = amount

  new_level = level_for_total_xp(new_total_xp)

  await db_update_eschelon_progress(user_discord_id, new_total_xp, new_level)
  await db_insert_eschelon_history(user_discord_id, amount, new_level, reason)

  if current['current_level'] < new_level:
    return new_level
  else:
    return False

async def bulk_award_xp(user_discord_ids: list[str], amount: int, reason: str):
  """
  Award XP to multiple users at once.
  Useful for mass event rewards or promotions(?.
  """
  for user_id in user_discord_ids:
    await award_xp(user_id, amount, reason)

async def deduct_xp(user_discord_id: str, amount: int, reason: str):
  """
  Deduct XP from a user.
  Mainly for admin corrections or penalties.
  """
  current = await db_get_eschelon_progress(user_discord_id)
  if not current:
    return

  new_total_xp = max(current['current_xp'] - amount, 0)
  new_level = level_for_total_xp(new_total_xp)

  await db_update_eschelon_progress(user_discord_id, new_total_xp, new_level)
  await db_insert_eschelon_history(user_discord_id, -amount, new_level, reason)

async def force_set_xp(user_discord_id: str, new_xp: int, reason: str):
  """
  Manually set a user's XP to a specific value.
  Debugging tool.
  """
  new_level = level_for_total_xp(new_xp)

  await db_update_eschelon_progress(user_discord_id, new_xp, new_level)
  await db_insert_eschelon_history(user_discord_id, 0, new_level, reason)  # 0 xp gained, just admin override


# .____                      .__     ____ ___       ._.
# |    |    _______  __ ____ |  |   |    |   \______| |
# |    |  _/ __ \  \/ // __ \|  |   |    |   /\____ \ |
# |    |__\  ___/\   /\  ___/|  |__ |    |  / |  |_> >|
# |_______ \___  >\_/  \___  >____/ |______/  |   __/__
#         \/   \/          \/                 |__|   \/
async def handle_user_level_up(user_discord_id: str, level: int, reason: str, source = None):
  member = await bot.current_guild.fetch_member(user_discord_id)

  badge_data = await award_level_up_badge(member)
  source_details = determine_level_up_source_details(source)

  await post_level_up_embed(member, level, badge_data, source_details)
  log_level_up_to_console(member)

  awarded_buffer_pattern = await award_possible_crystal_buffer_pattern(user_discord_id)
  if awarded_buffer_pattern:
    await post_buffer_pattern_acquired_embed(member, level)


async def post_level_up_embed(member: discord.User, level: int, badge_data: dict, source_details = None):
  """
  Build and send a level-up notification embed to the XP notification channel.
  """
  level_up_msg = f"**{random.choice(random_level_up_messages['messages']).format(user=member.mention, level=level, prev_level=(level-1))}**"

  discord_file, attachment_url = await generate_badge_preview(member.id, badge_data)

  embed_description = f"{member.mention} has reached **Eschelon {level}** and earned a new badge!"
  if level == 2:
    embed_description += "\n\nCheck out your full badge list with `/badges collection`."
  if badge_data['was_on_wishlist']:
    embed_description += f"\n\nIt was also on their **wishlist**! {get_emoji('picard_yes_happy_celebrate')}"

  embed=discord.Embed(
    title="Eschelon Level Up!",
    description=embed_description,
    color=discord.Color.random()
  )
  embed.set_image(url=attachment_url)
  embed.set_thumbnail(url=random.choice(config["handlers"]["xp"]["celebration_images"]))
  embed.set_footer(text="See all your badges by typing '/badges showcase' - disable this by typing '/settings'")
  embed.add_field(name=badge_data['badge_name'], value=badge_data['badge_url'], inline=False)
  if source_details:
    embed.add_field(name="Eschelon Level Source", value=source_details)

  notification_channel = bot.get_channel(get_channel_id(config["handlers"]["xp"]["notification_channel"]))
  message = await notification_channel.send(content=f"## {level_up_msg}", file=discord_file, embed=embed)
  # Add + emoji so that users can add it as well to add the badge to their wishlist
  await message.add_reaction("✅")


def log_level_up_to_console(user: discord.User, level: int):
  """
  Pretty rainbow console log when a user levels up.
  """
  rainbow_l = f"{Back.RESET}{Back.RED} {Back.YELLOW} {Back.GREEN} {Back.CYAN} {Back.BLUE} {Back.MAGENTA} {Back.RESET}"
  rainbow_r = f"{Back.RESET}{Back.MAGENTA} {Back.BLUE} {Back.CYAN} {Back.GREEN} {Back.YELLOW} {Back.RED} {Back.RESET}"
  logger.info(f"{rainbow_l} {Style.BRIGHT}{user.display_name}{Style.RESET_ALL} reached Eschelon {level}! {rainbow_r}")


async def post_buffer_pattern_acquired_embed(member: discord.Member, level: int):
  """
  Sends a special embed to the XP notification channel announcing that the user
  has acquired a Crystal Buffer Pattern.
  """
  embed = discord.Embed(
    title="✨ Crystal Buffer Pattern Acquired! ✨",
    description=f"{member.mention} {random.choice(BUFFER_PATTERN_AQUISITION_REASONS)} **Crystal Buffer Pattern** when they reached Eschelon {level}!\n\nThey can now use it to replicate a new Crystal from scratch!",
    color=discord.Color.teal()
  )
  embed.set_image(url="https://i.imgur.com/lgP2miO.gif")
  embed.set_footer(text="Use  `/crystals replicate` to materialize a freshly minted Crystal!")

  notification_channel = bot.get_channel(get_channel_id(config['handlers']['xp']['notification_channel']))
  await notification_channel.send(embed=embed)

BUFFER_PATTERN_AQUISITION_REASONS = [
  "was exploring the Jefferies Tubes and stumbled across a",
  "was browsing some weird Holodeck programs and found a",
  "opened a dusty crate in Cargo Bay 4 and was surprised to see a",
  "fucked around and found out, and also found a",
  "made an important scientific discovery, a *fascinating*",
  "was just pressing random LCARS buttons in the Transporter Room and discovered a",
  "hacked the Gibson and downloaded a",
  "was swimming in Cetecean Ops and uncovered a",
  "was scanning for lifeforms and instead scanned a",
  "ordered Steak, Hot, for their mouth but instead it spit out a",
  "was eating some snacks in Ten Forward and under their table found a lost",
  "was just digging up weird dirt but dug up a"
]

# .____                      .__             ____ ___           ____ ___   __  .__.__
# |    |    _______  __ ____ |  |           |    |   \______   |    |   \_/  |_|__|  |   ______
# |    |  _/ __ \  \/ // __ \|  |    ______ |    |   /\____ \  |    |   /\   __\  |  |  /  ___/
# |    |__\  ___/\   /\  ___/|  |__ /_____/ |    |  / |  |_> > |    |  /  |  | |  |  |__\___ \
# |_______ \___  >\_/  \___  >____/         |______/  |   __/  |______/   |__| |__|____/____  >
#         \/   \/          \/                         |__|                                  \/
def is_message_channel_unblocked(message: discord.Message) -> bool:
  """Checks whether a message was posted in a non-blocked channel."""
  blocked_channels = get_channel_ids_list(config["handlers"]["starboard"]["blocked_channels"])

  if isinstance(message.channel, discord.Thread):
    return message.channel.parent.id not in blocked_channels
  if isinstance(message.channel, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel)):
    return message.channel.id not in blocked_channels

  return False

def determine_level_up_source_details(user: discord.User, source):
  """Returns a short description string about what caused the XP level-up event."""
  if isinstance(source, discord.Message):
    return _message_source_details(source)
  elif isinstance(source, discord.Reaction):
    return _reaction_source_details(user, source)
  elif isinstance(source, discord.ScheduledEvent):
    return _event_source_details(source)
  elif isinstance(source, str):
    return source
  else:
    return random.choice(blocked_level_up_sources)  # fallback

def _message_source_details(message: discord.Message) -> str:
  if is_message_channel_unblocked(message):
    return f"Their message at: {message.jump_url}"
  else:
    return random.choice(blocked_level_up_sources)

def _reaction_source_details(user: discord.User, reaction: discord.Reaction) -> str:
  if is_message_channel_unblocked(reaction.message):
    if user.id == reaction.message.author.id:
      return f"Receiving a {reaction.emoji} reaction on their message: {reaction.message.jump_url}"
    else:
      return f"Reacting with {reaction.emoji} to a message: {reaction.message.jump_url}"
  else:
    return random.choice(blocked_level_up_sources)

def _event_source_details(event: discord.ScheduledEvent) -> str:
  return f"Creating the event: `{event.name}`"

#   ______________________________
#  /  _____/\_   _____/\__    ___/_____
# /   \  ___ |    __)_   |    | /  ___/
# \    \_\  \|        \  |    | \___ \
#  \______  /_______  /  |____|/____  >
#         \/        \/              \/
async def get_user_eschelon_progress(user_discord_id: str) -> dict:
  """
  Retrieve the user's full eschelon_progress record.
  Intended for internal lookups and validation.
  """
  return await db_get_eschelon_progress(user_discord_id)

async def get_xp_summary(user_discord_id: str) -> dict:
  """
  Return a summary dictionary with user's level, XP into level, XP required to next level, and total XP.
  Useful for user-facing displays like profiles or progress bars.
  """
  progress = await db_get_eschelon_progress(user_discord_id)

  if not progress:
    return {
      "level": 1,
      "xp_into_level": 0,
      "xp_required": xp_required_for_level(1),
      "total_xp": 0
    }

  total_xp = progress['current_xp']
  level, xp_into_level, xp_required = xp_progress_within_level(total_xp)

  return {
    "level": level,
    "xp_into_level": xp_into_level,
    "xp_required": xp_required,
    "total_xp": total_xp
  }

# ____  _____________  _________
# \   \/  /\______   \ \_   ___ \ __ ____________  __ ____
#  \     /  |     ___/ /    \  \/|  |  \_  __ \  \/ // __ \
#  /     \  |    |     \     \___|  |  /|  | \/\   /\  ___/
# /___/\  \ |____|      \______  /____/ |__|    \_/  \___  >
#       \_/                    \/                        \/
def xp_required_for_level(level: int) -> int:
  """
  Calculate the amount of XP required to level up from the given level.
  Applies cubic ease-in/ease-out curve up to Level 170, then flat 420 XP per level.
  """
  if level <= 0:
    return 0
  if level > 170:
    return 420

  t = (level - 1) / (170 - 1)
  ease = 3 * (t**2) - 2 * (t**3)
  return int(69 + (420 - 69) * ease)

def level_for_total_xp(total_xp: int) -> int:
  """
  Calculate the amount of XP required to level up from the given level.
  Applies cubic ease-in/ease-out curve up to Level 170, then flat 420 XP per level.
  """
  xp = 0
  level = 1

  while True:
    needed = xp_required_for_level(level)
    if xp + needed > total_xp:
      break
    xp += needed
    level += 1

  return level

def xp_progress_within_level(total_xp: int) -> tuple[int, int, int]:
  """
  Returns the user's current level, how much XP they have into that level,
  and the XP required to reach the next level.
  Useful for progress bars and UI displays.
  """
  level = level_for_total_xp(total_xp)
  xp_at_level_start = sum(xp_required_for_level(lvl) for lvl in range(1, level))
  xp_into_level = total_xp - xp_at_level_start
  xp_required = xp_required_for_level(level)
  return level, xp_into_level, xp_required

def calculate_next_level_xp_gap(level: int) -> int:
  """
  Shortcut function to return how much XP is needed to level up from a given level.
  """
  return xp_required_for_level(level)
