import math
import textwrap
import time

from common import *

# from utils.check_channel_access import access_check

# AUTOCOMPLETE
async def autocomplete_affiliations(ctx:discord.AutocompleteContext):
  affiliations = db_get_all_affiliations()
  return [result for result in affiliations if ctx.value.lower() in result.lower()]

# COMMAND
@bot.slash_command(
  name="badge_sets",
  description="Show off sets of your badges!"
)
@option(
  name="affiliation",
  description="Which faction?",
  required=True,
  autocomplete=autocomplete_affiliations
)
async def badge_sets(ctx:discord.ApplicationContext, affiliation:str):
  await ctx.defer()

  affiliations = db_get_all_affiliations()
  if affiliation not in affiliations:
    await ctx.followup.send("Your entry was not in the list of affiliations!", ephemeral=True)
    return

  users_affiliation_badges = db_get_badges_user_has_from_affiliation(ctx.author.id, affiliation)
  # logger.info(pprint(users_affiliation_badges))

  all_affiliation_badges = db_get_all_affiliation_badges(affiliation)
  # logger.info(pprint(all_affiliation_badges))

  set = []
  for badge in all_affiliation_badges:
    badge_filename = badge.replace(" ", "_")#.replace("'", "’").replace("’")
    record = {
      'badge_name': badge,
      'badge_filename': f"{badge_filename}.png",
      'in_user_collection': badge in users_affiliation_badges
    }
    set.append(record)

  # logger.info(pprint(set))

  set_image = generate_badge_set_showcase_for_user(ctx.author, set, affiliation)

  await ctx.followup.send(file=set_image, ephemeral=False)


def db_get_all_affiliations():
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT distinct(affiliation_name) FROM badge_affiliation"
  query.execute(sql)
  rows = query.fetchall()
  db.commit()
  query.close()
  db.close()

  affiliations = [r['affiliation_name'] for r in rows]
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



# XXX REFACTOR ME AND PUT ME IN UTIL
# big expensive function that generates a nice grid of images for the user
# returns discord.file
def generate_badge_set_showcase_for_user(user:discord.User, badge_set, affiliation):
  text_wrapper = textwrap.TextWrapper(width=22)
  # badge_list = get_user_badges(user.id)
  title_font = ImageFont.truetype("fonts/tng_credits.ttf", 68)
  credits_font = ImageFont.truetype("fonts/tng_credits.ttf", 42)
  badge_font = ImageFont.truetype("fonts/context_bold.ttf", 28)

  badge_size = 200
  badge_padding = 40
  badge_margin = 10
  badge_slot_size = badge_size + (badge_padding * 2) # size of badge slot size (must be square!)
  badges_per_row = 6

  base_width = (badge_slot_size+badge_margin) * badges_per_row
  base_height = math.ceil((len(badge_set) / badges_per_row)) * (badge_slot_size + badge_margin)

  header_height = badge_size
  image_padding = 50

  # create base image to paste all badges on to
  # what if they have 900 badges?
  badge_base_image = Image.new("RGBA", (base_width+(image_padding*2), base_height+header_height+(image_padding*2)), (200, 200, 200))
  badge_bg_image = Image.open("./images/stars/" + random.choice(os.listdir("./images/stars/")))

  base_w, base_h = badge_base_image.size
  bg_w, bg_h = badge_bg_image.size

  for i in range(0, base_w, bg_w):
    for j in range(0, base_h, bg_h):
      badge_base_image.paste(badge_bg_image, (i, j))

  draw = ImageDraw.Draw(badge_base_image)

  draw.text( (base_width/2, 100), f"{user.display_name.encode('ascii', errors='ignore').decode().strip()}'s {affiliation } badges", fill="white", font=title_font, anchor="mm", align="center")
  draw.text( (base_width/2, base_h-50), f"Collected {len([b for b in badge_set if b['in_user_collection']])} of {len(badge_set)}", fill="white", font=credits_font, anchor="mm", align="center",stroke_width=2,stroke_fill="#000000")

  start_x = image_padding
  current_x = start_x
  current_y = header_height
  counter = 0
  badge_border_color = random.choice(["#774466", "#6688CC", "#BB4411", "#0011EE"])

  for badge_record in badge_set:
    # todo: create slot border/stuff, lcars stuff

    # slot
    s = Image.new("RGBA", (badge_slot_size, badge_slot_size), (0, 0, 0, 0))
    badge_draw = ImageDraw.Draw(s)
    badge_draw.rounded_rectangle( (0, 0, badge_slot_size, badge_slot_size), fill="#000000", outline=badge_border_color, width=4, radius=32 )

    # badge
    b = Image.open(f"./images/badges/{badge_record['badge_filename']}").convert("RGBA")
    if not badge_record['in_user_collection']:
      b = ImageOps.grayscale(b)
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
    badge_draw.text( (int(badge_slot_size/2), 222), f"{wrapped_badge_name}", fill="white", font=badge_font, anchor="mm", align="center")

    # add slot to base image
    badge_base_image.paste(s, (current_x, current_y), s)

    current_x += badge_slot_size + badge_margin
    counter += 1

    if counter % badges_per_row == 0:
      # typewriter sound effects:
      current_x = start_x # ding!
      current_y += badge_slot_size + badge_margin # ka-chunk
      counter = 0 #...

  badge_set_filepath = f"./images/profiles/badge_set_{user.id}_{affiliation.lower().replace(' ', '-')}.png"
  badge_base_image.save(badge_set_filepath)

  while True:
    time.sleep(0.05)
    if os.path.isfile(badge_set_filepath):
      break

  discord_image = discord.File(badge_set_filepath)
  return discord_image