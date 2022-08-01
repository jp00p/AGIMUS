import functools
import math
import textwrap
import time

from common import *
from utils.badge_utils import generate_paginated_badge_images, db_get_badge_count_for_user, db_set_user_badge_page_color_preference

from utils.check_channel_access import access_check

#    _____          __                                     .__          __
#   /  _  \  __ ___/  |_  ____   ____  ____   _____ ______ |  |   _____/  |_  ____
#  /  /_\  \|  |  \   __\/  _ \_/ ___\/  _ \ /     \\____ \|  | _/ __ \   __\/ __ \
# /    |    \  |  /|  | (  <_> )  \__(  <_> )  Y Y  \  |_> >  |_\  ___/|  | \  ___/
# \____|__  /____/ |__|  \____/ \___  >____/|__|_|  /   __/|____/\___  >__|  \___  >
#         \/                        \/            \/|__|             \/          \/
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

# _________                                           .___
# \_   ___ \  ____   _____   _____ _____    ____    __| _/
# /    \  \/ /  _ \ /     \ /     \\__  \  /    \  / __ |
# \     \___(  <_> )  Y Y  \  Y Y  \/ __ \|   |  \/ /_/ |
#  \______  /\____/|__|_|  /__|_|  (____  /___|  /\____ |
#         \/             \/      \/     \/     \/      \/
@bot.slash_command(
  name="badge_sets",
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
async def badge_sets(ctx:discord.ApplicationContext, public:str, category:str, selection:str, color:str):
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
    color=discord.Color(0x2D698D)
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

# ________                      .__
# \_____  \  __ __   ___________|__| ____   ______
#  /  / \  \|  |  \_/ __ \_  __ \  |/ __ \ /  ___/
# /   \_/.  \  |  /\  ___/|  | \/  \  ___/ \___ \
# \_____\ \_/____/  \___  >__|  |__|\___  >____  >
#        \__>           \/              \/     \/

# Affiliations
def db_get_all_affiliations():
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT distinct(affiliation_name) FROM badge_affiliation"
  query.execute(sql)
  rows = query.fetchall()
  db.commit()
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
        ON b_i.id = b_a.badge_id
      WHERE b_a.affiliation_name = %s
  '''
  vals = (affiliation,)
  query.execute(sql, vals)
  rows = query.fetchall()
  db.commit()
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
        ON b.badge_name = b_i.badge_filename
      JOIN badge_affiliation AS b_a
        ON b_i.id = b_a.badge_id
      WHERE b.user_discord_id = %s
        AND b_a.affiliation_name = %s
  '''
  vals = (user_id, affiliation)
  query.execute(sql, vals)
  rows = query.fetchall()
  db.commit()
  query.close()
  db.close()

  user_badges = [r['badge_name'] for r in rows]
  user_badges.sort()

  return user_badges

# Franchises
def db_get_all_franchises():
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT distinct(franchise) FROM badge_info"
  query.execute(sql)
  rows = query.fetchall()
  db.commit()
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
  db.commit()
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
        ON b.badge_name = b_i.badge_filename
      WHERE b.user_discord_id = %s
        AND b_i.franchise = %s
  '''
  vals = (user_id, franchise)
  query.execute(sql, vals)
  rows = query.fetchall()
  db.commit()
  query.close()
  db.close()

  user_badges = [r['badge_name'] for r in rows]
  user_badges.sort()

  return user_badges

# Time Periods
def db_get_all_time_periods():
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT distinct(time_period) FROM badge_info"
  query.execute(sql)
  rows = query.fetchall()
  db.commit()
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
  db.commit()
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
        ON b.badge_name = b_i.badge_filename
      WHERE b.user_discord_id = %s
        AND b_i.time_period = %s
  '''
  vals = (user_id, time_period)
  query.execute(sql, vals)
  rows = query.fetchall()
  db.commit()
  query.close()
  db.close()

  user_badges = [r['badge_name'] for r in rows]
  user_badges.sort()

  return user_badges

# Types
def db_get_all_types():
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT distinct(type_name) FROM badge_type"
  query.execute(sql)
  rows = query.fetchall()
  db.commit()
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
        ON b_i.id = b_t.badge_id
      WHERE b_t.type_name = %s
  '''
  vals = (type,)
  query.execute(sql, vals)
  rows = query.fetchall()
  db.commit()
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
        ON b.badge_name = b_i.badge_filename
      JOIN badge_type AS b_t
        ON b_i.id = b_t.badge_id
      WHERE b.user_discord_id = %s
        AND b_t.type_name = %s
  '''
  vals = (user_id, type)
  query.execute(sql, vals)
  rows = query.fetchall()
  db.commit()
  query.close()
  db.close()

  user_badges = [r['badge_name'] for r in rows]
  user_badges.sort()

  return user_badges
