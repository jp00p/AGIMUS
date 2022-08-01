import functools
import textwrap
import time
import math

from common import *


# ___________.__                              .___.__
# \__    ___/|  |_________   ____ _____     __| _/|__| ____    ____
#   |    |   |  |  \_  __ \_/ __ \\__  \   / __ | |  |/    \  / ___\
#   |    |   |   Y  \  | \/\  ___/ / __ \_/ /_/ | |  |   |  \/ /_/  >
#   |____|   |___|  /__|    \___  >____  /\____ | |__|___|  /\___  /
#                 \/            \/     \/      \/         \//_____/
def to_thread(func):
  @functools.wraps(func)
  async def wrapper(*args, **kwargs):
    loop = asyncio.get_event_loop()
    wrapped = functools.partial(func, *args, **kwargs)
    return await loop.run_in_executor(None, wrapped)
  return wrapper


# ___________                  .___.__
# \__    ___/___________     __| _/|__| ____    ____
#   |    |  \_  __ \__  \   / __ | |  |/    \  / ___\
#   |    |   |  | \// __ \_/ /_/ | |  |   |  \/ /_/  >
#   |____|   |__|  (____  /\____ | |__|___|  /\___  /
#                       \/      \/         \//_____/
@to_thread
def generate_badge_trade_showcase(badge_list, id, title, footer):
  text_wrapper = textwrap.TextWrapper(width=22)
  title_font = ImageFont.truetype("fonts/tng_credits.ttf", 68)
  credits_font = ImageFont.truetype("fonts/tng_credits.ttf", 42)
  badge_font = ImageFont.truetype("fonts/context_bold.ttf", 28)

  badge_size = 200
  badge_padding = 40
  badge_margin = 10
  badge_slot_size = badge_size + (badge_padding * 2) # size of badge slot size (must be square!)
  badges_per_row = 6

  base_width = (badge_slot_size+badge_margin) * badges_per_row
  base_height = math.ceil((len(badge_list) / badges_per_row)) * (badge_slot_size + badge_margin)

  header_height = badge_size
  image_padding = 50

  # create base image to paste all badges on to
  badge_base_image = Image.new("RGBA", (base_width+(image_padding*2), base_height+header_height+(image_padding*2)), (200, 200, 200))
  badge_bg_image = Image.open("./images/trades/assets/trade_bg.jpg")

  base_w, base_h = badge_base_image.size
  bg_w, bg_h = badge_bg_image.size

  for i in range(0, base_w, bg_w):
    for j in range(0, base_h, bg_h):
      badge_base_image.paste(badge_bg_image, (i, j))

  draw = ImageDraw.Draw(badge_base_image)

  draw.text( (base_width/2 + image_padding, 100), title, fill="white", font=title_font, anchor="mm", align="center")
  draw.text( (base_width/2 + image_padding, base_h-50), footer, fill="white", font=credits_font, anchor="mm", align="center",stroke_width=2,stroke_fill="#000000")


  # Center positioning. Move start_x to center of image then - 1/2 of the width of each image * the length of images
  half_badge_slot_size = int(badge_slot_size / 2)
  start_x = int((base_width/2 + image_padding/2) - (half_badge_slot_size * len(badge_list)))

  current_x = start_x
  current_y = header_height
  counter = 0
  badge_border_color = random.choice(["#774466", "#6688CC", "#BB4411", "#0011EE"])

  for badge in badge_list:
    # todo: create slot border/stuff, lcars stuff

    # slot
    s = Image.new("RGBA", (badge_slot_size, badge_slot_size), (0, 0, 0, 0))
    badge_draw = ImageDraw.Draw(s)
    badge_draw.rounded_rectangle( (0, 0, badge_slot_size, badge_slot_size), fill="#000000", outline=badge_border_color, width=4, radius=32 )

    # badge
    b = Image.open(f"./images/badges/{badge}").convert("RGBA")
    b = b.resize((190, 190))

    w, h = b.size # badge size
    offset_x = min(0, (badge_size+badge_padding)-w) # center badge x
    offset_y = 5
    badge_name = text_wrapper.wrap(badge.replace("_", " ").replace(".png", ""))
    wrapped_badge_name = ""
    for i in badge_name[:-1]:
      wrapped_badge_name = wrapped_badge_name + i + "\n"
    wrapped_badge_name += badge_name[-1]
    # add badge to slot
    s.paste(b, (badge_padding+offset_x, offset_y), b)
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

  badge_base_image.save(f"./images/trades/{id}.png")

  while True:
    time.sleep(0.05)
    if os.path.isfile(f"./images/trades/{id}.png"):
      break

  discord_image = discord.File(fp=f"./images/trades/{id}.png", filename=f"{id}.png")
  return discord_image


# __________                .__               __  .__
# \______   \_____     ____ |__| ____ _____ _/  |_|__| ____   ____
#  |     ___/\__  \   / ___\|  |/    \\__  \\   __\  |/  _ \ /    \
#  |    |     / __ \_/ /_/  >  |   |  \/ __ \|  | |  (  <_> )   |  \
#  |____|    (____  /\___  /|__|___|  (____  /__| |__|\____/|___|  /
#                 \//_____/         \/     \/                    \/
async def generate_paginated_badge_images(user:discord.User, type, all_badges, total_badges, title, collected, filename_prefix):
  user_display_name = user.display_name
  # total_user_badges = db_get_badge_count_for_user(user.id)

  max_per_image = 30
  all_pages = [all_badges[i:i + max_per_image] for i in range(0, len(all_badges), max_per_image)]
  total_pages = len(all_pages)
  badge_images = [
    await generate_badge_images(
      type,
      user_display_name,
      page,
      page_number + 1, # Account for zero index
      total_pages,
      total_badges,
      title,
      collected,
      filename_prefix
    )
    for page_number, page in enumerate(all_pages)
  ]
  return badge_images

@to_thread
def generate_badge_images(type, user_display_name, page, page_number, total_pages, total_user_badges, title, collected, filename_prefix):

  if type == "showcase":
    color = "green"
    title_color = "#99B98D"
    highlight_color = "#54B145"
  if type == "sets":
    color = "teal"
    title_color = "#8DB9B5"
    highlight_color = "#2D698D"

  text_wrapper = textwrap.TextWrapper(width=22)
  title_font = ImageFont.truetype("fonts/lcars3.ttf", 110)
  if len(user_display_name) > 16:
    title_font = ImageFont.truetype("fonts/lcars3.ttf", 90)
  if len(user_display_name) > 21:
    title_font = ImageFont.truetype("fonts/lcars3.ttf", 82)
  collected_font = ImageFont.truetype("fonts/lcars3.ttf", 100)
  total_font = ImageFont.truetype("fonts/lcars3.ttf", 54)
  page_number_font = ImageFont.truetype("fonts/lcars3.ttf", 80)
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

  # If we're generating just one page we want the rows to simply expand to only what's necessary
  # Otherwise if there's multiple pages we want to have all of them be consistent
  if page_number == 1 and total_pages == 1:
    number_of_rows = math.ceil((len(page) / badges_per_row)) - 1
  else:
    number_of_rows = 4

  base_height = base_header_height + (base_row_height * number_of_rows) + base_footer_height

  # create base image to paste all badges on to
  badge_base_image = Image.new("RGBA", (base_width, base_height), (0, 0, 0))
  base_header_image = Image.open(f"./images/templates/badges/badge_set_header_{color}.png")
  base_row_image = Image.open(f"./images/templates/badges/badge_set_row_{color}.png")
  base_footer_image = Image.open(f"./images/templates/badges/badge_set_footer_{color}.png")

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

  draw.text( (100, 65), title, fill=title_color, font=title_font, align="left")
  draw.text( (590, base_height - 125), collected, fill=highlight_color, font=collected_font, align="left")
  draw.text( (32, base_height - 90), f"{total_user_badges}", fill=highlight_color, font=total_font, align="left")
  draw.text( (base_width - 370, base_height - 115), f"PAGE {'{:02d}'.format(page_number)} OF {'{:02d}'.format(total_pages)}", fill=highlight_color, font=page_number_font, align="right")

  start_x = 100
  current_x = start_x
  current_y = 245
  counter = 0

  for badge_record in page:
    badge_border_color = "#47AAB1"
    badge_text_color = "white"
    if type == 'sets' and not badge_record['in_user_collection']:
      badge_border_color = "#575757"
      badge_text_color = "#888888"

    # slot
    s = Image.new("RGBA", (badge_slot_size, badge_slot_size), (0, 0, 0, 0))
    badge_draw = ImageDraw.Draw(s)
    badge_draw.rounded_rectangle( (0, 0, badge_slot_size, badge_slot_size), fill="#000000", outline=badge_border_color, width=4, radius=32 )

    # badge
    b = Image.open(f"./images/badges/{badge_record['badge_filename']}").convert("RGBA")
    if type == 'sets' and not badge_record['in_user_collection']:
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

  badge_set_filepath = f"./images/profiles/{filename_prefix}{page_number}.png"
  badge_base_image.save(badge_set_filepath)

  while True:
    time.sleep(0.05)
    if os.path.isfile(badge_set_filepath):
      break

  discord_image = discord.File(badge_set_filepath, filename=f"{filename_prefix}{page_number}.png")
  return discord_image

# QUERIES
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
