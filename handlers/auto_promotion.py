# handlers/auto_promotion.py
from common import *
from handlers.echelon_xp import get_user_echelon_progress
from handlers.echelon_xp import award_xp

promotion_roles = config['roles']['promotion_roles']['ranks']
required_rank_xp = config['roles']['promotion_roles']['required_rank_xp']

usher_messages = config['handlers']['xp']['usher_messages']
welcome_images = config['handlers']['xp']['welcome_images']


async def handle_auto_promotions(message: discord.Message):
  member = message.author
  if message.guild is None or member.bot:
    return

  if await should_skip_promotions(member):
    return

  await handle_intro_promotion(message)
  await handle_xp_promotion(member)


async def should_skip_promotions(member: discord.Member) -> bool:
  """Early exit if user already has Cadet and Ensign roles."""
  member_role_names = [r.name for r in member.roles]
  return (
    promotion_roles['cadet'] in member_role_names
    and promotion_roles['ensign'] in member_role_names
  )


async def handle_intro_promotion(message: discord.Message):
  intro_channel_id = get_channel_id(config['intro_channel'])
  if message.channel.id != intro_channel_id:
    return

  member = message.author
  member_role_names = [r.name for r in member.roles]

  first_intro_message = await find_first_intro_message(message.channel, member.id)
  if not first_intro_message:
    return

  is_first_intro_post = first_intro_message.id == message.id

  if is_first_intro_post:
    first_message = await find_first_server_message(member)
    if not first_message:
      return

    if first_message.channel.id == intro_channel_id:
      await post_big_welcome_embed(member, first_message)
    else:
      await post_small_already_seen_embed(member, first_message)

  # Ensign should be granted for posting in intro at any time.
  if promotion_roles['ensign'] not in member_role_names:
    ensign_role = discord.utils.get(message.guild.roles, name=promotion_roles['ensign'])
    if ensign_role:
      await member.add_roles(ensign_role)
      logger.info(
        f'{Style.BRIGHT}{member.display_name}{Style.RESET_ALL} promoted to {Fore.GREEN}Ensign{Fore.RESET} via intro message!'
      )
      member_role_names.append(promotion_roles['ensign'])

  # Cadet can also be granted here if missing.
  if promotion_roles['cadet'] not in member_role_names:
    cadet_role = discord.utils.get(message.guild.roles, name=promotion_roles['cadet'])
    if cadet_role:
      await member.add_roles(cadet_role)
      logger.info(
        f'{Style.BRIGHT}{member.display_name}{Style.RESET_ALL} promoted to {Fore.CYAN}Cadet{Fore.RESET} via intro message!'
      )
      member_role_names.append(promotion_roles['cadet'])
      await award_xp(message.author, 10, 'intro_message', message.channel)


async def find_first_intro_message(
  intro_channel: discord.TextChannel | discord.Thread,
  user_id: int
) -> discord.Message | None:
  """
  Find the first message posted by a user in the intro channel.
  This is used to ensure the mod notification embed only triggers once.
  """
  try:
    async for msg in intro_channel.history(limit=None, oldest_first=True):
      if msg.author and msg.author.id == user_id:
        return msg
  except (discord.Forbidden, discord.HTTPException):
    return None

  return None


async def handle_xp_promotion(member: discord.Member):
  user_id = str(member.id)
  xp_data = await get_user_echelon_progress(user_id)

  member_role_names = [r.name for r in member.roles]

  current_xp = xp_data['current_xp'] if xp_data else 0
  current_level = xp_data['current_level'] if xp_data else 1

  has_any_xp = current_level > 1 or current_xp > 0
  has_ensign_xp = current_level > 1 or current_xp >= 15

  # Cadet: first XP anywhere.
  if promotion_roles['cadet'] not in member_role_names and has_any_xp:
    cadet_role = discord.utils.get(member.guild.roles, name=promotion_roles['cadet'])
    if cadet_role:
      await member.add_roles(cadet_role)
      logger.info(
        f'{Style.BRIGHT}{member.display_name}{Style.RESET_ALL} promoted to {Fore.CYAN}Cadet{Fore.RESET} via first XP!'
      )
      member_role_names.append(promotion_roles['cadet'])

  # Ensign: >= 15xp (hard-coded) via XP.
  if promotion_roles['ensign'] not in member_role_names and has_ensign_xp:
    ensign_role = discord.utils.get(member.guild.roles, name=promotion_roles['ensign'])
    if ensign_role:
      await member.add_roles(ensign_role)
      logger.info(
        f'{Style.BRIGHT}{member.display_name}{Style.RESET_ALL} promoted to {Fore.GREEN}Ensign{Fore.RESET} via XP (>= 15)!'
      )


async def post_big_welcome_embed(member: discord.Member, first_message: discord.Message):
  ten_forward_channel_id = get_channel_id(config['channels']['ten-forward'])
  channel_guide_id = get_channel_id(config['channels']['channel-guide'])
  roles_and_pronouns_id = get_channel_id(config['channels']['roles-and-pronouns'])
  animal_holophotography_id = get_channel_id(config['channels']['animal-holophotography'])
  welcome_channel_id = get_channel_id(config['welcome_channel'])

  embed = discord.Embed(
    title=f'Could someone {random.choice(usher_messages)}?',
    color=discord.Color.random(),
    description=f'Please greet our new crewmember in <#{ten_forward_channel_id}>!'
  )

  embed.set_image(url=random.choice(welcome_images))

  embed.add_field(
    name=f'Offer advice {get_emoji("pakled_smart_lol")}',
    value=f'Recommend <#{channel_guide_id}> and <#{roles_and_pronouns_id}>.',
    inline=False
  )
  embed.add_field(
    name=f'Read their intro {get_emoji("bashir_zoom_look_huh")}',
    value=f'Personalize your greeting based on their intro: {first_message.jump_url}',
    inline=False
  )
  embed.add_field(
    name=f'Bring them in {get_emoji("kira_good_morning_hello")}',
    value=f'Suggest <#{animal_holophotography_id}> to start!',
    inline=False
  )

  embed.set_footer(text='Thank you officers! 💖')
  welcome_channel = bot.get_channel(welcome_channel_id)
  await welcome_channel.send(
    content=f'## @here - {member.mention} just posted their introduction!',
    embed=embed
  )


async def post_small_already_seen_embed(member: discord.Member, first_message: discord.Message):
  intro_channel_id = get_channel_id(config['intro_channel'])
  welcome_channel_id = get_channel_id(config['welcome_channel'])
  embed = discord.Embed(
    title=f'{member.display_name} just posted in {member.guild.get_channel(intro_channel_id).mention}!',
    description=f"They've already been seen elsewhere on the server though.\nFirst post: [Jump to Message]({first_message.jump_url})",
    color=discord.Color.light_grey()
  )
  embed.set_footer(text=f'First post was on {first_message.created_at.strftime("%b %d, %Y at %H:%M UTC")}')
  welcome_channel = bot.get_channel(welcome_channel_id)
  await welcome_channel.send(
    content=f'## @here - {member.mention} just posted their introduction!',
    embed=embed
  )


async def find_first_server_message(member: discord.Member) -> discord.Message | None:
  """Find the first message ever posted by this user anywhere in the server."""
  for channel in member.guild.text_channels:
    try:
      async for msg in channel.history(limit=None, oldest_first=True):
        if msg.author.id == member.id:
          return msg
    except (discord.Forbidden, discord.HTTPException):
      continue
  return None
