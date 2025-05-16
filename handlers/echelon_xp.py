# handlers/echelon_xp.py
from common import *

from queries.echelon_xp import *
from queries.wishlists import db_is_badge_on_users_wishlist
from utils.echelon_rewards import *
from utils.prestige import PRESTIGE_TIERS, PRESTIGE_THEMES
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
async def award_xp(user: discord.User, amount: int, reason: str, channel = None):
  """
  Award XP to a user, check if they level up, update their record, and log the award.
  NOTE: Use `grant_xp` from `handlers.xp` if you want to give user's xp publically! It handles double xp and level ups, etc!
  """
  user_discord_id = user.id
  current = await db_get_echelon_progress(user_discord_id)

  if current:
    new_total_xp = current['current_xp'] + amount
  else:
    new_total_xp = amount

  new_level = level_for_total_xp(new_total_xp)

  await db_update_echelon_progress(user_discord_id, new_total_xp, new_level)
  await db_insert_echelon_history(user_discord_id, amount, new_level, channel.id if channel else None, reason)
  console_log_xp_history(user, amount, reason)

  if not current or current['current_level'] < new_level:
    console_log_level_up(user, new_level)
    return new_level
  else:
    return False

async def deduct_xp(user_discord_id: str, amount: int, channel_id, reason: str):
  """
  Deduct XP from a user.
  Only for for admin corrections, etc (hopefully never needed...).
  """
  current = await db_get_echelon_progress(user_discord_id)
  if not current:
    return

  new_total_xp = max(current['current_xp'] - amount, 0)
  new_level = level_for_total_xp(new_total_xp)

  await db_update_echelon_progress(user_discord_id, new_total_xp, new_level)
  await db_insert_echelon_history(user_discord_id, -amount, new_level, channel_id, reason)

async def force_set_xp(user_discord_id: str, new_xp: int, reason: str):
  """
  Manually set a user's XP to a specific value.
  Debugging tool.
  """
  new_level = level_for_total_xp(new_xp)

  await db_update_echelon_progress(user_discord_id, new_xp, new_level)
  await db_insert_echelon_history(user_discord_id, 0, new_level, reason)  # 0 xp gained, just admin override


# .____                      .__     ____ ___       ._.
# |    |    _______  __ ____ |  |   |    |   \______| |
# |    |  _/ __ \  \/ // __ \|  |   |    |   /\____ \ |
# |    |__\  ___/\   /\  ___/|  |__ |    |  / |  |_> >|
# |_______ \___  >\_/  \___  >____/ |______/  |   __/__
#         \/   \/          \/                 |__|   \/
async def handle_user_level_up(member: discord.User, level: int, source = None):
  logger.info(f"[DEBUG] Handling user level up: {member.display_name} to level {level}")

  prestige_before = await get_user_prestige_level(member)
  logger.info(f"prestige_before: {prestige_before}")

  badge_data = None
  awarded_buffer_pattern = None
  if level == 1:
    badge_data, awarded_buffer_pattern = await award_initial_welcome_package(member)
    source_details = determine_level_up_source_details(member, source)
    await post_first_level_welcome_embed(member, badge_data, source_details)
    await post_buffer_pattern_acquired_embed(member, level, awarded_buffer_pattern)
    return
  else:
    badge_data = await award_level_up_badge(member)
    awarded_buffer_pattern = await award_possible_crystal_pattern_buffer(member)

  prestige_after = await get_user_prestige_level(member)
  logger.info(f"prestige_after: {prestige_after}")

  if await db_is_badge_on_users_wishlist(member.id, badge_data['badge_info_id']):
    badge_data['was_on_wishlist'] = True

  source_details = determine_level_up_source_details(member, source)
  # Handle Prestige Advancement
  if prestige_after > prestige_before:
    await award_special_badge_prestige_echoes(member, prestige_after)
    await post_prestige_advancement_embed(member, level, prestige_after, badge_data, source_details)
  # Handle Standard Level Ups
  else:
    await post_level_up_embed(member, level, prestige_after, badge_data, source_details)

  if awarded_buffer_pattern:
    await post_buffer_pattern_acquired_embed(member, level, awarded_buffer_pattern)


async def post_level_up_embed(member: discord.User, level: int, prestige:int, badge_data: dict, source_details = None):
  """
  Build and send a level-up notification embed to the XP notification channel.
  """
  level_up_msg = f"**{random.choice(random_level_up_messages['messages']).format(user=member.mention, level=level, prev_level=(level-1))}**"

  discord_file, attachment_url = await generate_badge_preview(member.id, badge_data, theme='teal')

  embed_description = f"{member.mention} has reached **Echelon {level}** and earned a Badge ({PRESTIGE_TIERS[prestige]} Tier)!"
  if badge_data.get('was_on_wishlist', False):
    embed_description += f"\n\nIt was also on their ✨ **wishlist** ✨! {get_emoji('picard_yes_happy_celebrate')}"

  embed_color = discord.Color.teal()
  if prestige > 0:
    prestige_color = PRESTIGE_THEMES[prestige]['primary']
    embed_color = discord.Color.from_rgb(prestige_color[0], prestige_color[1], prestige_color[2])

  embed=discord.Embed(
    title="Echelon Level Up!",
    description=embed_description,
    color=embed_color
  )
  embed.set_image(url=attachment_url)
  embed.set_thumbnail(url=random.choice(config["handlers"]["xp"]["celebration_images"]))
  embed.add_field(name=badge_data['badge_name'], value=badge_data['badge_url'], inline=False)
  if source_details:
    embed.add_field(name="Echelon Level Source", value=source_details)
  embed.set_footer(text="See all your badges by typing '/badges collection' - disable this by typing '/settings'")

  notification_channel = bot.get_channel(get_channel_id(config["handlers"]["xp"]["notification_channel"]))
  message = await notification_channel.send(content=f"## {level_up_msg}", file=discord_file, embed=embed)
  # Add + emoji so that users can add it as well to add the badge to their wishlist
  await message.add_reaction("✅")


async def post_prestige_advancement_embed(member: discord.Member, level: int, new_prestige: int, badge_data: dict, source_details = None):
  """
  Builds and sends a celebratory embed to mark the user's advancement to a new prestige tier.
  This replaces the regular level-up embed when a prestige tier is reached for the first time.

  Args:
    member (discord.Member): The user who advanced.
    new_prestige (int): The prestige tier the user just reached.
  """
  prestige_name = PRESTIGE_TIERS.get(new_prestige, f"Prestige {new_prestige}")
  old_prestige_name = PRESTIGE_TIERS.get(new_prestige - 1, "Standard")

  prestige_msg = f"## STRANGE ENERGIES AFOOT! {member.mention} is entering boundary-space upon reaching **Echelon {level}**!!!"

  discord_file, attachment_url = await generate_badge_preview(member.id, badge_data, theme='teal')

  title = f"Echelon {level} and {prestige_name} Tier Unlocked!"
  description = (
    f"{member.mention} has ascended to the **{prestige_name} Prestige Tier!**"
    f"\n\nThey have reached **Echelon {level}** and have received their first **{prestige_name}** Badge!"
    f"\n\nThis also means they're within the *Prestige Quantum Improbability Field*..."
    f"\n\nAs they continue to advance into {prestige_name} the pull grows ever larger as the odds warp and skew! "
    f"Their chances of receiving *{old_prestige_name}* badges lessen while chances of receiving *{prestige_name}* badges strengthen!"
  )

  prestige_color = PRESTIGE_THEMES[new_prestige]['primary']
  embed = discord.Embed(
    title=title,
    description=description,
    color=discord.Color.from_rgb(prestige_color[0], prestige_color[1], prestige_color[2])
  )
  embed.set_image(url=attachment_url)
  embed.set_thumbnail(url=random.choice(config["handlers"]["xp"]["celebration_images"])) # TODO: Randomized special image here
  embed.add_field(name=badge_data['badge_name'], value=badge_data['badge_url'], inline=False)
  if source_details:
    embed.add_field(name="Echelon Level Source", value=source_details)
  embed.set_footer(text="Echoes of their past have carried forward — Any special badges they've acquired have ascended alongside them!")

  notification_channel = bot.get_channel(get_channel_id(config["handlers"]["xp"]["notification_channel"]))
  await notification_channel.send(content=prestige_msg, file=discord_file, embed=embed)


async def post_first_level_welcome_embed(member, badge_data, source_details = None):
  """
  Builds and sends a celebratory embed to mark the user's initialization to the Echelon System.

  Args:
    member (discord.Member): The user who advanced.
    badge_data: The badge_data for the standard FOD Welcome badge, or None if they've migrated from the old Legacy system
  """
  notification_channel = bot.get_channel(get_channel_id(config["handlers"]["xp"]["notification_channel"]))
  agimus_announcement_channel = bot.get_channel(get_channel_id(config["agimus_announcement_channel"]))

  if badge_data:
    prestige_msg = f"## TRANSPORTER SIGNAL INBOUND! {member.mention}, welcome to Echelon 1!!!"
    discord_file, attachment_url = await generate_badge_preview(member.id, badge_data, theme='teal')
    embed = discord.Embed(
      title="Echelon 1!",
      description=f"Enter, Friend! Welcome aboard {member.mention}! You've materialized onto The Hood's Transporter Pad and been inducted into **Echelon 1**!"
                  "\n\nYour activity on The Hood earns you optional XP and Badges you can collect and trade to other crew members (for funzies)!",
      color=discord.Color.green()
    )
    embed.set_image(url=attachment_url)
    embed.set_thumbnail(url=random.choice(config["handlers"]["xp"]["celebration_images"])) # TODO: Randomized special image here
    embed.add_field(name=badge_data['badge_name'], value=badge_data['badge_url'], inline=False)
    if source_details:
      embed.add_field(name="Echelon Level Source", value=source_details)
    embed.set_footer(text="You can opt-out of the Echelon System by using `/settings` at any time if so desired.")
    await notification_channel.send(content=prestige_msg, file=discord_file, embed=embed)
  else:
    prestige_msg = f"## TRANSPORTER SIGNAL CONVERSION COMPLETE! {member.mention}, welcome to Echelon 1!!!"
    embed = discord.Embed(
      title="Echelon 1!",
      description=f"Re-sequencing {member.mention}'s pattern finalized! You've been converted from the Legacy XP System and initialized at **Echelon 1**!"
                  "\n\nVery exciting. Your Legacy XP has been retained for bragging rights (viewable through `/profile`), and worry not, all of your existing badges are intact at the Standard Prestige Tier."
                  f"\n\nBe sure to check out the details of the new system over at {agimus_announcement_channel.mention}",
      color=discord.Color.green()
    )
    embed.set_image(url="https://i.imgur.com/3ALMc8V.png")
    embed.set_thumbnail(url=random.choice(config["handlers"]["xp"]["celebration_images"])) # TODO: Randomized special image here
    if source_details:
      embed.add_field(name="Echelon Level Source", value=source_details)
    embed.set_footer(text="You can opt-out of the Echelon System by using `/settings` at any time if so desired.")
    await notification_channel.send(content=prestige_msg, embed=embed)

async def post_buffer_pattern_acquired_embed(member: discord.Member, level: int, number_of_patterns: int = 1):
  """
  Sends a special embed to the XP notification channel announcing that the user
  has acquired a Crystal Pattern Buffer.

  If they received more than one (only currently occurs when they first hit Echelon 1),
  there's a little special messaging instead of the standard.
  """
  embed = None
  if number_of_patterns == 1:
    embed = discord.Embed(
      title="Crystal Pattern Buffer Acquired!",
      description=f"{member.mention} {random.choice(BUFFER_PATTERN_AQUISITION_REASONS)} **Crystal Pattern Buffer** when they reached Echelon {level}!\n\nThey can now use it to replicate a Crystal from scratch!",
      color=discord.Color.teal()
    )
  else:
    embed = discord.Embed(
      title="Crystal Pattern Buffers Acquired!",
      description=f"{member.mention} materialized onto the transporter pad with **{number_of_patterns} Crystal Pattern Buffers** in their hands when they reached Echelon {level}!\n\n"
                  f"They can now use them to replicate **{number_of_patterns}** Crystals from scratch!",
      color=discord.Color.teal()
    )
  embed.set_image(url=random.choice(BUFFER_PATTERN_AQUISITION_GIFS))
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
  "ordered `Steak, Hot, for their mouth` but instead it spit out a",
  "was eating some snacks in Ten Forward and bit into a lost",
  "was digging up weird dirt but dug up a",
  "overloaded the Deflector Dish and it spat out a",
  "found a mislabeled isolinear chip that contained a fully encoded",
  "asked the replicator for a `BANANA, HOT` and got a glowing",
  "was trying to synthesize raktajino and got a warm",
  "ran a Level-Five Diagnostic and the results came back with one unexpected",
  "was reconfiguring the warp core's resonance frequency and discovered a",
  "asked for a sonic shower and out sprayed a",
  "activated a forgotten TOS-era control panel and found a vintage-looking",
]

BUFFER_PATTERN_AQUISITION_GIFS = [
  "https://i.imgur.com/lgP2miO.gif",
  "https://i.imgur.com/ziLTH4f.gif",
  "https://i.imgur.com/RVEncra.gif",
  "https://i.imgur.com/O8FIb0I.gif"
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
  logger.info("Level Up Source:")
  logger.info(pprint(source))
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
async def get_user_echelon_progress(user_discord_id: str) -> dict:
  """
  Retrieve the user's full echelon_progress record.
  Intended for internal lookups and validation.
  """
  return await db_get_echelon_progress(user_discord_id)

async def get_xp_summary(user_discord_id: str) -> dict:
  """
  Return a summary dictionary with user's level, XP into level, XP required to next level, and total XP.
  Useful for user-facing displays like profiles or progress bars.
  """
  progress = await db_get_echelon_progress(user_discord_id)

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
    return 369

  t = (level - 1) / (170 - 1)
  ease = 3 * (t**2) - 2 * (t**3)
  return int(69 + (369 - 69) * ease)

_xp_to_level_170 = None
def total_xp_to_level_170() -> int:
  global _xp_to_level_170
  if _xp_to_level_170 is None:
    _xp_to_level_170 = sum(xp_required_for_level(level) for level in range(1, 170))
  return _xp_to_level_170

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


# _________                            .__            ____ ___   __  .__.__
# \_   ___ \  ____   ____   __________ |  |   ____   |    |   \_/  |_|__|  |   ______
# /    \  \/ /  _ \ /    \ /  ___/  _ \|  | _/ __ \  |    |   /\   __\  |  |  /  ___/
# \     \___(  <_> )   |  \\___ (  <_> )  |_\  ___/  |    |  /  |  | |  |  |__\___ \
#  \______  /\____/|___|  /____  >____/|____/\___  > |______/   |__| |__|____/____  >
#         \/            \/     \/                \/                               \/

# XP logging color rotation
current_color = 0
xp_colors = [
  Fore.RED, Fore.LIGHTRED_EX, Fore.YELLOW, Fore.LIGHTYELLOW_EX,
  Fore.GREEN, Fore.LIGHTGREEN_EX, Fore.LIGHTCYAN_EX, Fore.CYAN,
  Fore.LIGHTBLUE_EX, Fore.BLUE, Fore.MAGENTA, Fore.LIGHTMAGENTA_EX
]
# XP logging reasons
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

def console_log_xp_history(user: discord.User, amt: int, reason: str):
  global current_color
  msg_color = xp_colors[current_color]
  reason_text = reason_descriptions.get(reason, reason)
  star = f"{msg_color}{Style.BRIGHT}*{Style.NORMAL}{Fore.RESET}"
  logger.info(f"{star} {msg_color}{user.display_name}{Fore.RESET} earns {msg_color}{amt} XP{Fore.RESET} for {Style.BRIGHT}{reason_text}{Style.RESET_ALL}! {star}")
  current_color = (current_color + 1) % len(xp_colors)

def console_log_level_up(user: discord.User, new_level: int):
  rainbow_l = f"{Back.RESET}{Back.RED} {Back.YELLOW} {Back.GREEN} {Back.CYAN} {Back.BLUE} {Back.MAGENTA}{Back.RESET}"
  rainbow_r = f"{Back.RESET}{Back.MAGENTA} {Back.BLUE} {Back.CYAN} {Back.GREEN} {Back.YELLOW} {Back.RED}{Back.RESET}"
  logger.info(f"{rainbow_l} {Style.BRIGHT}{user.display_name}{Style.RESET_ALL} reached Level {new_level}! {rainbow_r}")
