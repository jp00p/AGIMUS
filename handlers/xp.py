import math
import asyncio
import random
from datetime import datetime

import discord
from common import *
from commands.badges import give_user_badge, send_badge_reward_message
from queries.wishlist import db_autolock_badges_by_filenames_if_in_wishlist, db_get_user_wishlist_badges
from utils.badge_utils import db_get_user_badges, db_purge_users_wishlist
from utils.shiny_badges import generate_shiny_badge_image, insert_shiny_badge_info

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
reasons = {
  "posted_message": "posting a message",
  "added_reaction": "adding a reaction",
  "got_single_reaction": "getting a reaction",
  "got_reactions": "getting lots of reactions",
  "intro_message": "posting an introduction in #first-contact",
  "starboard_post": "getting a post sent to the starboard",
  "slot_win": "winning the slots",
  "quiz_win": "winning a quiz",
  "trivia_win": "winning at trivia",
  "trivia_play": "participating in trivia",
  "poker_win": "winning a hand of poker",
  "used_computer": "using the computer",
  "asked_agimus": "asking agimus a question",
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

# --- Section 1: XP Calculation & Handling ---

# Award XP for a new message
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
    await increment_user_xp(message.author, xp_amt, "posted_message", message.channel, message)

  await handle_auto_promotions(message, xp_amt)

# Auto-promotion routing
async def handle_auto_promotions(message: discord.Message, xp_amt: int):
  promotion_config = config["roles"]["promotion_roles"]
  cadet = promotion_config["ranks"]["cadet"]
  ensign = promotion_config["ranks"]["ensign"]
  guild_roles = [r.name for r in await message.guild.fetch_roles()]

  if cadet in guild_roles and ensign in guild_roles:
    await _handle_intro_channel_promotion(message)
    await _handle_rank_xp_promotion(message, xp_amt)
  else:
    logger.info(f"Promotion is enabled but required roles are missing: {guild_roles}")

# Handle intro promotion if message is in intro channel
async def _handle_intro_channel_promotion(message):
  if message.channel.id != get_channel_id(config["intro_channel"]):
    return

  member = message.author
  promotion_roles = config["roles"]["promotion_roles"]["ranks"]
  cadet_role_name = promotion_roles["cadet"]
  author_roles = [r.name for r in member.roles]

  if cadet_role_name in author_roles:
    return

  cadet_role = discord.utils.get(message.guild.roles, name=cadet_role_name)
  if cadet_role:
    logger.info(f"Adding {Fore.CYAN}Cadet{Fore.RESET} role to {Style.BRIGHT}{member.display_name}{Style.RESET_ALL}")
    await member.add_roles(cadet_role)
    await increment_user_xp(member, 10, "intro_message", message.channel, message)
    await give_welcome_badge(member.id)
    await _send_intro_welcome_embed(message)

# Handle XP-based role promotions
async def _handle_rank_xp_promotion(message, xp_amt):
  user = message.author
  roles = config["roles"]["promotion_roles"]["ranks"]
  cadet_role = discord.utils.get(message.guild.roles, name=roles["cadet"])
  ensign_role = discord.utils.get(message.guild.roles, name=roles["ensign"])
  author_roles = [r.name for r in user.roles]

  xp_data = await get_user_xp(user.id)
  user_xp = xp_data["xp"]
  thresholds = config["roles"]["promotion_roles"]["required_rank_xp"]

  if roles["cadet"] not in author_roles and user_xp >= thresholds["cadet"]:
    await user.add_roles(cadet_role)
    logger.info(f"{Style.BRIGHT}{user.display_name}{Style.RESET_ALL} promoted to {Fore.CYAN}Cadet{Fore.RESET} via XP!")
    await give_welcome_badge(user.id)
  elif roles["ensign"] not in author_roles and user_xp >= thresholds["ensign"]:
    await user.add_roles(ensign_role)
    logger.info(f"{Style.BRIGHT}{user.display_name}{Style.RESET_ALL} promoted to {Fore.GREEN}Ensign{Fore.RESET} via XP!")

# Send custom intro embed for welcoming new users
async def _send_intro_welcome_embed(message):
  member = message.author
  usher_msgs = config["handlers"]["xp"]["usher_messages"]
  welcome_embed = discord.Embed(
    title=f"Could someone {random.choice(usher_msgs)}?",
    color=discord.Color.random(),
    description=f"Please greet our new crewmember in <#{get_channel_id(config['channels']['ten-forward'])}>!"
  )

  welcome_embed.set_image(url=random.choice(config["handlers"]["xp"]["welcome_images"]))

  welcome_embed.add_field(name=f"Offer advice {get_emoji('pakled_smart_lol')}",
    value=f"Recommend <#{get_channel_id(config['channels']['channel-guide'])}> and <#{get_channel_id(config['channels']['roles-and-pronouns'])}>", inline=False)
  welcome_embed.add_field(name=f"Read their intro {get_emoji('bashir_zoom_look_huh')}",
    value=f"Personalize your greeting based on their intro: {message.jump_url}", inline=False)
  welcome_embed.add_field(name=f"Bring them in {get_emoji('kira_good_morning_hello')}",
    value=f"Suggest a channel like <#{get_channel_id(config['channels']['animal-holophotography'])}> to start!", inline=False)

  welcome_embed.set_footer(text="Thank you officers! 💖")
  welcome_channel = bot.get_channel(get_channel_id(config["welcome_channel"]))
  await welcome_channel.send(content=f"@here — {member.mention} just posted an intro!", embed=welcome_embed)

bonusworthy_emoji_matches = None

async def handle_react_xp(reaction:discord.Reaction, user:discord.User):
  # Check if this user has already reacted to this message with this emoji
  blocked_channel_ids = get_channel_ids_list(config["handlers"]["xp"]["blocked_channels"])
  if reaction.message.author.bot or user.bot \
    or user.id is reaction.message.author.id \
    or reaction.message.channel.id in blocked_channel_ids:
    return

  global current_color

  reaction_already_counted = await check_react_history(reaction, user)
  if reaction_already_counted:
    return

  # Grant Standard XP for both User and Author
  await log_react_history(reaction, user)
  await increment_user_xp(user, 1, "added_reaction", reaction.message.channel, reaction)
  await increment_user_xp(reaction.message.author, 1, "got_single_reaction", reaction.message.channel, reaction)

  # Now give the Author some additional bonus XP if they've made a particularly reaction-worthy message!

  global bonusworthy_emoji_matches
  if bonusworthy_emoji_matches is None:
    # Check against general starboard inclusion for bonus XP as well
    starboard_dict = config["handlers"]["starboard"]["boards"].copy()
    # Get list of relevant bonus emoji from config
    starboard_dict['bonusworth_emoji'] = config["handlers"]["xp"]["bonusworthy_emoji"]
    # Get the precompiled regexps
    from handlers.starboard import generate_board_compiled_patterns
    starboard_emoji_matches = generate_board_compiled_patterns(starboard_dict).values()
    bonusworthy_emoji_matches = [match for sublist in starboard_emoji_matches for match in sublist]

  if hasattr(reaction.emoji, "name"):
    # if its a real emoji and has one of our words or matches exactly
    for match in bonusworthy_emoji_matches:
      if match.search(reaction.emoji.name.lower()) is not None:
        xp_amt = 0

        if 5 <= reaction.count < 10:
          xp_amt = 1
        if 10 <= reaction.count < 20:
          xp_amt = 2
        if reaction.count >= 20:
          xp_amt = 5
        if xp_amt > 0:
          await increment_user_xp(reaction.message.author, xp_amt, "got_reactions", reaction.message.channel, reaction)

        break

async def handle_event_creation_xp(event):
  creator = await bot.fetch_user(event.creator_id)
  location = event.location.value
  if type(location) == str:
    # Users might create an event that isn't a VoiceChannel
    return
  await increment_user_xp(creator, 45, "created_event", location, event)

# calculate_xp_for_next_level(current_level)
# current_level[required]: int
# returns the amount of xp required to level up for the given level
def calculate_xp_for_next_level(current_level:int):
  return int( (current_level*69) + (current_level * current_level) - 1)

# util function for debug - shows an XP chart like D&D
def show_list_of_levels():
  level_chart = ""
  previous_xp_amt = 0
  for i in range(101):
    xp_required = calculate_xp_for_next_level(i)
    amt_diff = xp_required - previous_xp_amt
    previous_xp_amt = xp_required
    level_chart += f"{i} - {xp_required} - ({amt_diff})\n"
  logger.info(level_chart)

# Entry point: triggered from increment_user_xp
async def level_up_user(user: discord.User, source_details: str):
  user_xp_data = await get_user_xp(user.id)
  level = user_xp_data["level"] + 1

  _log_level_up_to_console(user, level)

  async with AgimusDB() as query:
    await query.execute("UPDATE users SET level = level + 1 WHERE discord_id = %s", (user.id,))

  badge = await _award_level_up_badge(user.id)
  await _send_level_up_embed(user, level, badge, source_details)

def _log_level_up_to_console(user, level):
  rainbow_l = f"{Back.RESET}{Back.RED} {Back.YELLOW} {Back.GREEN} {Back.CYAN} {Back.BLUE} {Back.MAGENTA} {Back.RESET}"
  rainbow_r = f"{Back.RESET}{Back.MAGENTA} {Back.BLUE} {Back.CYAN} {Back.GREEN} {Back.YELLOW} {Back.RED} {Back.RESET}"
  logger.info(f"{rainbow_l} {Style.BRIGHT}{user.display_name}{Style.RESET_ALL} reached level {level}! {rainbow_r}")

async def _award_level_up_badge(user_id):
  badge = await give_user_badge(user_id)

  if badge:
    wishlist_badges = await db_get_user_wishlist_badges(user_id)
    was_on_wishlist = badge in [b['badge_filename'] for b in wishlist_badges]
    await db_autolock_badges_by_filenames_if_in_wishlist(user_id, [badge])
    await db_purge_users_wishlist(user_id)
    return { "filename": badge, "was_on_wishlist": was_on_wishlist }

  # No standard badge awarded — attempt shiny badge fallback
  return await potentially_award_shiny_badge(user_id)

async def _send_level_up_embed(user, level, badge_data, source_details):
  channel = bot.get_channel(get_channel_id(config["handlers"]["xp"]["notification_channel"]))
  msg = f"**{random.choice(random_level_up_messages['messages']).format(user=user.mention, level=level, prev_level=(level-1))}**"
  embed_title = "Level up!"
  thumbnail = random.choice(config["handlers"]["xp"]["celebration_images"])

  if badge_data is None:
    desc = f"{user.mention} reached **Level {level}**!\n\nBUT they've already collected ***ALL BADGES***! 🎉"
    embed = discord.Embed(title=embed_title, description=desc, color=discord.Color.random())
    embed.set_image(url="https://i.imgur.com/x9PjPT3.gif")
    embed.set_footer(text="See all your badges with '/badges showcase' or hide with '/settings'")
    embed.add_field(name='Level Up Source', value=source_details)
    await channel.send(content=msg, embed=embed)
    return

  filename = badge_data["filename"]
  was_on_wishlist = badge_data["was_on_wishlist"]
  desc = f"{user.mention} reached **Level {level}** and earned a new badge!"
  if level == 2:
    desc += "\n\nCheck out your full badge list with `/badges showcase`."
  if was_on_wishlist:
    desc += f"\n\nIt was also on their **wishlist**! {get_emoji('picard_yes_happy_celebrate')}"

  fields = []
  if source_details:
    fields.append({ 'name': "Level Up Source", 'value': source_details })

  await send_badge_reward_message(msg, desc, embed_title, channel, thumbnail, filename, user, fields)

# --- Section 3: XP Increment Logic ---
async def increment_user_xp(user: discord.User, amt: int, reason: str, channel, source=None):
  async with xp_lock:
    xp_multiplier = 2 if datetime.today().weekday() >= 4 else 1
    amt = int(amt * xp_multiplier)

    async with AgimusDB() as query:
      sql = "UPDATE users SET xp = xp + %s, name = %s WHERE discord_id = %s AND xp_enabled = 1"
      vals = (amt, user.display_name, user.id)
      await query.execute(sql, vals)
      updated = query.rowcount

    if updated == 0:
      return

    await log_xp_history(user.id, amt, channel.id, reason)
    _console_log_xp_history(user, amt, reason)

    user_xp_data = await get_user_xp(user.id)
    current_xp = user_xp_data["xp"]
    current_level = user_xp_data["level"]

    should_level = False

    if current_level >= 176:
      cap_progress = await get_xp_cap_progress(user.id)
      if cap_progress is None:
        next_xp = calculate_xp_for_next_level(current_level)
        if current_xp >= next_xp:
          should_level = True
          await init_xp_cap_progress(user.id, current_xp - next_xp)
      else:
        await increment_xp_cap_progress(user.id, amt)
        if cap_progress + amt >= 420:
          should_level = True
          await decrement_xp_cap_progress(user.id, 420)
    else:
      next_xp = calculate_xp_for_next_level(current_level)
      if current_xp >= next_xp:
        should_level = True

    if should_level:
      try:
        details = determine_level_up_source_details(user, source)
        await level_up_user(user, details)
      except Exception as e:
        logger.warning(f"Level-up error: {e}")
        logger.error(traceback.format_exc())

# UTILS
def _console_log_xp_history(user: discord.User, amt: int, reason: str):
  global current_color
  msg_color = xp_colors[current_color]
  reason_text = reasons.get(reason, reason)
  star = f"{msg_color}{Style.BRIGHT}*{Style.NORMAL}{Fore.RESET}"
  logger.info(f"{star} {msg_color}{user.display_name}{Fore.RESET} earns {msg_color}{amt} XP{Fore.RESET} for {Style.BRIGHT}{reason_text}{Style.RESET_ALL}! {star}")
  current_color = (current_color + 1) % len(xp_colors)

async def potentially_award_shiny_badge(user_id):
  user_badges = await db_get_user_badges(user_id)
  if not user_badges:
    logger.warning(f"User {user_id} has no badges—unexpected state when attempting shiny award.")
    return None

  standard_badges = [b for b in user_badges if b.get("shiny_level", 0) == 0]
  base_badge = standard_badges[0]  # Use first badge as the shiny base
  base_filename = base_badge["badge_filename"]
  shiny_filename = base_filename.replace(".png", "_shiny_1.png")

  await generate_shiny_badge_image(base_filename, shiny_filename)
  await insert_shiny_badge_info(base_badge, shiny_filename, shiny_level=1)

  async with AgimusDB() as query:
    sql = "INSERT INTO badges (user_discord_id, badge_filename) VALUES (%s, %s)"
    vals = (user_id, shiny_filename)
    await query.execute(sql, vals)

  return { "filename": shiny_filename, "was_on_wishlist": False }

def determine_level_up_source_details(user, source):
  if isinstance(source, discord.message.Message):
    if is_message_channel_unblocked(source):
      return f"Their message at: {source.jump_url}"
    else:
      return random.choice(blocked_level_up_sources)
  elif isinstance(source, discord.Reaction):
    if is_message_channel_unblocked(source.message):
      if user is source.message.author:
        return f"Receiving a {source.emoji} react on their message at: {source.message.jump_url}"
      else:
        return f"Adding a {source.emoji} react to the message at: {source.message.jump_url}"
    else:
      return random.choice(blocked_level_up_sources)
  elif isinstance(source, discord.ScheduledEvent):
    return f"Scheduing the `{source.name}` event"
  elif isinstance(source, str):
    return source

def is_message_channel_unblocked(message: discord.message.Message):
  # Use starboard blocked channel list to verify whether we should be reporting the source
  blocked_channels = get_channel_ids_list(config["handlers"]["starboard"]["blocked_channels"])

  if isinstance(message.channel, discord.Thread):
    return message.channel.parent.id not in blocked_channels
  if isinstance(message.channel, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel)):
    return message.channel.id not in blocked_channels

  return False

# Utils
async def give_welcome_badge(user_id):
  user_badge_filenames = [b['badge_filename'] for b in await db_get_user_badges(user_id)]
  if "Friends_Of_DeSoto.png" not in user_badge_filenames:
    async with AgimusDB() as query:
      sql = "INSERT INTO badges (user_discord_id, badge_filename) VALUES (%s, 'Friends_Of_DeSoto.png');"
      vals = (user_id,)
      await query.execute(sql, vals)

# Database Utils
async def get_user_xp(discord_id):
  async with AgimusDB() as query:
    sql = "SELECT level, xp FROM users WHERE discord_id = %s"
    vals = (discord_id,)
    await query.execute(sql, vals)
    user_xp = await query.fetchone()
  return { "level": user_xp[0], "xp" : user_xp[1] }

async def check_react_history(reaction:discord.Reaction, user:discord.User):
  async with AgimusDB() as query:
    sql = "SELECT id FROM reactions WHERE user_id = %s AND reaction = %s AND reaction_message_id = %s"
    vals = (user.id, f"{reaction}", reaction.message.id)
    await query.execute(sql, vals)
    reaction_exists = await query.fetchone()
  return reaction_exists

async def log_react_history(reaction:discord.Reaction, user:discord.User):
  async with AgimusDB() as query:
    sql = "INSERT INTO reactions (user_id, user_name, reaction, reaction_message_id) VALUES (%s, %s, %s, %s)"
    vals = (user.id, user.display_name, f"{reaction}", reaction.message.id)
    await query.execute(sql, vals)

async def log_xp_history(user_discord_id:int, amt:int, channel_id:int, reason:str):
  async with AgimusDB() as query:
    sql = "INSERT INTO xp_history (user_discord_id, amount, channel_id, reason) VALUES (%s, %s, %s, %s)"
    vals = (user_discord_id, amt, channel_id, reason)
    await query.execute(sql, vals)

async def get_xp_cap_progress(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT progress FROM xp_cap_progress WHERE user_discord_id = %s"
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    result = await query.fetchone()
  if result is not None:
    return result.get('progress')
  else:
    return result

async def init_xp_cap_progress(user_discord_id, amount):
  async with AgimusDB() as query:
    sql = "INSERT INTO xp_cap_progress (user_discord_id, progress) VALUES (%s, %s)"
    vals = (user_discord_id, amount)
    await query.execute(sql, vals)

async def increment_xp_cap_progress(user_discord_id, amount):
  async with AgimusDB() as query:
    sql = "UPDATE xp_cap_progress SET progress = progress + %s WHERE user_discord_id = %s"
    vals = (amount, user_discord_id)
    await query.execute(sql, vals)

async def decrement_xp_cap_progress(user_discord_id, amount):
  async with AgimusDB() as query:
    sql = "UPDATE xp_cap_progress SET progress = progress - %s WHERE user_discord_id = %s"
    vals = (amount, user_discord_id)
    await query.execute(sql, vals)
