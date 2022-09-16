from dateutil import tz

from common import *
from cogs.trade import db_cancel_trade, get_offered_and_requested_badge_names
import queries.badge_completion as queries_badge_completion
from queries.badge_scrap import *
from queries.wishlist import *
from utils.badge_utils import *
from utils.check_channel_access import access_check
from utils.string_utils import *

all_badge_info = db_get_all_badge_info()

#    _____          __                                     .__          __
#   /  _  \  __ ___/  |_  ____   ____  ____   _____ ______ |  |   _____/  |_  ____
#  /  /_\  \|  |  \   __\/  _ \_/ ___\/  _ \ /     \\____ \|  | _/ __ \   __\/ __ \
# /    |    \  |  /|  | (  <_> )  \__(  <_> )  Y Y  \  |_> >  |_\  ___/|  | \  ___/
# \____|__  /____/ |__|  \____/ \___  >____/|__|_|  /   __/|____/\___  >__|  \___  >
#         \/                        \/            \/|__|             \/          \/
async def all_badges_autocomplete(ctx:discord.AutocompleteContext):
  return [badge['badge_name'] for badge in all_badge_info if ctx.value.lower() in badge['badge_name'].lower()]

async def scrapper_autocomplete(ctx:discord.AutocompleteContext):
  first_badge = ctx.options["first_badge"]
  second_badge = ctx.options["second_badge"]
  third_badge = ctx.options["third_badge"]

  user_badges = db_get_user_unlocked_badges(ctx.interaction.user.id)

  filtered_badges = [first_badge, second_badge, third_badge] + [b['badge_name'] for b in SPECIAL_BADGES]

  filtered_badge_names = [badge['badge_name'] for badge in user_badges if badge['badge_name'] not in filtered_badges]

  return [b for b in filtered_badge_names if ctx.value.lower() in b.lower()]

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
  name="filter",
  description="Show only Locked, Unlocked, or Special badges?",
  required=False,
  choices=[
    discord.OptionChoice(
      name="Unlocked",
      value="unlocked"
    ),
    discord.OptionChoice(
      name="Locked",
      value="locked"
    ),
    discord.OptionChoice(
      name="Special",
      value="special"
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
async def showcase(ctx:discord.ApplicationContext, public:str, filter:str, color:str):
  public = (public == "yes")
  await ctx.defer(ephemeral=not public)

  if filter is not None:
    if filter == 'unlocked':
      title = f"{ctx.author.display_name.encode('ascii', errors='ignore').decode().strip()}'s Badge Collection - Unlocked"
      user_badges = db_get_user_unlocked_badges(ctx.author.id)
    elif filter == 'locked':
      title = f"{ctx.author.display_name.encode('ascii', errors='ignore').decode().strip()}'s Badge Collection - Locked"
      user_badges = db_get_user_locked_badges(ctx.author.id)
    elif filter == 'special':
      title = f"{ctx.author.display_name.encode('ascii', errors='ignore').decode().strip()}'s Badge Collection - Special"
      user_badges = db_get_user_special_badges(ctx.author.id)
  else:
    title = f"{ctx.author.display_name.encode('ascii', errors='ignore').decode().strip()}'s Badge Collection"
    user_badges = db_get_user_badges(ctx.author.id)

  # Set up text values for paginated pages
  total_badges_cnt = len(all_badge_info)
  user_badges_cnt = len(user_badges)
  collected = f"{user_badges_cnt} TOTAL ON THE USS HOOD"
  filename_prefix = f"badge_list_{ctx.author.id}-page-"

  if color:
    db_set_user_badge_page_color_preference(ctx.author.id, "showcase", color)
  badge_images = await generate_paginated_badge_images(ctx.author, 'showcase', user_badges, total_badges_cnt, title, collected, filename_prefix)

  embed = discord.Embed(
    title=f"Badge Collection",
    description=f"{ctx.author.mention} has collected {user_badges_cnt} of {total_badges_cnt}!",
    color=discord.Color.blurple()
  )

  # If we're doing a public display, use the images directly
  # Otherwise private displays can use the paginator
  if not public:
    buttons = [
      pages.PaginatorButton("prev", label="   ⬅   ", style=discord.ButtonStyle.primary, disabled=bool(user_badges_cnt <= 30), row=1),
      pages.PaginatorButton(
        "page_indicator", style=discord.ButtonStyle.gray, disabled=True, row=1
      ),
      pages.PaginatorButton("next", label="   ➡   ", style=discord.ButtonStyle.primary, disabled=bool(user_badges_cnt <= 30), row=1),
    ]

    pages_list = [
      pages.Page(files=[image], embeds=[embed])
      for image in badge_images
    ]
    paginator = pages.Paginator(
        pages=pages_list,
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
        await ctx.followup.send(embed=embed, files=chunk, ephemeral=False)
      else:
        await ctx.followup.send(files=chunk, ephemeral=False)


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

  category_title = category.replace("_", " ").title()

  if category == 'affiliation':
    user_set_badges = db_get_badges_user_has_from_affiliation(ctx.author.id, selection)
    all_set_badges = db_get_all_affiliation_badges(selection)
  elif category == 'franchise':
    user_set_badges = db_get_badges_user_has_from_franchise(ctx.author.id, selection)
    all_set_badges = db_get_all_franchise_badges(selection)
  elif category == 'time_period':
    user_set_badges = db_get_badges_user_has_from_time_period(ctx.author.id, selection)
    all_set_badges = db_get_all_time_period_badges(selection)
  elif category == 'type':
    user_set_badges = db_get_badges_user_has_from_type(ctx.author.id, selection)
    all_set_badges = db_get_all_type_badges(selection)
  else:
    await ctx.followup.send("Select a category", ephemeral=True)
    return

  if not all_set_badges:
    await ctx.followup.send(
      embed=discord.Embed(
        title=f"Your entry was not in the list of {category_title}s!",
        color=discord.Color.red()
      ), ephemeral=True
    )
    return

  set_badges = []
  for badge in all_set_badges:
    result = db_get_badge_locked_status_by_name(ctx.author.id, badge['badge_name'])
    locked = result['locked'] if result else False
    record = {
      'badge_name': badge['badge_name'],
      'badge_filename': badge['badge_filename'],
      'special': badge['special'],
      'locked': locked,
      'in_user_collection': badge['badge_name'] in [b['badge_name'] for b in user_set_badges]
    }
    set_badges.append(record)

  user_set_badge_cnt = len([b for b in set_badges if b['in_user_collection']])
  user_all_badge_cnt = db_get_badge_count_for_user(ctx.author.id)

  # Set up text values for paginated pages
  title = f"{ctx.author.display_name.encode('ascii', errors='ignore').decode().strip()}'s Badge Set: {category_title} - {selection}"
  collected = f"{user_set_badge_cnt} OF {len(set_badges)}"
  filename_prefix = f"badge_set_{ctx.author.id}_{selection.lower().replace(' ', '-').replace('/', '-')}-page-"

  if color:
    db_set_user_badge_page_color_preference(ctx.author.id, "sets", color)
  badge_images = await generate_paginated_badge_images(ctx.author, 'sets', set_badges, user_all_badge_cnt, title, collected, filename_prefix)

  embed = discord.Embed(
    title=f"Badge Set: **{category_title}** - **{selection}**",
    description=f"{ctx.author.mention} has collected {user_set_badge_cnt} of {len(set_badges)}!",
    color=discord.Color.blurple()
  )

  # If we're doing a public display, use the images directly
  # Otherwise private displays can use the paginator
  if not public:
    buttons = [
      pages.PaginatorButton("prev", label="   ⬅   ", style=discord.ButtonStyle.primary, disabled=bool(len(set_badges) <= 30), row=1),
      pages.PaginatorButton(
        "page_indicator", style=discord.ButtonStyle.gray, disabled=True, row=1
      ),
      pages.PaginatorButton("next", label="   ➡   ", style=discord.ButtonStyle.primary, disabled=bool(len(set_badges) <= 30), row=1),
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
        await ctx.followup.send(embed=embed, files=chunk, ephemeral=False)
      else:
        await ctx.followup.send(files=chunk, ephemeral=False)


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
@commands.check(access_check)
async def completion(ctx:discord.ApplicationContext, public:str, category:str, color:str):

  public = bool(public == "yes")
  await ctx.defer(ephemeral=not public)

  all_badges = os.listdir("./images/badges/")
  user_badges = db_get_user_badges(ctx.author.id)

  # Pull data using the queries.
  all_rows = []
  if category == 'affiliation':
    all_rows = queries_badge_completion.by_affiliation(ctx.author.id)
  elif category == 'franchise':
    all_rows = queries_badge_completion.by_franchise(ctx.author.id)
  elif category == 'time_period':
    all_rows = queries_badge_completion.by_time_period(ctx.author.id)
  elif category == 'type':
    all_rows = queries_badge_completion.by_type(ctx.author.id)
  all_rows = _append_featured_completion_badges(ctx.author.id, all_rows, category)

  # Format data for the returned embed
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
    if category == "affiliation":
      badges = db_get_random_badges_from_user_by_affiliations(user_id)
    elif category == "franchise":
      badges = db_get_random_badges_from_user_by_franchises(user_id)
    elif category == "time_period":
      badges = db_get_random_badges_from_user_by_time_periods(user_id)
    elif category == "type":
      badges = db_get_random_badges_from_user_by_types(user_id)
    else:
      badges = {}

    for r in report:
      if r['name'] in badges:
        r['featured_badge'] = badges.get(r['name'])
        return report


#   _________
#  /   _____/ ________________  ______ ______   ___________
#  \_____  \_/ ___\_  __ \__  \ \____ \\____ \_/ __ \_  __ \
#  /        \  \___|  | \// __ \|  |_> >  |_> >  ___/|  | \/
# /_______  /\___  >__|  (____  /   __/|   __/ \___  >__|
#         \/     \/           \/|__|   |__|        \/
class ScrapButton(discord.ui.Button):
  def __init__(self, user_id, badge_to_add, badges_to_scrap):
    self.user_id = user_id
    self.badge_to_add = badge_to_add
    self.badges_to_scrap = badges_to_scrap
    super().__init__(
      label="     Scrap     ",
      style=discord.ButtonStyle.primary,
      row=2
    )

  async def callback(self, interaction: discord.Interaction):
    # Re-check conditions to ensure this action is still valid
    # Ensure user still owns the badges
    user_badges = db_get_user_badges(self.user_id)
    user_badge_filenames = [b['badge_filename'] for b in user_badges]
    owned_user_badges = [b for b in self.badges_to_scrap if b['badge_filename'] in user_badge_filenames]
    # Ensure they haven't performed another scrap within the time period
    time_check_fail = True
    last_scrap_time = db_get_scrap_last_timestamp(self.user_id)
    if last_scrap_time:
      to_zone = tz.tzlocal()
      last_scrap_time.replace(tzinfo=to_zone)
      current_time = datetime.now()
      if last_scrap_time.date() < current_time.date():
        time_check_fail = False
    else:
        time_check_fail = False

    if (len(owned_user_badges) != 3) or (time_check_fail):
      await interaction.response.edit_message(
        embed=discord.Embed(
          title="Error",
          description=f"There's been a problem with this scrap request.\n\nEither you no longer possess the badges outlined or another scrap has been performed in the intervening time.",
          color=discord.Color.red()
        ),
        view=None,
        attachments=[]
      )
    else:
      await interaction.response.edit_message(
        embed=discord.Embed(
          title="Scrapper initiated!",
          description="Your badges are being broken down into their constituent components.\nJust a moment please...",
          color=discord.Color.teal()
        ),
        view=None,
        attachments=[]
      )

      # Cancel any existing trades that may be out requesting or offering these badges from this user
      trades_to_cancel = db_get_trades_to_cancel_from_scrapped_badges(self.user_id, self.badges_to_scrap)
      await _cancel_invalid_scrapped_trades(trades_to_cancel)

      # Do the actual scrappage
      db_perform_badge_scrap(self.user_id, self.badge_to_add, self.badges_to_scrap)

      # Post message about successful scrap
      scrapper_gif = await generate_badge_scrapper_result_gif(self.user_id, self.badge_to_add)

      scrap_complete_messages = [
        "{} reaches into AGIMUS' warm scrap hole and pulls out a shiny new badge!",
        "{} uses the Scrap-o-matic! Three old badges become one shiny new badge. That's science, baby!",
        "{} has replicator rations to spare, so they've scrapped some old badges for a new one!",
        "{} performs some strange gestures in front of the replicator. They hold a new badge above their head!",
        "{} adds 3 old crusty badges to the scrapper, and yanks out a new shiny badge!",
        "{} is using the scrapper on the clock. Don't tell the captain!",
        "{} is donating three old badges to the void, and gets a brand new badge in return!",
        "{} suspiciously shoves three badges into the slot and hastily pulls a fresh badge out, hoping you didn't see anything.",
        "Scrap complete! {} has recycled three old badges into one new badge!",
        "{} has used the badge scrapper! Tonight is the night when 3 become 1 🎶"
      ]

      embed = discord.Embed(
        title="Scrap complete!",
        description=random.choice(scrap_complete_messages).format(interaction.user.mention),
        color=discord.Color.teal()
      )
      embed.add_field(
        name="Scrapped badges: ❌",
        value="\n".join(["~~"+b['badge_name']+"~~" for b in self.badges_to_scrap]),
        inline=False
      )
      embed.add_field(
        name="New badge: 🆕",
        value=f"🌟 **{self.badge_to_add['badge_name']}** [(badge details)]({self.badge_to_add['badge_url']})",
        inline=False
      )
      embed.set_image(url=f"attachment://scrap_{self.user_id}.gif")
      await interaction.channel.send(embed=embed, file=scrapper_gif)

class CancelScrapButton(discord.ui.Button):
  def __init__(self):
    super().__init__(
      label="     Cancel     ",
      style=discord.ButtonStyle.red,
      row=2
    )

  async def callback(self, interaction:discord.Interaction):
    await interaction.response.edit_message(
      embed=discord.Embed(
        title="Scrap cancelled!",
        description="You may initiate a new scrap with `/badges scrap` at any time.",
        color=discord.Color.teal()
      ),
      view=None,
      attachments=[]
    )

class ScrapCancelView(discord.ui.View):
  def __init__(self, user_id, badge_to_add, badges_to_scrap):
    super().__init__()
    self.add_item(CancelScrapButton())
    self.add_item(ScrapButton(user_id, badge_to_add, badges_to_scrap))


@badge_group.command(
  name="scrap",
  description="Turn in 3 unlocked badges for 1 new random badge. One scrap allowed every 24 hours."
)
@option(
  name="first_badge",
  description="First badge to scrap",
  required=True,
  autocomplete=scrapper_autocomplete
)
@option(
  name="second_badge",
  description="Second badge to scrap",
  required=True,
  autocomplete=scrapper_autocomplete
)
@option(
  name="third_badge",
  description="Third badge to scrap",
  required=True,
  autocomplete=scrapper_autocomplete
)
@commands.check(access_check)
async def scrap(ctx:discord.ApplicationContext, first_badge:str, second_badge:str, third_badge:str):
  """
  This function executes the scrap for the /badge scrap command
  :param ctx:
  :param first_badge: The name of the first badge to scrap.
  :param second_badge: The name of the second badge to scrap.
  :param third_badge: The name of the third badge to scrap.
  :return:
  """
  await ctx.defer(ephemeral=True)
  user_id = ctx.interaction.user.id

  selected_badges = [first_badge, second_badge, third_badge]
  unlocked_user_badges = db_get_user_unlocked_badges(user_id)
  unlocked_user_badge_names = [b['badge_name'] for b in unlocked_user_badges]

  selected_user_badges = [b for b in selected_badges if b in unlocked_user_badge_names]

  if len(selected_user_badges) != 3:
    await ctx.followup.send(embed=discord.Embed(
      title="Invalid Selection",
      description=f"You must own all of the badges you've selected to scrap and they must be unlocked!",
      color=discord.Color.red()
    ), ephemeral=True)
    return

  if len(selected_user_badges) > len(set(selected_user_badges)):
    await ctx.followup.send(embed=discord.Embed(
      title="Invalid Selection",
      description=f"All badges selected must be unique!",
      color=discord.Color.red()
    ), ephemeral=True)
    return

  restricted_badges = [b for b in selected_user_badges if b in [b['badge_name'] for b in SPECIAL_BADGES]]
  if restricted_badges:
    await ctx.followup.send(embed=discord.Embed(
      title="Invalid Selection",
      description=f"You cannot scrap the following: {','.join(restricted_badges)}!",
      color=discord.Color.red()
    ), ephemeral=True)
    return

  # If all basics checks pass,
  # check that they're within the allowed time window
  last_scrap_time = db_get_scrap_last_timestamp(user_id)
  if last_scrap_time:
    time_check_fail = True

    to_zone = tz.tzlocal()
    last_scrap_time.replace(tzinfo=to_zone)
    current_time = datetime.now()
    current_time.replace(tzinfo=to_zone)
    if last_scrap_time.date() < current_time.date():
      time_check_fail = False

    if time_check_fail:
      midnight_tomorrow = current_time.date() + timedelta(days=1)
      midnight_tomorrow = datetime.combine(midnight_tomorrow, datetime.min.time())

      humanized_time_left = humanize.precisedelta(midnight_tomorrow - current_time, suppress=["days"])
      await ctx.followup.send(embed=discord.Embed(
        title="Scrapper recharging, please wait.",
        description=f"Reset time at Midnight Pacific ({humanized_time_left} left).",
        color=discord.Color.red()
      ), ephemeral=True)
      return

  # If time check okay, select a new random badge
  all_possible_badges = [b['badge_name'] for b in all_badge_info]
  special_badge_names = [b['badge_name'] for b in SPECIAL_BADGES]
  # Don't give them a badge they already have or a special badge
  all_user_badge_names = [b['badge_name'] for b in db_get_user_badges(user_id)]
  valid_choices = [b for b in all_possible_badges if b not in all_user_badge_names and b not in special_badge_names]
  if len(valid_choices) == 0:
    await ctx.respond(embed=discord.Embed(
      title="You already have *ALL BADGES!?!*",
      description=f"Amazing! You've collected every unique badge we have, so scrapping is unnecessary. Get it player.",
      color=discord.Color.random()
    ), ephemeral=True)
    return

  badge_choice = random.choice(valid_choices)

  badge_to_add = db_get_badge_info_by_name(badge_choice)
  badges_to_scrap = [db_get_badge_info_by_name(b) for b in selected_user_badges]

  # Check for wishlist badges
  wishlist_matches_groups = [m for m in (db_get_wishlist_badge_matches(b['badge_filename']) for b in badges_to_scrap) if m]

  # Generate Animated Scrapper Gif
  scrapper_confirm_gif = await generate_badge_scrapper_confirmation_gif(user_id, badges_to_scrap)

  # Create the first page
  scrap_embed_description = "** This cannot be undone.\n**" + str("\n".join(selected_user_badges))
  if len(wishlist_matches_groups):
    scrap_embed_description += "\n\n**NOTE:** One or more of the badges you're looking to scrap are on other user's wishlists! Check the following pages for more details, you may want to reach out to see if they'd like to trade!"

  scrap_embed = discord.Embed(
    title="Are you sure you want to scrap these badges?",
    description=scrap_embed_description,
    color=discord.Color.teal()
  )
  scrap_embed.set_image(url=f"attachment://scrap_{user_id}-confirm.gif")
  scrap_page = pages.Page(
    embeds=[scrap_embed],
    files=[scrapper_confirm_gif]
  )

  # Iterate over any wishlist matches if present and add them to paginator pages
  scrapper_pages = [scrap_page]
  for wishlist_matches in wishlist_matches_groups:
    if len(wishlist_matches):
      badge_filename = wishlist_matches[0]['badge_filename']
      badge_info = db_get_badge_info_by_filename(badge_filename)
      users = [await bot.current_guild.fetch_member(m['user_discord_id']) for m in wishlist_matches]
      wishlist_match_embed = discord.Embed(
        title=f"The following users want {badge_info['badge_name']}",
        description="\n".join([u.mention for u in users]),
        color=discord.Color.teal()
      )
      scrapper_pages.append(wishlist_match_embed)

  # Send scrapper paginator
  view = ScrapCancelView(user_id, badge_to_add, badges_to_scrap)
  paginator = pages.Paginator(
    pages=scrapper_pages,
    custom_buttons=[
      pages.PaginatorButton("prev", label="    ⬅     ", style=discord.ButtonStyle.primary, row=1),
      pages.PaginatorButton(
        "page_indicator", style=discord.ButtonStyle.gray, disabled=True, row=1
      ),
      pages.PaginatorButton("next", label="     ➡    ", style=discord.ButtonStyle.primary, row=1),
    ],
    use_default_buttons=False,
    custom_view=view
  )
  await paginator.respond(ctx.interaction, ephemeral=True)


async def _cancel_invalid_scrapped_trades(trades_to_cancel):
  # Iterate through to cancel
  for trade in trades_to_cancel:
    db_cancel_trade(trade)
    requestee = await bot.current_guild.fetch_member(trade['requestee_id'])
    requestor = await bot.current_guild.fetch_member(trade['requestor_id'])

    offered_badge_names, requested_badge_names = get_offered_and_requested_badge_names(trade)

    # Give notice to Requestee
    user = get_user(requestee.id)
    if user["receive_notifications"]:
      try:
        requestee_embed = discord.Embed(
          title="Trade Canceled",
          description=f"Just a heads up! Your pending trade initiated by {requestor.mention} was canceled because one or more of the badges involved were scrapped!",
          color=discord.Color.purple()
        )
        requestee_embed.add_field(
          name=f"Offered by {requestor.display_name}",
          value=offered_badge_names
        )
        requestee_embed.add_field(
          name=f"Requested from {requestee.display_name}",
          value=requested_badge_names
        )
        requestee_embed.set_footer(
          text="Note: You can use /settings to enable or disable these messages."
        )
        await requestee.send(embed=requestee_embed)
      except discord.Forbidden as e:
        logger.info(f"Unable to send trade cancelation message to {requestee.display_name}, they have their DMs closed.")
        pass

    # Give notice to Requestor
    user = get_user(requestor.id)
    if user["receive_notifications"]:
      try:
        requestor_embed = discord.Embed(
          title="Trade Canceled",
          description=f"Just a heads up! Your pending trade requested from {requestee.mention} was canceled because one or more of the badges involved were scrapped!",
          color=discord.Color.purple()
        )
        requestor_embed.add_field(
          name=f"Offered by {requestor.display_name}",
          value=offered_badge_names
        )
        requestor_embed.add_field(
          name=f"Requested from {requestee.display_name}",
          value=requested_badge_names
        )
        requestor_embed.set_footer(
          text="Note: You can use /settings to enable or disable these messages."
        )
        await requestor.send(embed=requestor_embed)
      except discord.Forbidden as e:
        logger.info(f"Unable to send trade cancelation message to {requestor.display_name}, they have their DMs closed.")
        pass

# .____                  __
# |    |    ____   ____ |  | ____ ________
# |    |   /  _ \ /  _ \|  |/ /  |  \____ \
# |    |__(  <_> |  <_> )    <|  |  /  |_> >
# |_______ \____/ \____/|__|_ \____/|   __/
#         \/                 \/     |__|
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
    badge_count = db_get_badge_count_by_filename(badge['badge_filename'])
    if (badge):
      affiliations = [
        a['affiliation_name']
        for a in db_get_badge_affiliations_by_badge_name(name)
      ]
      types = [
        t['type_name']
        for t in db_get_badge_types_by_badge_name(name)
      ]

      description = f"Quadrant: **{badge['quadrant']}**\n"
      description += f"Time Period: **{badge['time_period']}**\n"
      if affiliations:
        description += f"Affiliations: **{', '.join(affiliations)}**\n"
      if types:
        description += f"Types: **{', '.join(types)}**\n"
      description += f"Franchise: **{badge['franchise']}**\n"
      description += f"Reference: **{badge['reference']}**\n\n"
      description += f"Total number collected on The USS Hood: **{badge_count}**\n\n"
      description += f"{badge['badge_url']}"

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
  top_wishlisted = [res for res in results["most_wishlisted"]]
  top_locked = [res for res in results["most_locked"]]
  embed = discord.Embed(color=discord.Color.random(), description="", title="")
  embed.add_field(name=f"{get_emoji('combadge')} Total badges collected\non the USS Hood", value=f"{total_badges}\n⠀", inline=True)
  embed.add_field(name="⠀", value="⠀", inline=True)
  embed.add_field(name=f"{get_emoji('combadge')} Badges collected in\nthe last 24 hours", value=f"{badges_today}\n⠀", inline=True)
  embed.add_field(name=f"{get_emoji('combadge')} Top 5 most collected", value=str("\n".join(f"{t['badge_filename'].replace('_', ' ').replace('.png', '')} ({t['count']})" for t in top_three)), inline=True)
  embed.add_field(name="⠀", value="⠀", inline=True)
  embed.add_field(name=f"{get_emoji('combadge')} Top 5 badge collectors", value=str("\n".join(f"{t['name']} ({t['count']})" for t in top_collectors)), inline=True)
  embed.add_field(name=f"{get_emoji('combadge')} Top 5 most wishlisted", value=str("\n".join(f"{t['badge_name']} ({t['count']})" for t in top_wishlisted)), inline=True)
  embed.add_field(name="⠀", value="⠀", inline=True)
  embed.add_field(name=f"{get_emoji('combadge')} Top 5 most locked", value=str("\n".join(f"{t['badge_name']} ({t['count']})" for t in top_locked)), inline=True)
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
@option(
  "reason",
  str,
  description="The reason for the gift!",
  required=False
)
async def gift_badge(ctx:discord.ApplicationContext, user:discord.User, reason:str=""):
  """
  give a random badge to a user
  """
  await ctx.defer(ephemeral=True)

  notification_channel_id = get_channel_id(config["handlers"]["xp"]["notification_channel"])
  logger.info(f"{ctx.author.display_name} is attempting to {Style.BRIGHT}gift a random badge{Style.RESET_ALL} to {user.display_name}")

  badge = give_user_badge(user.id)
  if badge is None:
    await ctx.respond(embed=discord.Embed(
      title="This user already has *ALL BADGES!?!*",
      description=f"Amazing! This user already has every badge we've got! Gifting unnecessary/impossible!",
      color=discord.Color.random()
    ), ephemeral=True)
    return

  # Lock the badge if it was in their wishlist
  db_autolock_badges_by_filenames_if_in_wishlist(user.id, [badge])
  # Remove any badges the user may have on their wishlist that they now possess
  db_purge_users_wishlist(user.id)

  channel = bot.get_channel(notification_channel_id)
  embed_title = "You got rewarded a free badge!"
  thumbnail_image = random.choice(config["handlers"]["xp"]["celebration_images"])
  embed_description = f"{user.mention} has been gifted a badge by {ctx.author.mention}!"
  if reason != "":
    message = f"{user.mention} - {strip_emoji(reason)}"
  else:
    message = f"{user.mention} - Nice work, whatever you did!"
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

  badge_info = db_get_badge_info_by_name(specific_badge)
  if badge_info == None:
    await ctx.respond(f"Can't send {specific_badge}, it doesn't look like that badge exists!", ephemeral=True)
    return
  else:
    user_badges = db_get_user_badges(user.id)
    badge_filename = badge_info['badge_filename']
    if specific_badge not in [b['badge_name'] for b in user_badges]:
      give_user_specific_badge(user.id, badge_filename)
      # Lock the badge if it was in their wishlist
      db_autolock_badges_by_filenames_if_in_wishlist(user.id, [badge_filename])
      # Remove any badges the user may have on their wishlist that they now possess
      db_purge_users_wishlist(user.id)

  channel = bot.get_channel(notification_channel_id)
  embed_title = "You got rewarded a badge!"
  thumbnail_image = random.choice(config["handlers"]["xp"]["celebration_images"])
  embed_description = f"{user.mention} has been gifted a badge by {ctx.author.mention}!"
  message = f"{user.mention} - Nice work, you got a free badge!"
  await send_badge_reward_message(message, embed_description, embed_title, channel, thumbnail_image, badge_filename, user)
  await ctx.respond("Your gift has been sent!", ephemeral=True)


@gift_specific_badge.error
async def gift_specific_badge_error(ctx, error):
  if isinstance(error, commands.MissingPermissions):
    await ctx.respond("Sorry, you do not have permission to do that!", ephemeral=True)
  else:
    await ctx.respond("Sensoars indicate some kind of ...*error* has occured!", ephemeral=True)


async def send_badge_reward_message(message:str, embed_description:str, embed_title:str, channel, thumbnail_image:str, badge_filename:str, user:discord.User):
  embed=discord.Embed(title=embed_title, description=embed_description, color=discord.Color.random())

  if badge_filename != None:
    badge_info = db_get_badge_info_by_filename(badge_filename)
    badge_name = badge_info['badge_name']
    badge_url = badge_info['badge_url']

    embed.add_field(
      name=badge_name,
      value=badge_url,
      inline=False
    )
    embed_filename = str(user.id) + str(abs(hash(badge_name))) + ".png"
    discord_image = discord.File(fp=f"./images/badges/{badge_filename}", filename=embed_filename)
    embed.set_image(url=f"attachment://{embed_filename}")
    embed.set_footer(text="See all your badges by typing '/badges showcase' - disable this by typing '/settings'")

  embed.set_thumbnail(url=thumbnail_image)

  message = await channel.send(content=message, file=discord_image, embed=embed)
  # Add + emoji so that users can add it as well to add the badge to their wishlist
  await message.add_reaction("✅")


# ________                      .__
# \_____  \  __ __   ___________|__| ____   ______
#  /  / \  \|  |  \_/ __ \_  __ \  |/ __ \ /  ___/
# /   \_/.  \  |  /\  ___/|  | \/  \  ___/ \___ \
# \_____\ \_/____/  \___  >__|  |__|\___  >____  >
#        \__>           \/              \/     \/

def give_user_badge(user_discord_id:int):
  """ pick a badge, update badges DB, return badge name """
  # list files in images/badges directory
  badges = os.listdir("./images/badges/")
  # get the users current badges
  user_badges = [b['badge_filename'] for b in db_get_user_badges(user_discord_id)]
  special_badge_filenames = [b['badge_filename'] for b in SPECIAL_BADGES]
  valid_choices = [b for b in badges if b not in user_badges and b not in special_badge_filenames]
  if len(valid_choices) == 0:
    return None

  badge_choice = random.choice(valid_choices)
  with AgimusDB() as query:
    sql = "INSERT INTO badges (user_discord_id, badge_filename) VALUES (%s, %s)"
    vals = (user_discord_id, badge_choice)
    query.execute(sql, vals)
  return badge_choice

def give_user_specific_badge(user_discord_id:int, badge_choice:str):
  with AgimusDB() as query:
    sql = "INSERT INTO badges (user_discord_id, badge_filename) VALUES (%s, %s)"
    vals = (user_discord_id, badge_choice)
    query.execute(sql, vals)
  return badge_choice

def run_badge_stats_queries():
  queries = {
    "total_badges" : "SELECT COUNT(id) as count FROM badges;",
    "badges_today" : "SELECT COUNT(id) as count FROM badges WHERE time_created > NOW() - INTERVAL 1 DAY;",
    "top_collectors" : "SELECT name, COUNT(badges.id) as count FROM users JOIN badges ON users.discord_id = badges.user_discord_id GROUP BY discord_id ORDER BY COUNT(badges.id) DESC LIMIT 5;",
    "most_wishlisted" : "SELECT b_i.badge_name, COUNT(b_w.id) as count FROM badge_info AS b_i JOIN badge_wishlists AS b_w WHERE b_i.badge_filename = b_w.badge_filename GROUP BY b_w.badge_filename ORDER BY COUNT(b_w.badge_filename) DESC, b_i.badge_name ASC LIMIT 5;",
    "most_locked" : "SELECT b_i.badge_name, COUNT(b.locked) as count FROM badge_info AS b_i JOIN badges AS b ON b_i.badge_filename = b.badge_filename WHERE b.locked = 1 GROUP BY b.badge_filename ORDER BY COUNT(b.locked) DESC, b_i.badge_name ASC LIMIT 5;",
  }

  results = {}
  with AgimusDB(dictionary=True) as query:
    # Run most collected while filtering out special badges
    special_badge_filenames = [b['badge_filename'] for b in SPECIAL_BADGES]
    format_strings = ','.join(['%s'] * len(special_badge_filenames))
    sql = "SELECT badge_filename, COUNT(id) as count FROM badges WHERE badge_filename NOT IN (%s) GROUP BY badge_filename ORDER BY count DESC LIMIT 5;"
    query.execute(sql % format_strings, tuple(special_badge_filenames))
    results["most_collected"] = query.fetchall()

    # Run remaining queries
    for name,sql in queries.items():
      query.execute(sql)
      results[name] = query.fetchall()

  return results


def db_get_trades_to_cancel_from_scrapped_badges(user_id, badges_to_scrap):
  badge_filenames = [b['badge_filename'] for b in badges_to_scrap]
  with AgimusDB(dictionary=True) as query:
    # All credit for this query to Danma! Praise be!!!
    sql = '''
      SELECT t.*
      FROM trades as t
      LEFT JOIN trade_offered `to` ON t.id = to.trade_id
      LEFT JOIN trade_requested `tr` ON t.id = tr.trade_id
      WHERE t.status IN ('pending','active')
      AND (
        (t.requestor_id = %s AND to.badge_filename IN (%s, %s, %s))
        OR
        (t.requestee_id = %s AND tr.badge_filename IN (%s, %s, %s))
      )
    '''
    vals = (
      user_id, badge_filenames[0], badge_filenames[1], badge_filenames[2],
      user_id, badge_filenames[0], badge_filenames[1], badge_filenames[2]
    )
    query.execute(sql, vals)
    trades = query.fetchall()
  return trades
