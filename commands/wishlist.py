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

  source_list = [b['badge_name'] for b in all_badge_info]
  current_list_badges = [b['badge_name'] for b in db_get_user_wishlist_badges(ctx.interaction.user.id)]
  filtered_badges = filtered_badges + current_user_badges + current_list_badges

  filtered_badge_names = [b for b in source_list if b not in filtered_badges]

  return [b for b in filtered_badge_names if ctx.value.lower() in b.lower()]

async def remove_autocomplete(ctx:discord.AutocompleteContext):
  filtered_badges = [b['badge_name'] for b in SPECIAL_BADGES]
  current_list_badges = [b['badge_name'] for b in db_get_user_wishlist_badges(ctx.interaction.user.id)]
  filtered_badge_names = [b for b in current_list_badges if b not in filtered_badges]

  return [b for b in filtered_badge_names if ctx.value.lower() in b.lower()]

async def lock_autocomplete(ctx:discord.AutocompleteContext):
  filtered_badges = [b['badge_name'] for b in SPECIAL_BADGES]

  current_user_badges = [b for b in db_get_user_badges(ctx.interaction.user.id) if not b['locked']]
  filtered_badge_names = [b for b in current_user_badges if b not in filtered_badges]

  list_badges = [b for b in filtered_badge_names]
  if not list_badges:
    return ['All Badges are currently Locked!']
  else:
    return [b for b in list_badges if ctx.value.lower() in b.lower()]

async def unlock_autocomplete(ctx:discord.AutocompleteContext):
  filtered_badges = [b['badge_name'] for b in SPECIAL_BADGES]

  current_user_badges = [b for b in db_get_user_badges(ctx.interaction.user.id) if b['locked']]
  filtered_badge_names = [b for b in current_user_badges if b not in filtered_badges]

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
async def display(ctx:discord.ApplicationContext, public:str):
  public = (public == "yes")
  await ctx.defer(ephemeral=not public)
  user_discord_id = ctx.author.id

  wishlist_badges = db_get_user_wishlist_badges(user_discord_id)

  if len(wishlist_badges):
    embed = discord.Embed(
      title="Your Wishlist"
    )
    embed.add_field(
      name="Wishlist Badges",
      value="\n".join([b['badge_name'] for b in wishlist_badges])
    )
    await ctx.followup.send(embed=embed, ephemeral=not public)
  else:
    await ctx.followup.send(embed=discord.Embed(
      title="No Current Wishlist Badges Present",
      color=discord.Color.red()
    ), ephemeral=True)

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
  required=False,
  autocomplete=add_autocomplete
)
async def add(ctx:discord.ApplicationContext, badge:str):
  await ctx.defer(ephemeral=True)
  user_discord_id = ctx.author.id

  # Check to make sure none of the badges are already present in their wishlist
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
  required=False,
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
    wishlist_aggregate = {}
    for match in wishlist_matches:
      user_id = match['user_discord_id']
      user_record = match.get(user_id)
      if not user_record:
        wishlist_aggregate[user_id] = [match['badge_name']]
      else:
        wishlist_aggregate[user_id].append(match['badge_name'])

  # Get all the users and the badgenames that want badges that the user has
  inventory_matches = db_get_wishlist_inventory_matches(user_discord_id)
  inventory_matches_aggregate = {}
  if inventory_matches:
    for match in inventory_matches:
      user_id = match['user_discord_id']
      user_record = match.get(user_id)
      if not user_record:
        inventory_matches_aggregate[user_id] = [match['badge_name']]
      else:
        inventory_matches_aggregate[user_id].append(match['badge_name'])

  # Now create an aggregate of the users that intersect
  exact_matches_aggregate = {}
  for key in wishlist_aggregate:
    if key in inventory_matches_aggregate:
      exact_matches_aggregate[key] = {
        'has': wishlist_aggregate[key],
        'wants': inventory_matches_aggregate[key]
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
    await ctx.followup.send(embed=discord.Embed(
        title="No Wishlist Matches Found",
        description="Please check back later!"
      ),
      ephemeral=True
    )

# .____                  __
# |    |    ____   ____ |  | __
# |    |   /  _ \_/ ___\|  |/ /
# |    |__(  <_> )  \___|    <
# |_______ \____/ \___  >__|_ \
#         \/          \/     \/
@wishlist_group.command(
  name="lock",
  description="Lock a badge from being listed in Wishlist matches and trading."
)
@option(
  name="badge",
  description="Badge to lock",
  required=False,
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
        description=f"Unable to complete your request, {badge} is not present in your inventory.",
        color=discord.Color.red()
      )
    )
    return

  badge_info = db_get_badge_locked_status_by_name(badge)
  if badge_info['locked']:
    await ctx.followup.send(
      embed=discord.Embed(
        title="Badge Already Locked!",
        description=f"Unable to complete your request, {badge} has already been locked in your inventory.",
        color=discord.Color.red()
      )
    )
    return

  # Otherwise, good to go and add the badge
  db_lock_badge_by_filename(user_discord_id, badge_info['badge_filename'])

  discord_image = discord.File(fp=f"./images/badges/{badge_info['badge_filename']}", filename=badge_info['badge_filename'])
  embed = discord.Embed(
    title="Badge Locked Successfully",
    description=f"You've successfully locked {badge} from being traded and listed in Wishlist matches.",
    color=discord.Color.green()
  )
  embed.set_image(url=f"attachment://{badge_info['badge_filename']}")
  await ctx.followup.send(embed=embed, file=discord_image)



#  ____ ___      .__                 __
# |    |   \____ |  |   ____   ____ |  | __
# |    |   /    \|  |  /  _ \_/ ___\|  |/ /
# |    |  /   |  \  |_(  <_> )  \___|    <
# |______/|___|  /____/\____/ \___  >__|_ \
#              \/                 \/     \/
@wishlist_group.command(
  name="unlock",
  description="Unlock a badge from being listed in Wishlist matches and trading."
)
@option(
  name="badge",
  description="Badge to unlock",
  required=False,
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
        description=f"Unable to complete your request, {badge} is not present in your inventory.",
        color=discord.Color.red()
      )
    )
    return

  badge_info = db_get_badge_locked_status_by_name(badge)
  if not badge_info['locked']:
    await ctx.followup.send(
      embed=discord.Embed(
        title="Badge Unlocked!",
        description=f"Unable to complete your request, {badge} has already been unlocked in your inventory.",
        color=discord.Color.red()
      )
    )
    return

  # Otherwise, good to go and add the badge
  db_unlock_badge_by_filename(user_discord_id, badge_info['badge_filename'])

  discord_image = discord.File(fp=f"./images/badges/{badge_info['badge_filename']}", filename=badge_info['badge_filename'])
  embed = discord.Embed(
    title="Badge Unlocked Successfully",
    description=f"You've successfully unlocked {badge} and is now available for being traded and listed in Wishlist matches.",
    color=discord.Color.green()
  )
  embed.set_image(url=f"attachment://{badge_info['badge_filename']}")
  await ctx.followup.send(embed=embed, file=discord_image)