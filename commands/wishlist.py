from base64 import b16encode
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
  list = ctx.options["list"]
  first_badge = ctx.options["first_badge"]
  second_badge = ctx.options["second_badge"]
  third_badge = ctx.options["third_badge"]
  fourth_badge = ctx.options["fourth_badge"]
  fifth_badge = ctx.options["fifth_badge"]
  sixth_badge = ctx.options["sixth_badge"]

  filtered_badges = [
    first_badge, second_badge, third_badge, fourth_badge, fifth_badge, sixth_badge
  ] + [b['badge_name'] for b in SPECIAL_BADGES]

  current_user_badges = [b['badge_name'] for b in db_get_user_badges(ctx.interaction.user.id)]

  current_list_badges = []
  source_list = []
  filtered_badges = []
  if list == 'wishlist':
    source_list = [b['badge_name'] for b in all_badge_info]
    current_list_badges = [b['badge_name'] for b in db_get_user_wishlist_badges(ctx.interaction.user.id)]
    filtered_badges = filtered_badges + current_user_badges + current_list_badges
  if list == 'offerlist':
    source_list = current_user_badges
    current_list_badges = [b['badge_name'] for b in db_get_user_offerlist_badges(ctx.interaction.user.id)]
    filtered_badges = filtered_badges + current_list_badges

  filtered_badge_names = [b for b in source_list if b not in filtered_badges]

  return [b for b in filtered_badge_names if ctx.value.lower() in b.lower()]

async def remove_autocomplete(ctx:discord.AutocompleteContext):
  list = ctx.options["list"]
  first_badge = ctx.options["first_badge"]
  second_badge = ctx.options["second_badge"]
  third_badge = ctx.options["third_badge"]
  fourth_badge = ctx.options["fourth_badge"]
  fifth_badge = ctx.options["fifth_badge"]
  sixth_badge = ctx.options["sixth_badge"]

  filtered_badges = [
    first_badge, second_badge, third_badge, fourth_badge, fifth_badge, sixth_badge
  ] + [b['badge_name'] for b in SPECIAL_BADGES]

  current_list_badges = []
  if list == 'wishlist':
    current_list_badges = [b['badge_name'] for b in db_get_user_wishlist_badges(ctx.interaction.user.id)]
  if list == 'offerlist':
    current_list_badges = [b['badge_name'] for b in db_get_user_offerlist_badges(ctx.interaction.user.id)]

  filtered_badge_names = [b for b in current_list_badges if b not in filtered_badges]

  return [b for b in filtered_badge_names if ctx.value.lower() in b.lower()]


# ________  .__               .__
# \______ \ |__| ____________ |  | _____  ___.__.
#  |    |  \|  |/  ___/\____ \|  | \__  \<   |  |
#  |    `   \  |\___ \ |  |_> >  |__/ __ \\___  |
# /_______  /__/____  >|   __/|____(____  / ____|
#         \/        \/ |__|             \/\/
@wishlist_group.command(
  name="display",
  description="Show off your wishlist or offerlist."
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
async def showcase(ctx:discord.ApplicationContext, public:str):
  public = (public == "yes")
  await ctx.defer(ephemeral=not public)

  await ctx.followup.send("Not Implemented Yet")

# ________  .__               .__
# \______ \ |__| ____________ |  | _____  ___.__.
#  |    |  \|  |/  ___/\____ \|  | \__  \<   |  |
#  |    `   \  |\___ \ |  |_> >  |__/ __ \\___  |
# /_______  /__/____  >|   __/|____(____  / ____|
#         \/        \/ |__|             \/\/
@wishlist_group.command(
  name="add",
  description="Add up to 6 badges to your Wishlist or Offerlist."
)
@option(
  name="list",
  description="Wishlist or Offerlist?",
  required=True,
  choices=[
    discord.OptionChoice(
      name="Wishlist",
      value="wishlist"
    ),
    discord.OptionChoice(
      name="Offerlist",
      value="offerlist"
    )
  ]
)
@option(
  name="first_badge",
  description="First badge to add",
  required=False,
  autocomplete=add_autocomplete
)
@option(
  name="second_badge",
  description="Second badge to add",
  required=False,
  autocomplete=add_autocomplete
)
@option(
  name="third_badge",
  description="Third badge to add",
  required=False,
  autocomplete=add_autocomplete
)
@option(
  name="fourth_badge",
  description="Fourth badge to add",
  required=False,
  autocomplete=add_autocomplete
)
@option(
  name="fifth_badge",
  description="Fifth badge to add",
  required=False,
  autocomplete=add_autocomplete
)
@option(
  name="sixth_badge",
  description="Sixth badge to add",
  required=False,
  autocomplete=add_autocomplete
)
async def add(
  ctx:discord.ApplicationContext,
  list:str,
  first_badge:str,
  second_badge:str,
  third_badge:str,
  fourth_badge:str,
  fifth_badge:str,
  sixth_badge:str
):
  await ctx.defer(ephemeral=True)
  user_discord_id = ctx.author.id

  selected_badges = [first_badge, second_badge, third_badge, third_badge, fourth_badge, fifth_badge, sixth_badge]
  selected_badges = [b for b in selected_badges if b is not None]

  if len(selected_badges) > len(set(selected_badges)):
    await ctx.followup.send(embed=discord.Embed(
      title="Invalid Selection",
      description=f"All badges selected must be unique!",
      color=discord.Color.red()
    ))
    return

  if list == 'wishlist':
    # Check to make sure none of the badges are already present in their wishlist
    existing_wishlist_badges = [b['badge_name'] for b in db_get_user_wishlist_badges(user_discord_id) if b['badge_name'] in selected_badges]
    if len(existing_wishlist_badges):
      existing_badges_string = "\n".join(existing_wishlist_badges)
      await ctx.followup.send(embed=discord.Embed(
        title="Badge(s) Already Present in Wishlist!",
        description="Unable to complete your request, the following badges are already present in your Wishlist:\n\n"
                    f"{existing_badges_string}",
        color=discord.Color.red()
      ))
      return
    # Otherwise, good to go and add the badges
    for b in selected_badges:
      db_add_badge_name_to_users_wishlist(user_discord_id, b)

  if list == 'offerlist':
    # Check to make sure none of the badges are already present in their offerlist
    existing_offerlist_badges = [b['badge_name'] for b in db_get_user_wishlist_badges(user_discord_id) if b['badge_name'] in selected_badges]
    if len(existing_offerlist_badges):
      existing_badges_string = "\n".join(existing_offerlist_badges)
      await ctx.followup.send(embed=discord.Embed(
        title="Badge(s) Already Present in Offerlist!",
        description="Unable to complete your request, the following badges are already present in your Offerlist:\n\n"
                    f"{existing_badges_string}",
        color=discord.Color.red()
      ))
      return
    # Otherwise, good to go and add the badges
    for b in selected_badges:
      db_add_badge_name_to_users_offerlist(user_discord_id, b)

  selected_badges_string = "\n".join(selected_badges)
  await ctx.followup.send(embed=discord.Embed(
    title="Badges Added Successfully",
    description=f"You've successfully added the following badges to your {list.title()}:"
                "\n\n"
                f"{selected_badges_string}",
    color=discord.Color.green()
  ))


# __________
# \______   \ ____   _____   _______  __ ____
#  |       _// __ \ /     \ /  _ \  \/ // __ \
#  |    |   \  ___/|  Y Y  (  <_> )   /\  ___/
#  |____|_  /\___  >__|_|  /\____/ \_/  \___  >
#         \/     \/      \/                 \/
@wishlist_group.command(
  name="remove",
  description="Remove up to 6 badges to your Wishlist or Offerlist."
)
@option(
  name="list",
  description="Wishlist or Offerlist?",
  required=True,
  choices=[
    discord.OptionChoice(
      name="Wishlist",
      value="wishlist"
    ),
    discord.OptionChoice(
      name="Offerlist",
      value="offerlist"
    )
  ]
)
@option(
  name="first_badge",
  description="First badge to remove",
  required=False,
  autocomplete=remove_autocomplete
)
@option(
  name="second_badge",
  description="Second badge to remove",
  required=False,
  autocomplete=remove_autocomplete
)
@option(
  name="third_badge",
  description="Third badge to remove",
  required=False,
  autocomplete=remove_autocomplete
)
@option(
  name="fourth_badge",
  description="Fourth badge to remove",
  required=False,
  autocomplete=remove_autocomplete
)
@option(
  name="fifth_badge",
  description="Fifth badge to remove",
  required=False,
  autocomplete=remove_autocomplete
)
@option(
  name="sixth_badge",
  description="Sixth badge to remove",
  required=False,
  autocomplete=remove_autocomplete
)
async def remove(
  ctx:discord.ApplicationContext,
  list:str,
  first_badge:str,
  second_badge:str,
  third_badge:str,
  fourth_badge:str,
  fifth_badge:str,
  sixth_badge:str
):
  await ctx.defer(ephemeral=True)
  user_discord_id = ctx.author.id

  selected_badges = [first_badge, second_badge, third_badge, third_badge, fourth_badge, fifth_badge, sixth_badge]
  selected_badges = [b for b in selected_badges if b is not None]

  if len(selected_badges) > len(set(selected_badges)):
    await ctx.followup.send(embed=discord.Embed(
      title="Invalid Selection",
      description=f"All badges selected must be unique!",
      color=discord.Color.red()
    ))
    return

  if list == 'wishlist':
    # Check to make sure the badges are present in their wishlist
    user_wishlist_badge_names =  [b['badge_name'] for b in db_get_user_wishlist_badges(user_discord_id)]
    missing_badge_names = [b for b in selected_badges if b not in user_wishlist_badge_names]
    if len(missing_badge_names):
      missing_badges_string = "\n".join(missing_badge_names)
      await ctx.followup.send(embed=discord.Embed(
        title="Badge(s) Not Present in Wishlist!",
        description="Unable to complete your request, the following badges are not present in your Wishlist:\n\n"
                    f"{missing_badges_string}",
        color=discord.Color.red()
      ))
      return
    # If they are go ahead and remove the badges
    for b in selected_badges:
      db_remove_badge_name_from_users_wishlist(user_discord_id, b)

  if list == 'offerlist':
    # Check to make sure the badges are present in their wishlist
    user_offerlist_badge_names =  [b['badge_name'] for b in db_get_user_offerlist_badges(user_discord_id)]
    missing_badge_names = [b for b in selected_badges if b not in user_offerlist_badge_names]
    if len(missing_badge_names):
      missing_badges_string = "\n".join(missing_badge_names)
      await ctx.followup.send(embed=discord.Embed(
        title="Badge(s) Not Present in Offerlist!",
        description="Unable to complete your request, the following badges are not present in your Offerlist:\n\n"
                    f"{missing_badges_string}",
        color=discord.Color.red()
      ))
      return
    # If they are go ahead and remove the badges
    for b in selected_badges:
      db_remove_badge_name_from_users_offerlist(user_discord_id, b)

  selected_badges_string = "\n".join(selected_badges)
  await ctx.followup.send(embed=discord.Embed(
    title="Badges Removed Successfully",
    description=f"You've successfully removed the following badges to your {list.title()}:"
                "\n\n"
                f"{selected_badges_string}",
    color=discord.Color.green()
  ))