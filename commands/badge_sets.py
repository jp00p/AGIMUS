import math
import textwrap
import time

from random import randint

from common import *

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
  description="Show off sets of your badges!"
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
@commands.check(access_check)
async def badge_sets(ctx:discord.ApplicationContext, public:str, category:str, selection:str):
  await ctx.defer(ephemeral=True)

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


  set = []
  for badge in all_set_badges:
    badge_filename = badge.replace(" ", "_").replace("/", "-").replace(":", "-")
    record = {
      'badge_name': badge,
      'badge_filename': f"{badge_filename}.png",
      'in_user_collection': badge in user_set_badges
    }
    set.append(record)

  category_title = category.replace("_", " ").title()

  await ctx.followup.send(embed=discord.Embed(
    title="One moment while we pull up your set!",
    color=discord.Color(0x2D698D)
  ), ephemeral=True)

  set_image = generate_badge_set_showcase_for_user(ctx.author, set, selection, category_title)


  random_titles = [
    "Gotta catch em all!",
    "He who has the most toys...",
    f"Currently {randint(10, 220)}% Encumbered",
    "My badges, let me show you them."
  ]

  public = bool(public == "yes")
  await ctx.followup.send(
    embed=discord.Embed(
      title=f"Badge Set - **{category_title}** - **{selection}**",
      description=f"{ctx.author.mention} has collected {len(user_set_badges)} of {len(all_set_badges)}!\n\nClick and Open Original to view the details below.",
      color=discord.Color(0x2D698D)
    )
    .set_image(url=f"attachment://badge_set.png")
    .set_footer(text=random.choice(random_titles)),
    file=set_image,
    ephemeral=not public
  )


# .___
# |   | _____ _____     ____   ____
# |   |/     \\__  \   / ___\_/ __ \
# |   |  Y Y  \/ __ \_/ /_/  >  ___/
# |___|__|_|  (____  /\___  / \___  >
#           \/     \//_____/      \/
def generate_badge_set_showcase_for_user(user:discord.User, badge_set, selection, category_title):
  total_user_badges = db_get_badge_count_for_user(user.id)

  text_wrapper = textwrap.TextWrapper(width=22)
  # badge_list = get_user_badges(user.id)
  title_font = ImageFont.truetype("fonts/lcars3.ttf", 110)
  if len(user.display_name) > 16:
    title_font = ImageFont.truetype("fonts/lcars3.ttf", 90)
  if len(user.display_name) > 21:
    title_font = ImageFont.truetype("fonts/lcars3.ttf", 82)
  collected_font = ImageFont.truetype("fonts/lcars3.ttf", 70)
  total_font = ImageFont.truetype("fonts/lcars3.ttf", 54)
  badge_font = ImageFont.truetype("fonts/context_bold.ttf", 28)

  badge_size = 200
  badge_padding = 40
  badge_margin = 10
  badge_slot_size = badge_size + (badge_padding * 2) # size of badge slot size (must be square!)
  badges_per_row = 6

  base_width = 1890
  base_header_height = 530
  base_row_height = 290
  base_footer_height = 200

  number_of_rows = math.ceil((len(badge_set) / badges_per_row)) - 1

  base_height = base_header_height + (base_row_height * number_of_rows) + base_footer_height
  # base_height = math.ceil((len(badge_set) / badges_per_row)) * (badge_slot_size + badge_margin)

  # create base image to paste all badges on to
  badge_base_image = Image.new("RGBA", (base_width, base_height), (0, 0, 0))
  base_header_image = Image.open("./images/templates/badge_sets/badge_set_header.png")
  base_row_image = Image.open("./images/templates/badge_sets/badge_set_row.png")
  base_footer_image = Image.open("./images/templates/badge_sets/badge_set_footer.png")

  # Start image with header
  badge_base_image.paste(base_header_image, (0, 0))

  # Stamp rows (if needed, header includes first row)
  base_current_y = base_header_height
  for i in range(number_of_rows):
    badge_base_image.paste(base_row_image, (0, base_current_y))
    base_current_y += base_row_height

  # Stamp footer
  badge_base_image.paste(base_footer_image, (0, base_current_y))

  draw = ImageDraw.Draw(badge_base_image)

  draw.text( (100, 65), f"{user.display_name.encode('ascii', errors='ignore').decode().strip()}'s Badge Set: {category_title} - {selection}", fill="#8DB9B5", font=title_font, align="left")
  draw.text( (590, base_height - 113), f"{len([b for b in badge_set if b['in_user_collection']])} OF {len(badge_set)}", fill="#47AAB1", font=collected_font, align="left")
  draw.text( (32, base_height - 90), f"{total_user_badges}", fill="#47AAB1", font=total_font, align="left")

  start_x = 100
  current_x = start_x
  current_y = 245
  counter = 0

  for badge_record in badge_set:
    badge_border_color = "#47AAB1"
    badge_text_color = "white"
    if not badge_record['in_user_collection']:
      badge_border_color = "#575757"
      badge_text_color = "#888888"

    # slot
    s = Image.new("RGBA", (badge_slot_size, badge_slot_size), (0, 0, 0, 0))
    badge_draw = ImageDraw.Draw(s)
    badge_draw.rounded_rectangle( (0, 0, badge_slot_size, badge_slot_size), fill="#000000", outline=badge_border_color, width=4, radius=32 )

    # badge
    b = Image.open(f"./images/badges/{badge_record['badge_filename']}").convert("RGBA")
    if not badge_record['in_user_collection']:
      # Create a mask layer to apply a 1/4th opacity to
      b2 = b.copy()
      b2.putalpha(64)
      b.paste(b2, b)
    b = b.resize((190, 190))

    w, h = b.size # badge size
    offset_x = min(0, (badge_size+badge_padding)-w) # center badge x
    offset_y = 5
    badge_name = text_wrapper.wrap(badge_record['badge_name'])
    wrapped_badge_name = ""
    for i in badge_name[:-1]:
      wrapped_badge_name = wrapped_badge_name + i + "\n"
    wrapped_badge_name += badge_name[-1]
    # add badge to slot
    s.paste(b, (badge_padding+offset_x+4, offset_y), b)
    badge_draw.text( (int(badge_slot_size/2), 222), f"{wrapped_badge_name}", fill=badge_text_color, font=badge_font, anchor="mm", align="center")

    # add slot to base image
    badge_base_image.paste(s, (current_x, current_y), s)

    current_x += badge_slot_size + badge_margin
    counter += 1

    if counter % badges_per_row == 0:
      # typewriter sound effects:
      current_x = start_x # ding!
      current_y += badge_slot_size + badge_margin # ka-chunk
      counter = 0 #...

  badge_set_filepath = f"./images/profiles/badge_set_{user.id}_{selection.lower().replace(' ', '-').replace('/', '-')}.png"
  badge_base_image.save(badge_set_filepath)

  while True:
    time.sleep(0.05)
    if os.path.isfile(badge_set_filepath):
      break

  discord_image = discord.File(badge_set_filepath, filename="badge_set.png")
  return discord_image



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

# General
def db_get_badge_count_for_user(user_id):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT count(*) FROM badges WHERE user_discord_id = %s
  '''
  vals = (user_id,)
  query.execute(sql, vals)
  result = query.fetchone()
  db.commit()
  query.close()
  db.close()

  return result['count(*)']
