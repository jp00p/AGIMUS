# handlers/auto_promotions.py
from common import *
from handlers.eschelon_xp import award_xp, get_user_eschelon_progress
from queries.badge_instances import db_get_user_badge_instances
from queries.crystal_instances import db_set_user_crystal_buffer
from utils.badge_instances import create_new_badge_instance_by_filename


# _________                         __                 __
# \_   ___ \  ____   ____   _______/  |______    _____/  |_  ______
# /    \  \/ /  _ \ /    \ /  ___/\   __\__  \  /    \   __\/  ___/
# \     \___(  <_> )   |  \\___ \  |  |  / __ \|   |  \  |  \___ \
#  \______  /\____/|___|  /____  > |__| (____  /___|  /__| /____  >
#         \/            \/     \/            \/     \/          \/
promotion_roles = config["roles"]["promotion_roles"]["ranks"]
required_rank_xp = config["roles"]["promotion_roles"]["required_rank_xp"]

usher_messages = config["handlers"]["xp"]["usher_messages"]
welcome_images = config["handlers"]["xp"]["welcome_images"]


#   ___ ___                    .___.__
#  /   |   \_____    ____    __| _/|  |   ___________  ______
# /    ~    \__  \  /    \  / __ | |  | _/ __ \_  __ \/  ___/
# \    Y    // __ \|   |  \/ /_/ | |  |_\  ___/|  | \/\___ \
#  \___|_  /(____  /___|  /\____ | |____/\___  >__|  /____  >
#        \/      \/     \/      \/           \/           \/
async def handle_auto_promotions(message: discord.Message, xp_amt: int):
  if message.guild is None or message.author.bot:
    return

  member = message.author

  if await should_skip_promotions(member):
    return

  await handle_intro_promotion(message)
  await handle_xp_promotion(member)


async def should_skip_promotions(member: discord.Member) -> bool:
  """Early exit if user already has Cadet or Ensign role."""
  member_role_names = [r.name for r in member.roles]
  return promotion_roles["cadet"] in member_role_names and promotion_roles["ensign"] in member_role_names


async def handle_intro_promotion(message: discord.Message):
  intro_channel_id = get_channel_id(config["intro_channel"])
  if message.channel.id != intro_channel_id:
    return

  member = message.author
  member_role_names = [r.name for r in member.roles]

  # Find first-ever message by this user
  first_message = await find_first_server_message(member)

  if not first_message:
    return  # Shouldn't happen, but safe fallback

  if first_message.channel.id == intro_channel_id:
    await post_big_welcome_embed(member, first_message)
  else:
    await post_small_already_seen_embed(member, first_message)

  # Promotion to Cadet if appropriate
  if promotion_roles["cadet"] not in member_role_names:
    cadet_role = discord.utils.get(message.guild.roles, name=promotion_roles["cadet"])
    if cadet_role:
      await member.add_roles(cadet_role)
      logger.info(f"{Style.BRIGHT}{member.display_name}{Style.RESET_ALL} promoted to {Fore.CYAN}Cadet{Fore.RESET} via intro message!")
      await grant_xp(member.id, 10, "intro_message", channel=message.channel, source="Posted their intro message!")
      await grant_initial_welcome_rewards(member)


async def handle_xp_promotion(member: discord.Member):
  user_id = member.id
  xp_data = await get_user_eschelon_progress(user_id)
  user_level = xp_data["current_level"] if xp_data else 1

  member_role_names = [r.name for r in member.roles]

  if promotion_roles["cadet"] not in member_role_names and user_level >= required_rank_xp["cadet"]:
    cadet_role = discord.utils.get(member.guild.roles, name=promotion_roles["cadet"])
    if cadet_role:
      await member.add_roles(cadet_role)
      logger.info(f"{Style.BRIGHT}{member.display_name}{Style.RESET_ALL} promoted to {Fore.CYAN}Cadet{Fore.RESET} via XP!")
      await grant_initial_welcome_rewards(member)

  elif promotion_roles["ensign"] not in member_role_names and user_level >= required_rank_xp["ensign"]:
    ensign_role = discord.utils.get(member.guild.roles, name=promotion_roles["ensign"])
    if ensign_role:
      await member.add_roles(ensign_role)
      logger.info(f"{Style.BRIGHT}{member.display_name}{Style.RESET_ALL} promoted to {Fore.GREEN}Ensign{Fore.RESET} via XP!")


# __________                                .___
# \______   \ ______  _  _______ _______  __| _/______
#  |       _// __ \ \/ \/ /\__  \\_  __ \/ __ |/  ___/
#  |    |   \  ___/\     /  / __ \|  | \/ /_/ |\___ \
#  |____|_  /\___  >\/\_/  (____  /__|  \____ /____  >
#         \/     \/             \/           \/    \/
async def grant_initial_welcome_rewards(member: discord.Member):
  user_id = str(member.id)
  badges = await db_get_user_badge_instances(user_id)
  badge_filenames = [b["badge_filename"] for b in badges]

  # Standard Friends of DeSoto Badge reward
  if "Friends_Of_DeSoto.png" not in badge_filenames:
    await create_new_badge_instance_by_filename(user_id, "Friends_Of_DeSoto.png", event_type="first_promotion")

  # Give em 3 crystal buffers to play with
  await db_set_user_crystal_buffer(user_id, 3)


# ___________      ___.              .___
# \_   _____/ _____\_ |__   ____   __| _/______
#  |    __)_ /     \| __ \_/ __ \ / __ |/  ___/
#  |        \  Y Y  \ \_\ \  ___// /_/ |\___ \
# /_______  /__|_|  /___  /\___  >____ /____  >
#         \/      \/    \/     \/     \/    \/
async def post_big_welcome_embed(member: discord.Member, first_message: discord.Message):
  """Send the full 'brand new crewmember' welcome embed."""
  ten_forward_channel_id = get_channel_id(config["channels"]["ten-forward"])
  channel_guide_id = get_channel_id(config["channels"]["channel-guide"])
  roles_and_pronouns_id = get_channel_id(config["channels"]["roles-and-pronouns"])
  animal_holophotography_id = get_channel_id(config["channels"]["animal-holophotography"])
  welcome_channel_id = get_channel_id(config["welcome_channel"])

  embed = discord.Embed(
    title=f"Could someone {random.choice(usher_messages)}?",
    color=discord.Color.random(),
    description=f"Please greet our new crewmember in <#{ten_forward_channel_id}>!"
  )

  embed.set_image(url=random.choice(welcome_images))

  embed.add_field(name=f"Offer advice {get_emoji('pakled_smart_lol')}",
    value=f"Recommend <#{channel_guide_id}> and <#{roles_and_pronouns_id}>.", inline=False)
  embed.add_field(name=f"Read their intro {get_emoji('bashir_zoom_look_huh')}",
    value=f"Personalize your greeting based on their intro: {first_message.jump_url}", inline=False)
  embed.add_field(name=f"Bring them in {get_emoji('kira_good_morning_hello')}",
    value=f"Suggest <#{animal_holophotography_id}> to start!", inline=False)

  embed.set_footer(text="Thank you officers! 💖")
  welcome_channel = bot.get_channel(welcome_channel_id)
  await welcome_channel.send(content=f"## @here — {member.mention} just posted their introduction!", embed=embed)

async def post_small_already_seen_embed(member: discord.Member, first_message: discord.Message):
  """Send a smaller notification if they've already been seen elsewhere."""
  intro_channel_id = get_channel_id(config["intro_channel"])
  welcome_channel_id = get_channel_id(config["welcome_channel"])
  embed = discord.Embed(
    title=f"{member.display_name} just posted in {member.guild.get_channel(intro_channel_id).mention}!",
    description=f"👀 They've already been seen elsewhere on the server though.\nFirst post: [Jump to Message]({first_message.jump_url})",
    color=discord.Color.light_grey()
  )
  embed.set_footer(text=f"First post was on {first_message.created_at.strftime('%b %d, %Y at %H:%M UTC')}")
  welcome_channel = bot.get_channel(welcome_channel_id)
  await welcome_channel.send(content=f"## @here — {member.mention} just posted their introduction!", embed=embed)

# --- Section 6: Utilities ---

async def find_first_server_message(member: discord.Member) -> discord.Message | None:
  """Find the first message ever posted by this user anywhere in the server."""
  for channel in member.guild.text_channels:
    try:
      async for msg in channel.history(limit=None, oldest_first=True):
        if msg.author.id == member.id:
          return msg
    except (discord.Forbidden, discord.HTTPException):
      continue  # Skip channels we can't access
  return None
