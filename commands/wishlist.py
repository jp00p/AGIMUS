from common import *
from queries.wishlist import *
from utils.badge_utils import *
from utils.check_channel_access import access_check

all_badge_info = db_get_all_badge_info()

wishlist_group = bot.create_group("wishlist", "Badges Wishlist Commands!")

#    _____          __                                     .__          __
#   /  _  \  __ ___/  |_  ____   ____  ____   _____ ______ |  |   _____/  |_  ____
#  /  /_\  \|  |  \   __\/  _ \_/ ___\/  _ \ /     \\____ \|  | _/ __ \   __\/ __ \
# /    |    \  |  /|  | (  <_> )  \__(  <_> )  Y Y  \  |_> >  |_\  ___/|  | \  ___/
# \____|__  /____/ |__|  \____/ \___  >____/|__|_|  /   __/|____/\___  >__|  \___  >
#         \/                        \/            \/|__|             \/          \/

async def add_autocomplete(ctx:discord.AutocompleteContext):
  filtered_badges = [b['badge_name'] for b in SPECIAL_BADGES]

  current_user_badges = [b['badge_name'] for b in db_get_user_badges(ctx.interaction.user.id)]
  current_wishlist_badges = [b['badge_name'] for b in db_get_user_wishlist_badges(ctx.interaction.user.id)]
  filtered_badges = filtered_badges + current_user_badges + current_wishlist_badges

  all_badge_names = [b['badge_name'] for b in all_badge_info]

  filtered_badge_names = [b for b in all_badge_names if b not in filtered_badges]

  return [b for b in filtered_badge_names if ctx.value.lower() in b.lower()]

async def remove_autocomplete(ctx:discord.AutocompleteContext):
  filtered_badges = [b['badge_name'] for b in SPECIAL_BADGES]
  current_list_badges = [b['badge_name'] for b in db_get_user_wishlist_badges(ctx.interaction.user.id)]
  filtered_badge_names = [b for b in current_list_badges if b not in filtered_badges]

  return [b for b in filtered_badge_names if ctx.value.lower() in b.lower()]

async def lock_autocomplete(ctx:discord.AutocompleteContext):
  filtered_badges = [b['badge_name'] for b in SPECIAL_BADGES]

  current_unlocked_badges = [b['badge_name'] for b in db_get_user_badges(ctx.interaction.user.id) if not b['locked']]
  filtered_badge_names = [b for b in current_unlocked_badges if b not in filtered_badges]

  list_badges = [b for b in filtered_badge_names]
  if not list_badges:
    return ['All Badges are currently Locked!']
  else:
    return [b for b in list_badges if ctx.value.lower() in b.lower()]

async def unlock_autocomplete(ctx:discord.AutocompleteContext):
  filtered_badges = [b['badge_name'] for b in SPECIAL_BADGES]

  current_locked_badges = [b['badge_name'] for b in db_get_user_badges(ctx.interaction.user.id) if b['locked']]
  filtered_badge_names = [b for b in current_locked_badges if b not in filtered_badges]

  list_badges = [b for b in filtered_badge_names]
  if not list_badges:
    return ['All Badges are currently Unlocked!']
  else:
    return [b for b in list_badges if ctx.value.lower() in b.lower()]

# ________  .__               .__
# \______ \ |__| ____________ |  | _____  ___.__.
#  |    |  \|  |/  ___/\____ \|  | \__  \<   |  |
#  |    `   \  |\___ \ |  |_> >  |__/ __ \\___  |
# /_______  /__/____  >|   __/|____(____  / ____|
#         \/        \/ |__|             \/\/
@wishlist_group.command(
  name="display",
  description="List all of the badges on your current wishlist."
)
async def display(ctx:discord.ApplicationContext):
  await ctx.defer(ephemeral=True)
  user_discord_id = ctx.author.id

  wishlist_badges = db_get_user_wishlist_badges(user_discord_id)

  if len(wishlist_badges):
    # Set up paginated results
    max_badges_per_page = 50
    all_pages = [wishlist_badges[i:i + max_badges_per_page] for i in range(0, len(wishlist_badges), max_badges_per_page)]
    total_pages = len(all_pages)

    wishlist_pages = []
    for page_index, page in enumerate(all_pages):
      embed = discord.Embed(
        title="Wishlist",
        description="\n".join([b['badge_name'] for b in page]),
        color=discord.Color.blurple()
      )
      embed.set_footer(text=f"Page {page_index + 1} of {total_pages}")
      wishlist_pages.append(embed)

    paginator = pages.Paginator(
      pages=wishlist_pages,
      loop_pages=True,
      disable_on_timeout=True
    )

    await paginator.respond(ctx.interaction, ephemeral=True)
  else:
    await ctx.followup.send(embed=discord.Embed(
      title="No Current Wishlist Badges Present",
      color=discord.Color.red()
    ))


#    _____          __         .__
#   /     \ _____ _/  |_  ____ |  |__   ____   ______
#  /  \ /  \\__  \\   __\/ ___\|  |  \_/ __ \ /  ___/
# /    Y    \/ __ \|  | \  \___|   Y  \  ___/ \___ \
# \____|__  (____  /__|  \___  >___|  /\___  >____  >
#         \/     \/          \/     \/     \/     \/
@wishlist_group.command(
  name="matches",
  description="Find matches from other users who have what you want, and want what you have!"
)
async def matches(ctx:discord.ApplicationContext):
  await ctx.defer(ephemeral=True)
  user_discord_id = ctx.author.id

  # Get all the users and the badgenames that have the badges the user wants
  wishlist_matches = db_get_wishlist_matches(user_discord_id)
  wishlist_aggregate = {}
  if wishlist_matches:
    for match in wishlist_matches:
      user_id = match['user_discord_id']
      user_record = wishlist_aggregate.get(user_id)
      if not user_record:
        wishlist_aggregate[user_id] = [match['badge_name']]
      else:
        wishlist_aggregate[user_id].append(match['badge_name'])

  # Get all the users and the badgenames that want badges that the user has
  inventory_matches = db_get_wishlist_inventory_matches(user_discord_id)
  inventory_aggregate = {}
  if inventory_matches:
    for match in inventory_matches:
      user_id = match['user_discord_id']
      user_record = inventory_aggregate.get(user_id)
      if not user_record:
        inventory_aggregate[user_id] = [match['badge_name']]
      else:
        inventory_aggregate[user_id].append(match['badge_name'])

  # Now create an aggregate of the users that intersect
  exact_matches_aggregate = {}
  for key in wishlist_aggregate:
    if key in inventory_aggregate:
      exact_matches_aggregate[key] = {
        'has': wishlist_aggregate[key],
        'wants': inventory_aggregate[key]
      }

  if len(exact_matches_aggregate.keys()):
    for user_id in exact_matches_aggregate.keys():
      user = await bot.current_guild.fetch_member(user_id)
      embed = discord.Embed(
        title="Wishlist Match!",
        description=f"{user.mention} has a wishlist match with you.",
        color=discord.Color.random()
      )
      embed.add_field(
        name="Has From Your Wishlist:",
        value="\n".join(exact_matches_aggregate[user_id]['has']),
        inline=False
      )
      embed.add_field(
        name="Wants From Your Inventory:",
        value="\n".join(exact_matches_aggregate[user_id]['wants']),
        inline=False
      )
      embed.set_footer(text="Make them an offer with '/trade start'!")
      await ctx.followup.send(embed=embed, ephemeral=True)
  else:
    await ctx.followup.send(
      embed=discord.Embed(
        title="No Wishlist Matches Found",
        description="Please check back later!",
        color=discord.Color.blurple()
      )
    )


#    _____       .___  .___
#   /  _  \    __| _/__| _/
#  /  /_\  \  / __ |/ __ |
# /    |    \/ /_/ / /_/ |
# \____|__  /\____ \____ |
#         \/      \/    \/
@wishlist_group.command(
  name="add",
  description="Add badges to your Wishlist."
)
@option(
  name="badge",
  description="Badge to add",
  required=True,
  autocomplete=add_autocomplete
)
async def add(ctx:discord.ApplicationContext, badge:str):
  await ctx.defer(ephemeral=True)
  user_discord_id = ctx.author.id

  # Check to make sure the badge is not already present in their wishlist
  existing_wishlist_badges = [b['badge_name'] for b in db_get_user_wishlist_badges(user_discord_id)]
  if badge in existing_wishlist_badges:
    await ctx.followup.send(
      embed=discord.Embed(
        title="Badge Already Present in Wishlist!",
        description=f"Unable to complete your request, {badge} is already present in your Wishlist.",
        color=discord.Color.red()
      )
    )
    return

  # Check to make sure the badge is not already present in their inventory
  existing_user_badges = [b['badge_name'] for b in db_get_user_badges(user_discord_id)]
  if badge in existing_user_badges:
    await ctx.followup.send(
      embed=discord.Embed(
        title="Badge Already Present in Inventory!",
        description=f"Unable to complete your request, {badge} is already present in your Inventory. No need to wish for it!",
        color=discord.Color.red()
      )
    )
    return

  # Otherwise, good to go and add the badge
  db_add_badge_name_to_users_wishlist(user_discord_id, badge)

  badge_info = db_get_badge_info_by_name(badge)
  discord_image = discord.File(fp=f"./images/badges/{badge_info['badge_filename']}", filename=badge_info['badge_filename'])
  embed = discord.Embed(
    title="Badge Added Successfully",
    description=f"You've successfully added {badge} to your wishlist.",
    color=discord.Color.green()
  )
  embed.set_image(url=f"attachment://{badge_info['badge_filename']}")
  await ctx.followup.send(embed=embed, file=discord_image)


#    _____       .___  .____________       __
#   /  _  \    __| _/__| _/   _____/ _____/  |_
#  /  /_\  \  / __ |/ __ |\_____  \_/ __ \   __\
# /    |    \/ /_/ / /_/ |/        \  ___/|  |
# \____|__  /\____ \____ /_______  /\___  >__|
#         \/      \/    \/       \/     \/
@wishlist_group.command(
  name="add_set",
  description="Add a full set of badges to your Wishlist."
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
async def add_set(ctx:discord.ApplicationContext, category:str, selection:str):
  await ctx.defer(ephemeral=True)
  user_discord_id = ctx.author.id

  if category == 'affiliation':
    all_set_badges = db_get_all_affiliation_badges(selection)
  elif category == 'franchise':
    all_set_badges = db_get_all_franchise_badges(selection)
  elif category == 'time_period':
    all_set_badges = db_get_all_time_period_badges(selection)
  elif category == 'type':
    all_set_badges = db_get_all_type_badges(selection)
  else:
    await ctx.followup.send("Select a category")
    return

  category_title = category.replace("_", " ").title()

  if not all_set_badges:
    await ctx.followup.send(
      embed=discord.Embed(
        title=f"Your entry was not in the list of {category_title}s!",
        color=discord.Color.red()
      )
    )
    return

  existing_user_badges = [b['badge_name'] for b in db_get_user_badges(user_discord_id)]
  existing_wishlist_badges = [b['badge_name'] for b in db_get_user_wishlist_badges(user_discord_id)]

  # Filter out those badges that are already present in the Wishlist and user's Inventory
  valid_badges = [b['badge_name'] for b in all_set_badges if b['badge_name'] not in existing_user_badges and b['badge_name'] not in existing_wishlist_badges]

  # If there are no badges to add, error to user
  if not valid_badges:
    await ctx.followup.send(
      embed=discord.Embed(
        title="All Set Badges Already Present!",
        description=f"Unable to complete your request, all of the `{selection}` badges are already present in your Wishlist or in your Inventory.",
        color=discord.Color.red()
      )
    )
    return

  # Otherwise go ahead and add them
  for badge_name in valid_badges:
    db_add_badge_name_to_users_wishlist(user_discord_id, badge_name)

  embed = discord.Embed(
    title="Badge Set Added Successfully",
    description=f"You've successfully added all of the `{selection}` badges to your Wishlist you do not currently possess.",
    color=discord.Color.green()
  )
  await ctx.followup.send(embed=embed)


# __________
# \______   \ ____   _____   _______  __ ____
#  |       _// __ \ /     \ /  _ \  \/ // __ \
#  |    |   \  ___/|  Y Y  (  <_> )   /\  ___/
#  |____|_  /\___  >__|_|  /\____/ \_/  \___  >
#         \/     \/      \/                 \/
@wishlist_group.command(
  name="remove",
  description="Remove a badge from your wishlist."
)
@option(
  name="badge",
  description="Badge to remove",
  required=True,
  autocomplete=remove_autocomplete
)
async def remove(ctx:discord.ApplicationContext, badge:str):
  await ctx.defer(ephemeral=True)
  user_discord_id = ctx.author.id

  # Check to make sure the badges are present in their wishlist
  user_wishlist_badge_names =  [b['badge_name'] for b in db_get_user_wishlist_badges(user_discord_id)]
  if badge not in user_wishlist_badge_names:
    await ctx.followup.send(embed=discord.Embed(
      title="Badge Not Present in Wishlist!",
      description=f"Unable to complete your request, {badge} is not present in your Wishlist",
      color=discord.Color.red()
    ))
    return

  # If they are go ahead and remove the badges
  db_remove_badge_name_from_users_wishlist(user_discord_id, badge)

  await ctx.followup.send(embed=discord.Embed(
    title="Badge Removed Successfully",
    description=f"You've successfully removed {badge} from your wishlist",
    color=discord.Color.green()
  ))


# __________                                    _________       __
# \______   \ ____   _____   _______  __ ____  /   _____/ _____/  |_
#  |       _// __ \ /     \ /  _ \  \/ // __ \ \_____  \_/ __ \   __\
#  |    |   \  ___/|  Y Y  (  <_> )   /\  ___/ /        \  ___/|  |
#  |____|_  /\___  >__|_|  /\____/ \_/  \___  >_______  /\___  >__|
#         \/     \/      \/                 \/        \/     \/
@wishlist_group.command(
  name="remove_set",
  description="Remove a full set of badges from your Wishlist."
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
async def remove_set(ctx:discord.ApplicationContext, category:str, selection:str):
  await ctx.defer(ephemeral=True)
  user_discord_id = ctx.author.id

  if category == 'affiliation':
    all_set_badges = db_get_all_affiliation_badges(selection)
  elif category == 'franchise':
    all_set_badges = db_get_all_franchise_badges(selection)
  elif category == 'time_period':
    all_set_badges = db_get_all_time_period_badges(selection)
  elif category == 'type':
    all_set_badges = db_get_all_type_badges(selection)
  else:
    await ctx.followup.send("Select a category")
    return

  category_title = category.replace("_", " ").title()

  if not all_set_badges:
    await ctx.followup.send(
      embed=discord.Embed(
        title=f"Your entry was not in the list of {category_title}s!",
        color=discord.Color.red()
      )
    )
    return

  existing_wishlist_badges = [b['badge_name'] for b in db_get_user_wishlist_badges(user_discord_id)]

  # Filter out those badges that are not already present in the Wishlist and user's Inventory
  valid_badges = [b['badge_name'] for b in all_set_badges if b['badge_name'] in existing_wishlist_badges]

  # If there are no badges to add, error to user
  if not valid_badges:
    await ctx.followup.send(
      embed=discord.Embed(
        title="No Set Badges Present in Wishlist!",
        description=f"Unable to complete your request, none of the `{selection}` badges are currently present in your Wishlist.",
        color=discord.Color.red()
      )
    )
    return

  # Otherwise go ahead and add them
  for badge_name in valid_badges:
    db_remove_badge_name_from_users_wishlist(user_discord_id, badge_name)

  embed = discord.Embed(
    title="Badge Set Removed Successfully",
    description=f"You've successfully removed all of the `{selection}` badges from your Wishlist.",
    color=discord.Color.green()
  )
  await ctx.followup.send(embed=embed)


# .____                  __
# |    |    ____   ____ |  | __
# |    |   /  _ \_/ ___\|  |/ /
# |    |__(  <_> )  \___|    <
# |_______ \____/ \___  >__|_ \
#         \/          \/     \/
@wishlist_group.command(
  name="lock",
  description="Lock a badge from being listed in Wishlist matches."
)
@option(
  name="badge",
  description="Badge to lock",
  required=True,
  autocomplete=lock_autocomplete
)
async def lock(ctx:discord.ApplicationContext, badge:str):
  await ctx.defer(ephemeral=True)
  user_discord_id = ctx.author.id

  # Check to make sure badge is present in inventory
  existing_badges = [b['badge_name'] for b in db_get_user_badges(user_discord_id)]
  if badge not in existing_badges:
    await ctx.followup.send(
      embed=discord.Embed(
        title="Badge Not Present in Inventory!",
        description=f"Unable to complete your request, `{badge}` is not present in your inventory.",
        color=discord.Color.red()
      )
    )
    return

  badge_info = db_get_badge_locked_status_by_name(user_discord_id, badge)
  if badge_info['locked']:
    await ctx.followup.send(
      embed=discord.Embed(
        title="Badge Already Locked!",
        description=f"Unable to complete your request, `{badge}` has already been locked in your inventory.",
        color=discord.Color.red()
      )
    )
    return

  # Otherwise, good to go and add the badge
  db_lock_badge_by_filename(user_discord_id, badge_info['badge_filename'])

  discord_image = discord.File(fp=f"./images/badges/{badge_info['badge_filename']}", filename=badge_info['badge_filename'])
  embed = discord.Embed(
    title="Badge Locked Successfully",
    description=f"You've successfully locked `{badge}` from being listed in Wishlist matches.",
    color=discord.Color.green()
  )
  embed.set_image(url=f"attachment://{badge_info['badge_filename']}")
  await ctx.followup.send(embed=embed, file=discord_image)


# .____                  __      _________       __
# |    |    ____   ____ |  | __ /   _____/ _____/  |_
# |    |   /  _ \_/ ___\|  |/ / \_____  \_/ __ \   __\
# |    |__(  <_> )  \___|    <  /        \  ___/|  |
# |_______ \____/ \___  >__|_ \/_______  /\___  >__|
#         \/          \/     \/        \/     \/
@wishlist_group.command(
  name="lock_set",
  description="Lock your current items in a set from being listed in Wishlist matches."
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
async def lock_set(ctx:discord.ApplicationContext, category:str, selection:str):
  await ctx.defer(ephemeral=True)
  user_discord_id = ctx.author.id

  if category == 'affiliation':
    all_set_badges = db_get_all_affiliation_badges(selection)
  elif category == 'franchise':
    all_set_badges = db_get_all_franchise_badges(selection)
  elif category == 'time_period':
    all_set_badges = db_get_all_time_period_badges(selection)
  elif category == 'type':
    all_set_badges = db_get_all_type_badges(selection)
  else:
    await ctx.followup.send("Select a category")
    return

  category_title = category.replace("_", " ").title()

  if not all_set_badges:
    await ctx.followup.send(
      embed=discord.Embed(
        title=f"Your entry was not in the list of {category_title}s!",
        color=discord.Color.red()
      )
    )
    return

  # Otherwise, good to go and lock the badges
  for badge_info in all_set_badges:
    db_lock_badge_by_filename(user_discord_id, badge_info['badge_filename'])

  embed = discord.Embed(
    title="Badge Set Locked Successfully",
    description=f"You've successfully locked all of the `{selection}` badges in your inventory from being listed in Wishlist matches.",
    color=discord.Color.green()
  )
  await ctx.followup.send(embed=embed)

#  ____ ___      .__                 __
# |    |   \____ |  |   ____   ____ |  | __
# |    |   /    \|  |  /  _ \_/ ___\|  |/ /
# |    |  /   |  \  |_(  <_> )  \___|    <
# |______/|___|  /____/\____/ \___  >__|_ \
#              \/                 \/     \/
@wishlist_group.command(
  name="unlock",
  description="Unlock a badge so that it is listed again in Wishlist matches."
)
@option(
  name="badge",
  description="Badge to unlock",
  required=True,
  autocomplete=unlock_autocomplete
)
async def unlock(ctx:discord.ApplicationContext, badge:str):
  await ctx.defer(ephemeral=True)
  user_discord_id = ctx.author.id

  # Check to make sure badge is present in inventory
  existing_badges = [b['badge_name'] for b in db_get_user_badges(user_discord_id)]
  if badge not in existing_badges:
    await ctx.followup.send(
      embed=discord.Embed(
        title="Badge Not Present in Inventory!",
        description=f"Unable to complete your request, `{badge}` is not present in your inventory.",
        color=discord.Color.red()
      )
    )
    return

  badge_info = db_get_badge_locked_status_by_name(user_discord_id, badge)
  if not badge_info['locked']:
    await ctx.followup.send(
      embed=discord.Embed(
        title="Badge Unlocked!",
        description=f"Unable to complete your request, `{badge}` has already been unlocked in your inventory.",
        color=discord.Color.red()
      )
    )
    return

  # Otherwise, good to go and unlock the badge
  db_unlock_badge_by_filename(user_discord_id, badge_info['badge_filename'])

  discord_image = discord.File(fp=f"./images/badges/{badge_info['badge_filename']}", filename=badge_info['badge_filename'])
  embed = discord.Embed(
    title="Badge Unlocked Successfully",
    description=f"You've successfully unlocked `{badge}` and it will now be available for listing in Wishlist matches.",
    color=discord.Color.green()
  )
  embed.set_image(url=f"attachment://{badge_info['badge_filename']}")
  await ctx.followup.send(embed=embed, file=discord_image)


#  ____ ___                     __      _________       __
# |    |   \____   ____   ____ |  | __ /   _____/ _____/  |_
# |    |   /    \ /  _ \_/ ___\|  |/ / \_____  \_/ __ \   __\
# |    |  /   |  (  <_> )  \___|    <  /        \  ___/|  |
# |______/|___|  /\____/ \___  >__|_ \/_______  /\___  >__|
#              \/            \/     \/        \/     \/
@wishlist_group.command(
  name="unlock_set",
  description="Unlock your current items in a set so they are listed in Wishlist matches."
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
async def unlock_set(ctx:discord.ApplicationContext, category:str, selection:str):
  await ctx.defer(ephemeral=True)
  user_discord_id = ctx.author.id

  if category == 'affiliation':
    all_set_badges = db_get_all_affiliation_badges(selection)
  elif category == 'franchise':
    all_set_badges = db_get_all_franchise_badges(selection)
  elif category == 'time_period':
    all_set_badges = db_get_all_time_period_badges(selection)
  elif category == 'type':
    all_set_badges = db_get_all_type_badges(selection)
  else:
    await ctx.followup.send("Select a category")
    return

  category_title = category.replace("_", " ").title()

  if not all_set_badges:
    await ctx.followup.send(
      embed=discord.Embed(
        title=f"Your entry was not in the list of {category_title}s!",
        color=discord.Color.red()
      )
    )
    return

  # Otherwise, good to go and lock the badges
  for badge_info in all_set_badges:
    db_unlock_badge_by_filename(user_discord_id, badge_info['badge_filename'])

  embed = discord.Embed(
    title="Badge Set Locked Successfully",
    description=f"You've successfully unlocked all of the `{selection}` badges in your inventory and they will now be listed in Wishlist matches.",
    color=discord.Color.green()
  )
  await ctx.followup.send(embed=embed)
