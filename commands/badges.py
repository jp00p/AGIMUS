import textwrap
import time
import math

from common import *
from utils.badge_utils import *
from utils.check_channel_access import access_check


f = open(config["handlers"]["xp"]["badge_data"])
badge_data = json.loads(f.read())
f.close()

#    _____          __                                     .__          __
#   /  _  \  __ ___/  |_  ____   ____  ____   _____ ______ |  |   _____/  |_  ____
#  /  /_\  \|  |  \   __\/  _ \_/ ___\/  _ \ /     \\____ \|  | _/ __ \   __\/ __ \
# /    |    \  |  /|  | (  <_> )  \__(  <_> )  Y Y  \  |_> >  |_\  ___/|  | \  ___/
# \____|__  /____/ |__|  \____/ \___  >____/|__|_|  /   __/|____/\___  >__|  \___  >
#         \/                        \/            \/|__|             \/          \/

async def all_badges_autocomplete(ctx:discord.AutocompleteContext):
  all_badges = [key.replace('_', ' ').replace('.png', '') for key in badge_data.keys()]
  return [badge for badge in all_badges if ctx.value.lower() in badge.lower()]

async def autocomplete_selections(ctx:discord.AutocompleteContext):
  category = ctx.options["category"]

  selections = []

  if category == 'affiliation':
    selections = db_get_all_affiliations()
  elif category == 'franchise':
    selections = db_get_all_franchises()
  elif category == 'time_period':
    selections = db_get_all_time_periods()
  elif category == 'type':
    selections = db_get_all_types()

  return [result for result in selections if ctx.value.lower() in result.lower()]

badge_group = bot.create_group("badges", "Badge Commands!")

#   _________.__
#  /   _____/|  |__   ______  _  __ ____ _____    ______ ____
#  \_____  \ |  |  \ /  _ \ \/ \/ // ___\\__  \  /  ___// __ \
#  /        \|   Y  (  <_> )     /\  \___ / __ \_\___ \\  ___/
# /_______  /|___|  /\____/ \/\_/  \___  >____  /____  >\___  >
#         \/      \/                   \/     \/     \/     \/
@badge_group.command(
  name="showcase",
  description="Show off all your badges! Please be mindful of posting very large collections publicly."
)
@option(
  name="public",
  description="Show to public?",
  required=True,
  choices=[
    discord.OptionChoice(
      name="No",
      value="no"
    ),
    discord.OptionChoice(
      name="Yes",
      value="yes"
    )
  ]
)
@option(
  name="color",
  description="Which colorscheme would you like?",
  required=False,
  choices = [
    discord.OptionChoice(name=color_choice, value=color_choice.lower())
    for color_choice in ["Green", "Orange", "Purple", "Teal"]
  ]
)
async def showcase(ctx:discord.ApplicationContext, public:str, color:str):
  public = bool(public == "yes")
  await ctx.defer(ephemeral=not public)

  badges = os.listdir("./images/badges/")
  all_badges = db_get_user_badges(ctx.author.id)

  # Set up text values for paginated pages
  total_badges = len(badges)
  title = f"{ctx.author.display_name.encode('ascii', errors='ignore').decode().strip()}'s Badge Collection"
  collected = f"{len(all_badges)} TOTAL ON THE USS HOOD"
  filename_prefix = f"badge_list_{ctx.author.id}-page-"

  if color:
    db_set_user_badge_page_color_preference(ctx.author.id, "showcase", color)
  badge_images = await generate_paginated_badge_images(ctx.author, 'showcase', all_badges, total_badges, title, collected, filename_prefix)

  embed = discord.Embed(
    title=f"Badge Collection",
    description=f"{ctx.author.mention} has collected {len(all_badges)} of {len(badges)}!",
    color=discord.Color.blurple()
  )

  # If we're doing a public display, use the images directly
  # Otherwise private displays can use the paginator
  if not public:
    buttons = [
      pages.PaginatorButton("prev", label="   ⬅   ", style=discord.ButtonStyle.primary, disabled=bool(len(all_badges) <= 30), row=1),
      pages.PaginatorButton(
        "page_indicator", style=discord.ButtonStyle.gray, disabled=True, row=1
      ),
      pages.PaginatorButton("next", label="   ➡   ", style=discord.ButtonStyle.primary, disabled=bool(len(all_badges) <= 30), row=1),
    ]

    set_pages = [
      pages.Page(files=[image], embeds=[embed])
      for image in badge_images
    ]
    paginator = pages.Paginator(
        pages=set_pages,
        show_disabled=True,
        show_indicator=True,
        use_default_buttons=False,
        custom_buttons=buttons,
        loop_pages=True
    )
    await paginator.respond(ctx.interaction, ephemeral=True)
  else:
    # We can only attach up to 10 files per message, so if it's public send them in chunks
    file_chunks = [badge_images[i:i + 10] for i in range(0, len(badge_images), 10)]
    for chunk_index, chunk in enumerate(file_chunks):
      # Only post the embed on the last chunk
      if chunk_index + 1 == len(file_chunks):
        await ctx.followup.send(embed=embed, files=chunk, ephemeral=not public)
      else:
        await ctx.followup.send(files=chunk, ephemeral=not public)


#   _________       __
#  /   _____/ _____/  |_  ______
#  \_____  \_/ __ \   __\/  ___/
#  /        \  ___/|  |  \___ \
# /_______  /\___  >__| /____  >
#         \/     \/          \/
@badge_group.command(
  name="sets",
  description="Show off sets of your badges! Please be mindful of posting very large sets publicly."
)
@option(
  name="public",
  description="Show to public?",
  required=True,
  choices=[
    discord.OptionChoice(
      name="No",
      value="no"
    ),
    discord.OptionChoice(
      name="Yes",
      value="yes"
    )
  ]
)
@option(
  name="category",
  description="Which category of set?",
  required=True,
  choices=[
    discord.OptionChoice(
      name="Affiliation",
      value="affiliation"
    ),
    discord.OptionChoice(
      name="Franchise",
      value="franchise"
    ),
    discord.OptionChoice(
      name="Time Period",
      value="time_period"
    ),
    discord.OptionChoice(
      name="Type",
      value="type"
    )
  ]
)
@option(
  name="selection",
  description="Which one?",
  required=True,
  autocomplete=autocomplete_selections
)
@option(
  name="color",
  description="Which colorscheme would you like?",
  required=False,
  choices = [
    discord.OptionChoice(name=color_choice, value=color_choice.lower())
    for color_choice in ["Green", "Orange", "Purple", "Teal"]
  ]
)
@commands.check(access_check)
async def sets(ctx:discord.ApplicationContext, public:str, category:str, selection:str, color:str):
  public = bool(public == "yes")
  await ctx.defer(ephemeral=not public)

  user_set_badges = []
  all_set_badges = []

  if category == 'affiliation':
    affiliations = db_get_all_affiliations()
    if selection not in affiliations:
      await ctx.followup.send("Your entry was not in the list of Affiliations!", ephemeral=True)
      return

    user_set_badges = db_get_badges_user_has_from_affiliation(ctx.author.id, selection)
    all_set_badges = db_get_all_affiliation_badges(selection)

  elif category == 'franchise':
    franchises = db_get_all_franchises()
    if selection not in franchises:
      await ctx.followup.send("Your entry was not in the list of Franchises!", ephemeral=True)
      return

    user_set_badges = db_get_badges_user_has_from_franchise(ctx.author.id, selection)
    all_set_badges = db_get_all_franchise_badges(selection)

  elif category == 'time_period':
    time_periods = db_get_all_time_periods()
    if selection not in time_periods:
      await ctx.followup.send("Your entry was not in the list of Time Periods!", ephemeral=True)
      return

    user_set_badges = db_get_badges_user_has_from_time_period(ctx.author.id, selection)
    all_set_badges = db_get_all_time_period_badges(selection)

  elif category == 'type':
    types = db_get_all_types()
    if selection not in types:
      await ctx.followup.send("Your entry was not in the list of Types!", ephemeral=True)
      return

    user_set_badges = db_get_badges_user_has_from_type(ctx.author.id, selection)
    all_set_badges = db_get_all_type_badges(selection)


  all_badges = []
  for badge in all_set_badges:
    badge_filename = badge.replace(" ", "_").replace("/", "-").replace(":", "-")
    record = {
      'badge_name': badge,
      'badge_filename': f"{badge_filename}.png",
      'in_user_collection': badge in user_set_badges
    }
    all_badges.append(record)

  category_title = category.replace("_", " ").title()

  total_badges = db_get_badge_count_for_user(ctx.author.id)

  # Set up text values for paginated pages
  title = f"{ctx.author.display_name.encode('ascii', errors='ignore').decode().strip()}'s Badge Set: {category_title} - {selection}"
  collected = f"{len([b for b in all_badges if b['in_user_collection']])} OF {len(all_set_badges)}"
  filename_prefix = f"badge_set_{ctx.author.id}_{selection.lower().replace(' ', '-').replace('/', '-')}-page-"

  if color:
    db_set_user_badge_page_color_preference(ctx.author.id, "sets", color)
  badge_images = await generate_paginated_badge_images(ctx.author, 'sets', all_badges, total_badges, title, collected, filename_prefix)

  embed = discord.Embed(
    title=f"Badge Set: **{category_title}** - **{selection}**",
    description=f"{ctx.author.mention} has collected {len(user_set_badges)} of {len(all_set_badges)}!",
    color=discord.Color.blurple()
  )

  # If we're doing a public display, use the images directly
  # Otherwise private displays can use the paginator
  if not public:
    buttons = [
      pages.PaginatorButton("prev", label="   ⬅   ", style=discord.ButtonStyle.primary, disabled=bool(len(all_badges) <= 30), row=1),
      pages.PaginatorButton(
        "page_indicator", style=discord.ButtonStyle.gray, disabled=True, row=1
      ),
      pages.PaginatorButton("next", label="   ➡   ", style=discord.ButtonStyle.primary, disabled=bool(len(all_badges) <= 30), row=1),
    ]

    set_pages = [
      pages.Page(files=[image], embeds=[embed])
      for image in badge_images
    ]
    paginator = pages.Paginator(
        pages=set_pages,
        show_disabled=True,
        show_indicator=True,
        use_default_buttons=False,
        custom_buttons=buttons,
        loop_pages=True
    )
    await paginator.respond(ctx.interaction, ephemeral=True)
  else:
    # We can only attach up to 10 files per message, so if it's public send them in chunks
    file_chunks = [badge_images[i:i + 10] for i in range(0, len(badge_images), 10)]
    for chunk_index, chunk in enumerate(file_chunks):
      # Only post the embed on the last chunk
      if chunk_index + 1 == len(file_chunks):
        await ctx.followup.send(embed=embed, files=chunk, ephemeral=not public)
      else:
        await ctx.followup.send(files=chunk, ephemeral=not public)


# _________                       .__          __  .__
# \_   ___ \  ____   _____ ______ |  |   _____/  |_|__| ____   ____
# /    \  \/ /  _ \ /     \\____ \|  | _/ __ \   __\  |/  _ \ /    \
# \     \___(  <_> )  Y Y  \  |_> >  |_\  ___/|  | |  (  <_> )   |  \
#  \______  /\____/|__|_|  /   __/|____/\___  >__| |__|\____/|___|  /
#         \/             \/|__|             \/                    \/
@badge_group.command(
  name="completion",
  description="Get a report of how close to completion you are on various sets."
)
@option(
  name="public",
  description="Show to public?",
  required=True,
  choices=[
    discord.OptionChoice(
      name="No",
      value="no"
    ),
    discord.OptionChoice(
      name="Yes",
      value="yes"
    )
  ]
)
@option(
  name="category",
  description="Which category of set?",
  required=True,
  choices=[
    discord.OptionChoice(
      name="Affiliation",
      value="affiliation"
    ),
    discord.OptionChoice(
      name="Franchise",
      value="franchise"
    ),
    discord.OptionChoice(
      name="Time Period",
      value="time_period"
    ),
    discord.OptionChoice(
      name="Type",
      value="type"
    )
  ]
)
@option(
  name="color",
  description="Which colorscheme would you like?",
  required=False,
  choices = [
    discord.OptionChoice(name=color_choice, value=color_choice.lower())
    for color_choice in ["Green", "Orange", "Purple", "Teal"]
  ]
)
async def completion(ctx:discord.ApplicationContext, public:str, category:str, color:str):
  public = bool(public == "yes")
  await ctx.defer(ephemeral=not public)

  all_badges = os.listdir("./images/badges/")
  user_badges = db_get_user_badges(ctx.author.id)

  all_rows = []
  if category == "affiliation":
    all_rows = db_get_set_completion_for_affiliations(ctx.author.id)
  if category == "franchise":
    all_rows = db_get_set_completion_for_franchises(ctx.author.id)
  if category == "time_period":
    all_rows = db_get_set_completion_for_time_periods(ctx.author.id)
  if category == "type":
    all_rows = db_get_set_completion_for_types(ctx.author.id)
  all_rows = _append_featured_completion_badges(ctx.author.id, all_rows, category)

  category_title = category.replace('_', ' ').title()

  total_badges = len(all_badges)
  title = f"{ctx.author.display_name.encode('ascii', errors='ignore').decode().strip()}'s Badge Completion - {category_title}"
  collected = f"{len(user_badges)} TOTAL ON THE USS HOOD"
  filename_prefix = f"badge_set_completion_{ctx.author.id}_affiliations-page-"

  if color:
    db_set_user_badge_page_color_preference(ctx.author.id, "sets", color)
  completion_images = await generate_paginated_set_completion_images(ctx.author, all_rows, total_badges, title, collected, filename_prefix)

  embed = discord.Embed(
    title=f"Badge Set Completion - {category_title}",
    description=f"{ctx.author.mention}'s Current Set Completion Progress",
    color=discord.Color.blurple()
  )

  # If we're doing a public display, use the images directly
  # Otherwise private displays can use the paginator
  if not public:
    buttons = [
      pages.PaginatorButton("prev", label="   ⬅   ", style=discord.ButtonStyle.primary, disabled=bool(len(all_rows) <= 7), row=1),
      pages.PaginatorButton(
        "page_indicator", style=discord.ButtonStyle.gray, disabled=True, row=1
      ),
      pages.PaginatorButton("next", label="   ➡   ", style=discord.ButtonStyle.primary, disabled=bool(len(all_rows) <= 7), row=1),
    ]

    set_pages = [
      pages.Page(files=[image], embeds=[embed])
      for image in completion_images
    ]
    paginator = pages.Paginator(
        pages=set_pages,
        show_disabled=True,
        show_indicator=True,
        use_default_buttons=False,
        custom_buttons=buttons,
        loop_pages=True
    )
    await paginator.respond(ctx.interaction, ephemeral=True)
  else:
    # We can only attach up to 10 files per message, so if it's public send them in chunks
    file_chunks = [completion_images[i:i + 10] for i in range(0, len(completion_images), 10)]
    for chunk_index, chunk in enumerate(file_chunks):
      # Only post the embed on the last chunk
      if chunk_index + 1 == len(file_chunks):
        await ctx.followup.send(embed=embed, files=chunk, ephemeral=not public)
      else:
        await ctx.followup.send(files=chunk, ephemeral=not public)

def _append_featured_completion_badges(user_id, report, category):
  for r in report:
    if category == "affiliation":
      badges = db_get_badge_filenames_user_has_from_affiliation(user_id, r['name'])
    elif category == "franchise":
      badges = db_get_badge_filenames_user_has_from_franchise(user_id, r['name'])
    elif category == "time_period":
      badges = db_get_badge_filenames_user_has_from_time_period(user_id, r['name'])
    if category == "type":
      badges = db_get_badge_filenames_user_has_from_type(user_id, r['name'])

    r['featured_badge'] = random.choice(badges)
  return report

#
#
# Lookup
#
#
@badge_group.command(
  name="lookup",
  description="Look up information about a specific badge"
)
@option(
  name="name",
  description="Which badge do you want to look up?",
  required=True,
  autocomplete=all_badges_autocomplete
)
async def badge_lookup(ctx:discord.ApplicationContext, name:str):
  """
  This function executes the lookup for the /badge lookup command
  :param ctx:
  :param name: The name of the badge to be looked up.
  :return:
  """
  try:
    logger.info(f"{Fore.CYAN}Firing /badge lookup command for '{name}'!{Fore.RESET}")
    badge = db_get_badge_info_by_name(name)
    if (badge):

      description = f"Quadrant: **{badge['quadrant']}**\n"
      description += f"Time Period: **{badge['time_period']}**\n"
      description += f"Franchise: **{badge['franchise']}**\n"
      description += f"Reference: **{badge['reference']}**\n"

      embed = discord.Embed(
        title=f"{badge['badge_name']}",
        description=description,
        color=discord.Color.random() # jp00p made me do it
      )
      discord_image = discord.File(fp=f"./images/badges/{badge['badge_filename']}", filename=badge['badge_filename'].replace(',','_'))
      embed.set_image(url=f"attachment://{badge['badge_filename'].replace(',','_')}")
      await ctx.send_response(embed=embed, file=discord_image, ephemeral=True)

    else:
      await ctx.respond("Could not find this badge.\n")
  except Exception as e:
    logger.info(f">>> ERROR: {e}")



#   _________ __          __  .__          __  .__
#  /   _____//  |______ _/  |_|__| _______/  |_|__| ____   ______
#  \_____  \\   __\__  \\   __\  |/  ___/\   __\  |/ ___\ /  ___/
#  /        \|  |  / __ \|  | |  |\___ \  |  | |  \  \___ \___ \
# /_______  /|__| (____  /__| |__/____  > |__| |__|\___  >____  >
#         \/           \/             \/               \/     \/
@badge_group.command(
  name="statistics",
  description="See the server-wide badge statistics"
)
async def badge_statistics(ctx:discord.ApplicationContext):
  """
  slash command to get common badge stats
  """
  emoji_numbers = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
  results = {}
  results = run_badge_stats_queries()
  total_badges = "".join(emoji_numbers[int(n)] for n in list(str(results['total_badges'][0]['count'])))
  badges_today = "".join(emoji_numbers[int(n)] for n in list(str(results['badges_today'][0]['count'])))
  top_collectors = [res for res in results["top_collectors"]]
  top_three = [res for res in results["most_collected"]]
  embed = discord.Embed(color=discord.Color.random(), description="", title="")
  embed.add_field(name=f"{get_emoji('combadge')} Total badges collected\non the USS Hood", value=f"{total_badges}\n⠀", inline=True)
  embed.add_field(name="⠀", value="⠀", inline=True)
  embed.add_field(name=f"{get_emoji('combadge')} Badges collected in\nthe last 24 hours", value=f"{badges_today}\n⠀", inline=True)
  embed.add_field(name=f"{get_emoji('combadge')} Top 5 most collected", value=str("\n".join(f"{t['badge_filename'].replace('_', ' ').replace('.png', '')} ({t['count']})" for t in top_three)), inline=True)
  embed.add_field(name="⠀", value="⠀", inline=True)
  embed.add_field(name=f"{get_emoji('combadge')} Top 5 badge collectors", value=str("\n".join(f"{t['name']} ({t['count']})" for t in top_collectors)), inline=True)
  await ctx.respond(embed=embed, ephemeral=False)

#   ________.__  _____  __
#  /  _____/|__|/ ____\/  |_
# /   \  ___|  \   __\\   __\
# \    \_\  \  ||  |   |  |
#  \______  /__||__|   |__|
#         \/
@bot.slash_command(
  name="gift_badge",
  description="Give a user a random badge (admin only)"
)
@commands.has_permissions(administrator=True)
@option(
  "user",
  discord.User,
  description="Which user to gift the badge to",
  required=True
)
async def gift_badge(ctx:discord.ApplicationContext, user:discord.User):
  """
  give a random badge to a user
  """
  notification_channel_id = get_channel_id(config["handlers"]["xp"]["notification_channel"])
  logger.info(f"{ctx.author.display_name} is attempting to {Style.BRIGHT}gift a random badge{Style.RESET_ALL} to {user.display_name}")

  badge = give_user_badge(user.id)

  channel = bot.get_channel(notification_channel_id)
  embed_title = "You got rewarded a badge!"
  thumbnail_image = random.choice(config["handlers"]["xp"]["celebration_images"])
  embed_description = f"{user.mention} has been gifted a badge by {ctx.author.mention}!"
  message = f"{user.mention} - Nice work, you got a free badge!"
  await send_badge_reward_message(message, embed_description, embed_title, channel, thumbnail_image, badge, user)
  await ctx.respond("Your gift has been sent!", ephemeral=True)

@gift_badge.error
async def gift_badge_error(ctx, error):
  if isinstance(error, commands.MissingPermissions):
    await ctx.respond("Sorry, you do not have permission to do that!", ephemeral=True)
  else:
    await ctx.respond("Sensoars indicate some kind of ...*error* has occured!", ephemeral=True)


#   ________.__  _____  __      _________                    .__  _____.__
#  /  _____/|__|/ ____\/  |_   /   _____/_____   ____   ____ |__|/ ____\__| ____
# /   \  ___|  \   __\\   __\  \_____  \\____ \_/ __ \_/ ___\|  \   __\|  |/ ___\
# \    \_\  \  ||  |   |  |    /        \  |_> >  ___/\  \___|  ||  |  |  \  \___
#  \______  /__||__|   |__|   /_______  /   __/ \___  >\___  >__||__|  |__|\___  >
#         \/                          \/|__|        \/     \/                  \/
@bot.slash_command(
  name="gift_specific_badge",
  description="Give a user a specific badge (admin only)"
)
@commands.has_permissions(administrator=True)
@option(
  "user",
  discord.User,
  description="Which user to gift the badge to",
  required=True
)
@option(
  name="specific_badge",
  description="The name of the Badge to Gift",
  required=True,
  autocomplete=all_badges_autocomplete
)
async def gift_specific_badge(ctx:discord.ApplicationContext, user:discord.User, specific_badge:str):
  """
  give a random badge to a user
  """
  notification_channel_id = get_channel_id(config["handlers"]["xp"]["notification_channel"])
  logger.info(f"{ctx.author.display_name} is attempting to {Style.BRIGHT}gift {specific_badge}{Style.RESET_ALL} to {user.display_name}")

  specific_badge_filename = f"{specific_badge.replace(' ', '_')}.png"
  badge_info = badge_data.get(specific_badge_filename)
  if badge_info == None:
    await ctx.respond(f"Can't send {specific_badge}, it doesn't look like that badge exists!", ephemeral=True)
    return
  else:
    user_badges = db_get_user_badges(user.id)
    if specific_badge not in [b['badge_name'] for b in user_badges]:
      badge = specific_badge_filename
      give_user_specific_badge(user.id, specific_badge_filename)

  channel = bot.get_channel(notification_channel_id)
  embed_title = "You got rewarded a badge!"
  thumbnail_image = random.choice(config["handlers"]["xp"]["celebration_images"])
  embed_description = f"{user.mention} has been gifted a badge by {ctx.author.mention}!"
  message = f"{user.mention} - Nice work, you got a free badge!"
  await send_badge_reward_message(message, embed_description, embed_title, channel, thumbnail_image, badge, user)
  await ctx.respond("Your gift has been sent!", ephemeral=True)


@gift_specific_badge.error
async def gift_specific_badge_error(ctx, error):
  if isinstance(error, commands.MissingPermissions):
    await ctx.respond("Sorry, you do not have permission to do that!", ephemeral=True)
  else:
    await ctx.respond("Sensoars indicate some kind of ...*error* has occured!", ephemeral=True)


async def send_badge_reward_message(message:str, embed_description:str, embed_title:str, channel, thumbnail_image:str, badge:str, user:discord.User):
  badge_info = badge_data.get(badge)
  badge_name = badge.replace("_", " ").replace(".png", "")
  star_str = "🌟 ⠀"*8
  if badge_info:
    badge_url = badge_info["badge_url"]
    embed_description += f"\n\n**{badge_name}**\n{badge_url}"
  embed_description += f"\n{star_str}\n"
  embed=discord.Embed(title=embed_title, description=embed_description, color=discord.Color.random())
  embed.set_thumbnail(url=thumbnail_image)
  embed.set_footer(text="See all your badges by typing '/badges showcase' - disable this by typing '/settings'")
  if badge_info:
    embed.set_image(url=f"{badge_info['image_url']}")
    await channel.send(content=message, embed=embed)
  else:
    embed_filename = str(user.id) + str(abs(hash(badge_name))) + ".png"
    discord_image = discord.File(fp=f"./images/badges/{badge}", filename=embed_filename)
    embed.set_image(url=f"attachment://{embed_filename}")
    await channel.send(content=message, file=discord_image, embed=embed)


# ________                      .__
# \_____  \  __ __   ___________|__| ____   ______
#  /  / \  \|  |  \_/ __ \_  __ \  |/ __ \ /  ___/
# /   \_/.  \  |  /\  ___/|  | \/  \  ___/ \___ \
# \_____\ \_/____/  \___  >__|  |__|\___  >____  >
#        \__>           \/              \/     \/

def db_get_badge_info_by_name(name):
  """
  Given the name of a badge, retrieves its information from badge_info
  :param name: the name of the badge.
  :return:
  """
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT * FROM badge_info WHERE badge_name = %s"
  query.execute(sql, (name,))
  row = query.fetchone()
  query.close()
  db.close()

  return row

# Affiliations
def db_get_all_affiliations():
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT distinct(affiliation_name) FROM badge_affiliation"
  query.execute(sql)
  rows = query.fetchall()
  query.close()
  db.close()

  affiliations = [r['affiliation_name'] for r in rows if r['affiliation_name'] is not None]
  affiliations.sort()

  return affiliations

def db_get_all_affiliation_badges(affiliation):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT badge_name FROM badge_info b_i
      JOIN badge_affiliation AS b_a
        ON b_i.badge_filename = b_a.badge_filename
      WHERE b_a.affiliation_name = %s
  '''
  vals = (affiliation,)
  query.execute(sql, vals)
  rows = query.fetchall()
  query.close()
  db.close()

  affiliation_badges = [r['badge_name'] for r in rows]
  affiliation_badges.sort()

  return affiliation_badges

def db_get_badges_user_has_from_affiliation(user_id, affiliation):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT b_i.badge_name FROM badges b
      JOIN badge_info AS b_i
        ON b.badge_filename = b_i.badge_filename
      JOIN badge_affiliation AS b_a
        ON b_i.badge_filename = b_a.badge_filename
      WHERE b.user_discord_id = %s
        AND b_a.affiliation_name = %s
  '''
  vals = (user_id, affiliation)
  query.execute(sql, vals)
  rows = query.fetchall()
  query.close()
  db.close()

  user_badges = [r['badge_name'] for r in rows]
  user_badges.sort()

  return user_badges

def db_get_badge_filenames_user_has_from_affiliation(user_id, affiliation):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT b_i.badge_filename FROM badges b
      JOIN badge_info AS b_i
        ON b.badge_filename = b_i.badge_filename
      JOIN badge_affiliation AS b_a
        ON b_i.badge_filename = b_a.badge_filename
      WHERE b.user_discord_id = %s
        AND b_a.affiliation_name = %s
  '''
  vals = (user_id, affiliation)
  query.execute(sql, vals)
  rows = query.fetchall()
  db.commit()
  query.close()
  db.close()

  user_badges = [r['badge_filename'] for r in rows]
  user_badges.sort()

  return user_badges

def db_get_set_completion_for_affiliations(user_id):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT
        affiliation_name,
        count(DISTINCT b_i.badge_filename) as totalBadgeCount,
        count(DISTINCT b.badge_filename) as ownedBadgeCount
    FROM badge_info AS b_i
    INNER JOIN badge_affiliation AS b_a
        ON b_i.badge_filename = b_a.badge_filename
    LEFT JOIN badges AS b
        ON b_i.badge_filename = b.badge_filename
        AND b.user_discord_id = %s
    GROUP BY b_a.affiliation_name;
  '''
  vals = (user_id,)
  query.execute(sql, vals)
  rows = query.fetchall()

  db.commit()
  query.close()
  db.close()

  results = [
    {
      "name": r['affiliation_name'],
      "owned": r['ownedBadgeCount'],
      'total': r['totalBadgeCount'],
      'percentage': int((r['ownedBadgeCount'] / r['totalBadgeCount']) * 100)
    } for r in rows if r['ownedBadgeCount'] != 0
  ]
  results = sorted(results, key=lambda r: r['percentage'], reverse=True)
  return results

# Franchises
def db_get_all_franchises():
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT distinct(franchise) FROM badge_info"
  query.execute(sql)
  rows = query.fetchall()
  query.close()
  db.close()

  franchises = [r['franchise'] for r in rows if r['franchise'] is not None]
  franchises.sort()

  return franchises

def db_get_all_franchise_badges(franchise):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT badge_name FROM badge_info b_i
      WHERE franchise = %s
  '''
  vals = (franchise,)
  query.execute(sql, vals)
  rows = query.fetchall()
  query.close()
  db.close()

  franchise_badges = [r['badge_name'] for r in rows]
  franchise_badges.sort()

  return franchise_badges

def db_get_badges_user_has_from_franchise(user_id, franchise):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT b_i.badge_name FROM badges b
      JOIN badge_info AS b_i
        ON b.badge_filename = b_i.badge_filename
      WHERE b.user_discord_id = %s
        AND b_i.franchise = %s
  '''
  vals = (user_id, franchise)
  query.execute(sql, vals)
  rows = query.fetchall()
  query.close()
  db.close()

  user_badges = [r['badge_name'] for r in rows]
  user_badges.sort()

  return user_badges

def db_get_badge_filenames_user_has_from_franchise(user_id, franchise):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT b_i.badge_filename FROM badges b
      JOIN badge_info AS b_i
        ON b.badge_filename = b_i.badge_filename
      WHERE b.user_discord_id = %s
        AND b_i.franchise = %s
  '''
  vals = (user_id, franchise)
  query.execute(sql, vals)
  rows = query.fetchall()
  db.commit()
  query.close()
  db.close()

  user_badges = [r['badge_filename'] for r in rows]
  user_badges.sort()

  return user_badges

def db_get_set_completion_for_franchises(user_id):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT
        b_i.franchise,
        count(DISTINCT b_i.badge_filename) as totalBadgeCount,
        count(DISTINCT b.badge_filename) as ownedBadgeCount
    FROM badge_info AS b_i
    LEFT JOIN badges AS b
        ON b_i.badge_filename = b.badge_filename
        AND b.user_discord_id = %s
    GROUP BY b_i.franchise;
  '''
  vals = (user_id,)
  query.execute(sql, vals)
  rows = query.fetchall()

  db.commit()
  query.close()
  db.close()

  results = [
    {
      "name": r['franchise'],
      "owned": r['ownedBadgeCount'],
      'total': r['totalBadgeCount'],
      'percentage': int((r['ownedBadgeCount'] / r['totalBadgeCount']) * 100)
    } for r in rows if r['ownedBadgeCount'] != 0
  ]
  results = sorted(results, key=lambda r: r['percentage'], reverse=True)
  return results

# Time Periods
def db_get_all_time_periods():
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT distinct(time_period) FROM badge_info"
  query.execute(sql)
  rows = query.fetchall()
  query.close()
  db.close()

  time_periods = [r['time_period'] for r in rows if r['time_period'] is not None]
  time_periods.sort(key=_time_period_sort)

  return time_periods

# We may be dealing with time periods before 1000,
# so tack on a 0 prefix for these for proper sorting
def _time_period_sort(time_period):
  if len(time_period) == 4:
    return f"0{time_period}"
  else:
    return time_period

def db_get_all_time_period_badges(time_period):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT badge_name FROM badge_info b_i
      WHERE time_period = %s
  '''
  vals = (time_period,)
  query.execute(sql, vals)
  rows = query.fetchall()
  query.close()
  db.close()

  time_period_badges = [r['badge_name'] for r in rows]
  time_period_badges.sort()

  return time_period_badges

def db_get_badges_user_has_from_time_period(user_id, time_period):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT b_i.badge_name FROM badges b
      JOIN badge_info AS b_i
        ON b.badge_filename = b_i.badge_filename
      WHERE b.user_discord_id = %s
        AND b_i.time_period = %s
  '''
  vals = (user_id, time_period)
  query.execute(sql, vals)
  rows = query.fetchall()
  query.close()
  db.close()

  user_badges = [r['badge_name'] for r in rows]
  user_badges.sort()

  return user_badges


def db_get_badge_filenames_user_has_from_time_period(user_id, franchise):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT b_i.badge_filename FROM badges b
      JOIN badge_info AS b_i
        ON b.badge_filename = b_i.badge_filename
      WHERE b.user_discord_id = %s
        AND b_i.time_period = %s
  '''
  vals = (user_id, franchise)
  query.execute(sql, vals)
  rows = query.fetchall()
  db.commit()
  query.close()
  db.close()

  user_badges = [r['badge_filename'] for r in rows]
  user_badges.sort()

  return user_badges

def db_get_set_completion_for_time_periods(user_id):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT
        b_i.time_period,
        count(DISTINCT b_i.badge_filename) as totalBadgeCount,
        count(DISTINCT b.badge_filename) as ownedBadgeCount
    FROM badge_info AS b_i
    LEFT JOIN badges AS b
        ON b_i.badge_filename = b.badge_filename
        AND b.user_discord_id = %s
    GROUP BY b_i.time_period;
  '''
  vals = (user_id,)
  query.execute(sql, vals)
  rows = query.fetchall()

  db.commit()
  query.close()
  db.close()

  results = [
    {
      "name": r['time_period'],
      "owned": r['ownedBadgeCount'],
      'total': r['totalBadgeCount'],
      'percentage': int((r['ownedBadgeCount'] / r['totalBadgeCount']) * 100)
    } for r in rows if r['ownedBadgeCount'] != 0
  ]
  results = sorted(results, key=lambda r: r['percentage'], reverse=True)
  return results

# Types
def db_get_all_types():
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT distinct(type_name) FROM badge_type"
  query.execute(sql)
  rows = query.fetchall()
  query.close()
  db.close()

  types = [r['type_name'] for r in rows if r['type_name'] is not None]
  types.sort()

  return types

def db_get_all_type_badges(type):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT badge_name FROM badge_info b_i
      JOIN badge_type AS b_t
        ON b_i.badge_filename = b_t.badge_filename
      WHERE b_t.type_name = %s
  '''
  vals = (type,)
  query.execute(sql, vals)
  rows = query.fetchall()
  query.close()
  db.close()

  type_badges = [r['badge_name'] for r in rows]
  type_badges.sort()

  return type_badges

def db_get_badges_user_has_from_type(user_id, type):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT b_i.badge_name FROM badges b
      JOIN badge_info AS b_i
        ON b.badge_filename = b_i.badge_filename
      JOIN badge_type AS b_t
        ON b_i.badge_filename = b_t.badge_filename
      WHERE b.user_discord_id = %s
        AND b_t.type_name = %s
  '''
  vals = (user_id, type)
  query.execute(sql, vals)
  rows = query.fetchall()
  query.close()
  db.close()

  user_badges = [r['badge_name'] for r in rows]
  user_badges.sort()

  return user_badges

def db_get_badge_filenames_user_has_from_type(user_id, type):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT b_i.badge_filename FROM badges b
      JOIN badge_info AS b_i
        ON b.badge_filename = b_i.badge_filename
      JOIN badge_type AS b_t
        ON b_i.badge_filename = b_t.badge_filename
      WHERE b.user_discord_id = %s
        AND b_t.type_name = %s
  '''
  vals = (user_id, type)
  query.execute(sql, vals)
  rows = query.fetchall()
  db.commit()
  query.close()
  db.close()

  user_badges = [r['badge_filename'] for r in rows]
  user_badges.sort()

  return user_badges

def db_get_set_completion_for_types(user_id):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT
        type_name,
        count(DISTINCT b_i.badge_filename) as totalBadgeCount,
        count(DISTINCT b.badge_filename) as ownedBadgeCount
    FROM badge_info AS b_i
    INNER JOIN badge_type AS b_t
        ON b_i.badge_filename = b_t.badge_filename
    LEFT JOIN badges AS b
        ON b_i.badge_filename = b.badge_filename
        AND b.user_discord_id = %s
    GROUP BY b_t.type_name;
  '''
  vals = (user_id,)
  query.execute(sql, vals)
  rows = query.fetchall()

  db.commit()
  query.close()
  db.close()

  results = [
    {
      "name": r['type_name'],
      "owned": r['ownedBadgeCount'],
      'total': r['totalBadgeCount'],
      'percentage': int((r['ownedBadgeCount'] / r['totalBadgeCount']) * 100)
    } for r in rows if r['ownedBadgeCount'] != 0
  ]
  results = sorted(results, key=lambda r: r['percentage'], reverse=True)
  return results

# give_user_badge(user_discord_id)
# user_discord_id[required]:int
# pick a badge, update badges DB, return badge name
def give_user_badge(user_discord_id:int):
  # list files in images/badges directory
  badges = os.listdir("./images/badges/")
  # get the users current badges
  user_badges = [b['badge_filename'] for b in db_get_user_badges(user_discord_id)]
  badge_choice = random.choice(badges)
  # don't give them a badge they already have
  while badge_choice in user_badges:
    badge_choice = random.choice(badges)
  db = getDB()
  query = db.cursor()
  sql = "INSERT INTO badges (user_discord_id, badge_filename) VALUES (%s, %s)"
  vals = (user_discord_id, badge_choice)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()
  return badge_choice

def give_user_specific_badge(user_discord_id:int, badge_choice:str):
  db = getDB()
  query = db.cursor()
  sql = "INSERT INTO badges (user_discord_id, badge_filename) VALUES (%s, %s)"
  vals = (user_discord_id, badge_choice)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()
  return badge_choice

def run_badge_stats_queries():
  queries = {
    "most_collected" : "SELECT badge_filename, COUNT(id) as count FROM badges WHERE badge_filename != 'Friends_Of_DeSoto.png' GROUP BY badge_filename ORDER BY count DESC LIMIT 5;",
    "total_badges" : "SELECT COUNT(id) as count FROM badges;",
    "badges_today" : "SELECT COUNT(id) as count FROM badges WHERE time_created > NOW() - INTERVAL 1 DAY;",
    "top_collectors" : "SELECT name, COUNT(badges.id) as count FROM users JOIN badges ON users.discord_id = badges.user_discord_id GROUP BY discord_id ORDER BY COUNT(badges.id) DESC LIMIT 5;"
  }
  db = getDB()
  results = {}
  for name,sql in queries.items():
    query = db.cursor(dictionary=True)
    query.execute(sql)
    results[name] = query.fetchall()
    query.close()
  db.close()
  return results
