import functools
import textwrap
import time
import math

from common import *

SPECIAL_BADGES = [
  {
    "badge_name": "Friends Of DeSoto",
    "badge_filename": "Friends_Of_DeSoto.png"
  },
  {
    "badge_name": "Captain Picard Day",
    "badge_filename": "Captain_Picard_Day.png"
  }
]


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
  max_per_image = 30
  all_pages = [all_badges[i:i + max_per_image] for i in range(0, len(all_badges), max_per_image)]
  total_pages = len(all_pages)
  badge_images = [
    await generate_badge_images(
      type,
      user,
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
def generate_badge_images(type, user, page, page_number, total_pages, total_user_badges, title, collected, filename_prefix):
  user_display_name = user.display_name
  color_preference = db_get_user_badge_page_color_preference(user.id, type)

  if color_preference == "green":
    title_color = "#99B98D"
    highlight_color = "#54B145"
  elif color_preference == "orange":
    title_color = "#BD9789"
    highlight_color = "#BA6F3B"
  elif color_preference == "purple":
    title_color = "#6455A1"
    highlight_color = "#9593B2"
  elif color_preference == "teal":
    title_color = "#8DB9B5"
    highlight_color = "#47AAB1"

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
  base_header_image = Image.open(f"./images/templates/badges/badge_page_header_{color_preference}.png")
  base_row_image = Image.open(f"./images/templates/badges/badge_page_row_{color_preference}.png")
  base_footer_image = Image.open(f"./images/templates/badges/badge_page_footer_{color_preference}.png")

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
    badge_border_color = highlight_color
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

    if badge_record['locked']:
      lock_icon = Image.open(f"./images/templates/badges/lock_icon.png").convert("RGBA")
      s.paste(lock_icon, (badge_slot_size-54, 16), lock_icon)

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


#   _________       __    _________                       .__          __  .__
#  /   _____/ _____/  |_  \_   ___ \  ____   _____ ______ |  |   _____/  |_|__| ____   ____
#  \_____  \_/ __ \   __\ /    \  \/ /  _ \ /     \\____ \|  | _/ __ \   __\  |/  _ \ /    \
#  /        \  ___/|  |   \     \___(  <_> )  Y Y  \  |_> >  |_\  ___/|  | |  (  <_> )   |  \
# /_______  /\___  >__|    \______  /\____/|__|_|  /   __/|____/\___  >__| |__|\____/|___|  /
#         \/     \/               \/             \/|__|             \/                    \/
async def generate_paginated_set_completion_images(user:discord.User, all_rows, total_badges, title, collected, filename_prefix):
  max_per_image = 7
  all_pages = [all_rows[i:i + max_per_image] for i in range(0, len(all_rows), max_per_image)]
  total_pages = len(all_pages)
  badge_images = [
    await generate_badge_completion_images(
      user,
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
def generate_badge_completion_images(user, page, page_number, total_pages, total_user_badges, title, collected, filename_prefix):
  user_display_name = user.display_name
  color_preference = db_get_user_badge_page_color_preference(user.id, "sets")

  if color_preference == "green":
    title_color = "#99B98D"
    highlight_color = "#54B145"
    bar_color = "#265F26"
  elif color_preference == "orange":
    title_color = "#BD9789"
    highlight_color = "#BA6F3B"
    bar_color = "#5F3C26"
  elif color_preference == "purple":
    title_color = "#6455A1"
    highlight_color = "#9593B2"
    bar_color = "#31265F"
  elif color_preference == "teal":
    title_color = "#8DB9B5"
    highlight_color = "#47AAB1"
    bar_color = "#265B5F"

  title_font = ImageFont.truetype("fonts/lcars3.ttf", 110)
  if len(user_display_name) > 16:
    title_font = ImageFont.truetype("fonts/lcars3.ttf", 90)
  if len(user_display_name) > 21:
    title_font = ImageFont.truetype("fonts/lcars3.ttf", 82)
  collected_font = ImageFont.truetype("fonts/lcars3.ttf", 100)
  total_font = ImageFont.truetype("fonts/lcars3.ttf", 54)
  page_number_font = ImageFont.truetype("fonts/lcars3.ttf", 80)

  row_title_font = ImageFont.truetype("fonts/lcars3.ttf", 160)
  row_tag_font = ImageFont.truetype("fonts/lcars3.ttf", 120)

  # Set up rows and dimensions
  row_height = 280
  row_width = 1700
  row_margin = 10

  base_width = 1890
  base_header_height = 530
  base_row_height = 290
  base_footer_height = 200

  # If we're generating just one page we want the rows to simply expand to only what's necessary
  # Otherwise if there's multiple pages we want to have all of them be consistent
  if len(page) == 0:
    number_of_rows = 0
  elif page_number == 1 and total_pages == 1:
    number_of_rows = len(page) - 1
  else:
    number_of_rows = 6

  base_height = base_header_height + (base_row_height * number_of_rows) + base_footer_height

  # create base image to paste all badges on to
  badge_base_image = Image.new("RGBA", (base_width, base_height), (0, 0, 0))
  base_header_image = Image.open(f"./images/templates/badges/badge_page_header_{color_preference}.png")
  base_row_image = Image.open(f"./images/templates/badges/badge_page_row_{color_preference}.png")
  base_footer_image = Image.open(f"./images/templates/badges/badge_page_footer_{color_preference}.png")

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

  start_x = 120
  current_x = start_x
  current_y = 245

  # If the user has no badges that are within sets of this category,
  # Stamp an empty message
  if len(page) == 0:
    row_image = Image.new("RGBA", (row_width, row_height), (0, 0, 0, 0))
    r_draw = ImageDraw.Draw(row_image)

    r_title = "No badges within inventory that match this set type."
    r_draw.rounded_rectangle( (0, 0, row_width, row_height), fill="#101010", outline=highlight_color, width=4, radius=32 )
    r_draw.text( (row_width / 2, row_height / 2), r_title, fill=title_color, font=row_tag_font, anchor="mm", align="left")

    badge_base_image.paste(row_image, (current_x, current_y - 35), row_image)
  else:
    for set_row in page:
      offset = 250

      # row
      row_image = Image.new("RGBA", (row_width, row_height), (0, 0, 0, 0))
      r_draw = ImageDraw.Draw(row_image)

      r_draw.rounded_rectangle( (0, 0, row_width, row_height), fill="#101010", outline="#101010", width=4, radius=32 )

      r_title = set_row['name']
      if r_title == None:
        continue # Skip this row if the category doesn't have a name

      r_draw.text( (offset, 50), r_title, fill=title_color, font=row_title_font, align="left")

      r_tag = f"{set_row['percentage']}% ({set_row['owned']} of {set_row['total']})"
      r_draw.text( (row_width - 20, 170), r_tag, fill=title_color, anchor="rb", font=row_tag_font, align="right")

      # draw percentage bar
      w, h = row_width - offset, 64
      x, y = offset, row_height - 64

      base_shape = (x, y, (w+x, h+y))
      r_draw.rectangle(base_shape, fill=bar_color)

      percentage_shape = (x, y, ((set_row['percentage'] / 100)*w)+x, h+y)
      r_draw.rectangle(percentage_shape, fill=highlight_color)

      # badge
      if 'featured_badge' in set_row:
        b = Image.open(f"./images/badges/{set_row['featured_badge']}").convert("RGBA")
        b = b.resize((190, 190))
        row_image.paste(b, (20, 50), b)

      # add row to base image
      badge_base_image.paste(row_image, (current_x, current_y), row_image)

      # Move y down to next row
      current_y += row_height + row_margin

  badge_completion_filepath = f"./images/profiles/{filename_prefix}{page_number}.png"
  badge_base_image.save(badge_completion_filepath)

  while True:
    time.sleep(0.05)
    if os.path.isfile(badge_completion_filepath):
      break

  discord_image = discord.File(badge_completion_filepath, filename=f"{filename_prefix}{page_number}.png")
  return discord_image


#   _________
#  /   _____/ ________________  ______ ______   ___________
#  \_____  \_/ ___\_  __ \__  \ \____ \\____ \_/ __ \_  __ \
#  /        \  \___|  | \// __ \|  |_> >  |_> >  ___/|  | \/
# /_______  /\___  >__|  (____  /   __/|   __/ \___  >__|
#         \/     \/           \/|__|   |__|        \/
@to_thread
def generate_badge_scrapper_confirmation_gif(user_id, badges_to_scrap):
  replicator_image = Image.open(f"./images/templates/scrap/replicator.png")

  base_image = Image.new("RGBA", (replicator_image.width, replicator_image.height), (0, 0, 0))
  base_image.paste(replicator_image, (0, 0))

  b1 = Image.open(f"./images/badges/{badges_to_scrap[0]['badge_filename']}").convert("RGBA").resize((125, 125))
  b2 = Image.open(f"./images/badges/{badges_to_scrap[1]['badge_filename']}").convert("RGBA").resize((125, 125))
  b3 = Image.open(f"./images/badges/{badges_to_scrap[2]['badge_filename']}").convert("RGBA").resize((125, 125))

  b_list = [b1, b2, b3]

  frames = []
  badge_position_x = 75
  badge_position_y = 130

  # Add 30 frames of just the replicator and the badges by themselves
  for n in range(1, 31):
    frame = base_image.copy()
    frame_badges = [b.copy() for b in b_list]

    current_x = badge_position_x
    for f_b in frame_badges:
      frame.paste(f_b, (current_x, badge_position_y), f_b)
      current_x = current_x + 130

    frames.append(frame)

  # Create the badge transporter effect animation
  for n in range(1, 71):
    frame = base_image.copy()

    frame_badges = [b.copy() for b in b_list]

    current_x = badge_position_x
    for f_b in frame_badges:
      # Determine opacity of badge
      # As the animation continues the opacity decreases
      # based on the percentage of the animation length to 255 (70 total frames)
      opacity_value = round((100 - (n / 70 * 100)) * 2.55)
      badge_with_opacity = f_b.copy()
      badge_with_opacity.putalpha(opacity_value)
      f_b.paste(badge_with_opacity, f_b)

      # Layer effect over badge image
      badge_with_effect = Image.new("RGBA", (125, 125), (255, 255, 255, 0))
      badge_with_effect.paste(f_b, (0, 0), f_b)
      effect_frame = Image.open(f"./images/templates/scrap/effect/{'{:02d}'.format(n)}.png").convert('RGBA').resize((125, 125))
      badge_with_effect.paste(effect_frame, (0, 0), effect_frame)

      # Stick badge onto replicator background
      frame.paste(badge_with_effect, (current_x, badge_position_y), badge_with_effect)

      current_x = current_x + 130

    frames.append(frame)

  # Add 10 frames of the replicator by itself
  for n in range(1, 11):
    frame = base_image.copy()
    frames.append(frame)

  gif_save_filepath = f"./images/scrap/{user_id}-confirm.gif"
  frames[0].save(
    gif_save_filepath,
    save_all=True, append_images=frames[1:], optimize=False, duration=40, loop=0
  )

  while True:
    time.sleep(0.05)
    if os.path.isfile(gif_save_filepath):
      break

  discord_image = discord.File(gif_save_filepath, filename=f"scrap_{user_id}-confirm.gif")
  return discord_image

@to_thread
def generate_badge_scrapper_result_gif(user_id, badge_to_add):
  badge_created_filename = badge_to_add['badge_filename']
  replicator_image = Image.open(f"./images/templates/scrap/replicator.png")

  base_image = Image.new("RGBA", (replicator_image.width, replicator_image.height), (0, 0, 0))
  base_image.paste(replicator_image, (0, 0))

  b = Image.open(f"./images/badges/{badge_created_filename}").convert("RGBA")
  b = b.resize((190, 190))

  frames = []
  badge_position_x = 180
  badge_position_y = 75

  # Add 10 frames of just the replicator by itself
  for n in range(1, 11):
    frame = base_image.copy()
    frames.append(frame)

  # Create the badge transporter effect animation
  for n in range(1, 71):
    frame = base_image.copy()
    frame_badge = b.copy()

    # Determine opacity of badge
    # As the animation continues the opacity increases
    # based on the percentage of the animation length to 255 (70 total frames)
    opacity_value = round((n / 70 * 100) * 2.55)
    badge_with_opacity = b.copy()
    badge_with_opacity.putalpha(opacity_value)
    frame_badge.paste(badge_with_opacity, frame_badge)

    # Layer effect over badge image
    badge_with_effect = Image.new("RGBA", (190, 190), (255, 255, 255, 0))
    badge_with_effect.paste(frame_badge, (0, 0), frame_badge)
    effect_frame = Image.open(f"./images/templates/scrap/effect/{'{:02d}'.format(n)}.png").convert('RGBA')
    badge_with_effect.paste(effect_frame, (0, 0), effect_frame)

    # Stick badge onto replicator background
    frame.paste(badge_with_effect, (badge_position_x, badge_position_y), badge_with_effect)

    frames.append(frame)

  # Add 30 frames of the replicator with the final badge by itself
  for n in range(1, 31):
    frame = base_image.copy()
    frame.paste(b, (badge_position_x, badge_position_y), b)
    frames.append(frame)

  gif_save_filepath = f"./images/scrap/{user_id}.gif"
  frames[0].save(
    gif_save_filepath,
    save_all=True, append_images=frames[1:], optimize=False, duration=40, loop=0
  )

  while True:
    time.sleep(0.05)
    if os.path.isfile(gif_save_filepath):
      break

  discord_image = discord.File(gif_save_filepath, filename=f"scrap_{user_id}.gif")
  return discord_image


# ________                      .__
# \_____  \  __ __   ___________|__| ____   ______
#  /  / \  \|  |  \_/ __ \_  __ \  |/ __ \ /  ___/
# /   \_/.  \  |  /\  ___/|  | \/  \  ___/ \___ \
# \_____\ \_/____/  \___  >__|  |__|\___  >____  >
#        \__>           \/              \/     \/
def db_get_all_badge_info():
  """
  Returns all rows from badge_info table
  :return: list of row dicts
  """
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT * FROM badge_info ORDER BY badge_name ASC;"
  query.execute(sql)
  rows = query.fetchall()
  query.close()
  db.close()

  return rows

def db_get_badge_info_by_name(name):
  """
  Given the name of a badge, retrieves its information from badge_info
  :param name: the name of the badge.
  :return: row dict
  """
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT * FROM badge_info WHERE badge_name = %s;"
  vals = (name,)
  query.execute(sql, vals)
  row = query.fetchone()
  query.close()
  db.close()

  return row

def db_get_badge_count_by_filename(filename):
  """
  Given the name of a badge, retrieves its information from badge_info
  :param name: the name of the badge.
  :return: row dict
  """
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT count(*) FROM badges WHERE badge_filename = %s;"
  vals = (filename,)
  query.execute(sql, vals)
  row = query.fetchone()
  query.close()
  db.close()

  return row["count(*)"]

def db_get_badge_info_by_filename(filename):
  """
  Given the filename of a badge, retrieves its information from badge_info
  :param filename: the name of the badge.
  :return: row dict
  """
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT * FROM badge_info WHERE badge_filename = %s;"
  vals = (filename,)
  query.execute(sql, vals)
  row = query.fetchone()
  query.close()
  db.close()

  return row

def db_get_user_badges(user_discord_id:int):
  '''
    get_user_badges(user_discord_id)
    user_discord_id[required]: int
    returns a list of badges the user has
  '''
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT b_i.badge_name, b_i.badge_filename, b.locked FROM badges b
      JOIN badge_info AS b_i
        ON b.badge_filename = b_i.badge_filename
        WHERE b.user_discord_id = %s
        ORDER BY b_i.badge_filename ASC
  '''
  vals = (user_discord_id,)
  query.execute(sql, vals)
  badges = query.fetchall()
  query.close()
  db.close()
  return badges

def db_get_user_unlocked_badges(user_discord_id:int):
  '''
    get_unlocked_user_badges(user_discord_id)
    user_discord_id[required]: int
    returns a list of unlocked badges the user has
  '''
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT b_i.badge_name, b_i.badge_filename, b.locked FROM badges b
      JOIN badge_info AS b_i
        ON b.badge_filename = b_i.badge_filename
        WHERE b.user_discord_id = %s AND b.locked = 0
        ORDER BY b_i.badge_filename ASC
  '''
  vals = (user_discord_id,)
  query.execute(sql, vals)
  badges = query.fetchall()
  query.close()
  db.close()
  return badges

def db_get_user_locked_badges(user_discord_id:int):
  '''
    get_unlocked_user_badges(user_discord_id)
    user_discord_id[required]: int
    returns a list of unlocked badges the user has
  '''
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT b_i.badge_name, b_i.badge_filename, b.locked FROM badges b
      JOIN badge_info AS b_i
        ON b.badge_filename = b_i.badge_filename
        WHERE b.user_discord_id = %s AND b.locked = 1
        ORDER BY b_i.badge_filename ASC
  '''
  vals = (user_discord_id,)
  query.execute(sql, vals)
  badges = query.fetchall()
  query.close()
  db.close()
  return badges

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

def db_set_user_badge_page_color_preference(user_id, type, color):
  db = getDB()
  query = db.cursor()

  if type == "showcase":
    sql = "UPDATE user_preferences SET badge_showcase_color = %s WHERE user_discord_id = %s"
  elif type == "sets":
    sql = "UPDATE user_preferences SET badge_sets_color = %s WHERE user_discord_id = %s"

  vals = (color, user_id)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

def db_get_user_badge_page_color_preference(user_id, type):
  db = getDB()
  query = db.cursor(dictionary=True)

  sql = "SELECT * FROM user_preferences WHERE user_discord_id = %s"
  vals = (user_id,)
  query.execute(sql, vals)
  result = query.fetchone()
  if result is None:
    sql = "INSERT INTO user_preferences (user_discord_id) VALUES (%s)"
    query.execute(sql, vals)

  if type == "showcase":
    sql = "SELECT badge_showcase_color AS color_preference FROM user_preferences WHERE user_discord_id = %s"
  elif type == "sets":
    sql = "SELECT badge_sets_color AS color_preference FROM user_preferences WHERE user_discord_id = %s"

  query.execute(sql, vals)
  result = query.fetchone()
  db.commit()
  query.close()
  db.close()
  color_preference = result['color_preference']

  return color_preference



# Affiliations
def db_get_all_affiliations():
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT distinct(affiliation_name) FROM badge_affiliation;"
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
    SELECT b_i.badge_name, b_i.badge_filename FROM badge_info b_i
      JOIN badge_affiliation AS b_a
        ON b_i.badge_filename = b_a.badge_filename
      WHERE b_a.affiliation_name = %s
      ORDER BY b_i.badge_name ASC;
  '''
  vals = (affiliation,)
  query.execute(sql, vals)
  rows = query.fetchall()
  query.close()
  db.close()

  return rows

def db_get_badge_affiliations_by_badge_name(name):
  """
  Given the name of a badge, retrieves the affiliation(s) associated with it
  :param name: the name of the badge.
  :return: list of row dicts
  """
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT affiliation_name FROM badge_affiliation b_a
    JOIN badge_info as b_i
      ON b_i.badge_filename = b_a.badge_filename
    WHERE badge_name = %s;
  '''
  vals = (name,)
  query.execute(sql, vals)
  rows = query.fetchall()
  query.close()
  db.close()

  return rows

def db_get_badges_user_has_from_affiliation(user_id, affiliation):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT b_i.badge_name, b_i.badge_filename FROM badges b
      JOIN badge_info AS b_i
        ON b.badge_filename = b_i.badge_filename
      JOIN badge_affiliation AS b_a
        ON b_i.badge_filename = b_a.badge_filename
      WHERE b.user_discord_id = %s
        AND b_a.affiliation_name = %s
      ORDER BY b_i.badge_name ASC;
  '''
  vals = (user_id, affiliation)
  query.execute(sql, vals)
  rows = query.fetchall()
  query.close()
  db.close()

  return rows

def db_get_random_badges_from_user_by_affiliations(user_id: int):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT b_i.badge_filename, b_a.affiliation_name
    FROM badges b
    INNER JOIN badge_info AS b_i
        ON b.badge_filename = b_i.badge_filename
    INNER JOIN badge_affiliation AS b_a
        ON b_i.badge_filename = b_a.badge_filename
    WHERE b.user_discord_id = %s
    ORDER BY RAND()
  '''
  query.execute(sql, (user_id,))
  rows = query.fetchall()
  query.close()
  db.close()

  return {r['affiliation_name']: r['badge_filename'] for r in rows}

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
    SELECT badge_name, badge_filename FROM badge_info
      WHERE franchise = %s
      ORDER BY badge_name ASC;
  '''
  vals = (franchise,)
  query.execute(sql, vals)
  rows = query.fetchall()
  query.close()
  db.close()

  return rows

def db_get_badges_user_has_from_franchise(user_id, franchise):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT b_i.badge_name, b_i.badge_filename FROM badges b
      JOIN badge_info AS b_i
        ON b.badge_filename = b_i.badge_filename
      WHERE b.user_discord_id = %s
        AND b_i.franchise = %s
      ORDER BY b_i.badge_name ASC;
  '''
  vals = (user_id, franchise)
  query.execute(sql, vals)
  rows = query.fetchall()
  query.close()
  db.close()

  return rows

def db_get_random_badges_from_user_by_franchises(user_id: int):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT b_i.badge_filename, b_i.franchise
    FROM badges b
    INNER JOIN badge_info AS b_i
        ON b.badge_filename = b_i.badge_filename
    WHERE b.user_discord_id = %s
    ORDER BY RAND()
  '''
  query.execute(sql, (user_id,))
  rows = query.fetchall()
  query.close()
  db.close()

  return {r['franchise']: r['badge_filename'] for r in rows}


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

def _time_period_sort(time_period):
  """
  We may be dealing with time periods before 1000,
  so tack on a 0 prefix for these for proper sorting
  """
  if len(time_period) == 4:
    return f"0{time_period}"
  else:
    return time_period

def db_get_all_time_period_badges(time_period):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT badge_name, badge_filename FROM badge_info b_i
      WHERE time_period = %s
      ORDER BY badge_name ASC
  '''
  vals = (time_period,)
  query.execute(sql, vals)
  rows = query.fetchall()
  query.close()
  db.close()

  return rows

def db_get_badges_user_has_from_time_period(user_id, time_period):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT b_i.badge_name, b_i.badge_filename FROM badges b
      JOIN badge_info AS b_i
        ON b.badge_filename = b_i.badge_filename
      WHERE b.user_discord_id = %s
        AND b_i.time_period = %s
      ORDER BY b_i.badge_name ASC
  '''
  vals = (user_id, time_period)
  query.execute(sql, vals)
  rows = query.fetchall()
  query.close()
  db.close()

  return rows


def db_get_random_badges_from_user_by_time_periods(user_id: int):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT b_i.badge_filename, b_i.time_period
    FROM badges b
    INNER JOIN badge_info AS b_i
        ON b.badge_filename = b_i.badge_filename
    WHERE b.user_discord_id = %s
    ORDER BY RAND()
  '''
  query.execute(sql, (user_id,))
  rows = query.fetchall()
  query.close()
  db.close()

  return {r['time_period']: r['badge_filename'] for r in rows}


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
    SELECT b_i.badge_name, b_i.badge_filename FROM badge_info b_i
      JOIN badge_type AS b_t
        ON b_i.badge_filename = b_t.badge_filename
      WHERE b_t.type_name = %s
      ORDER BY b_i.badge_name ASC
  '''
  vals = (type,)
  query.execute(sql, vals)
  rows = query.fetchall()
  query.close()
  db.close()

  return rows

def db_get_badge_types_by_badge_name(name):
  """
  Given the name of a badge, retrieves the types(s) associated with it
  :param name: the name of the badge.
  :return: list of row dicts
  """
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT type_name FROM badge_type b_t
    JOIN badge_info as b_i
      ON b_i.badge_filename = b_t.badge_filename
    WHERE badge_name = %s;
  '''
  vals = (name,)
  query.execute(sql, vals)
  rows = query.fetchall()
  query.close()
  db.close()

  return rows


def db_get_badges_user_has_from_type(user_id, type):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT b_i.badge_name, b_i.badge_filename FROM badges b
      JOIN badge_info AS b_i
        ON b.badge_filename = b_i.badge_filename
      JOIN badge_type AS b_t
        ON b_i.badge_filename = b_t.badge_filename
      WHERE b.user_discord_id = %s
        AND b_t.type_name = %s
      ORDER BY b_i.badge_name ASC
  '''
  vals = (user_id, type)
  query.execute(sql, vals)
  rows = query.fetchall()
  query.close()
  db.close()

  return rows

def db_get_random_badges_from_user_by_types(user_id: int):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    SELECT b_i.badge_filename, b_t.type_name
    FROM badges b
    INNER JOIN badge_info AS b_i
        ON b.badge_filename = b_i.badge_filename
    INNER JOIN badge_type AS b_t
        ON b_i.badge_filename = b_t.badge_filename
    WHERE b.user_discord_id = %s
    ORDER BY RAND()
  '''
  query.execute(sql, (user_id,))
  rows = query.fetchall()
  query.close()
  db.close()

  return {r['type_name']: r['badge_filename'] for r in rows}

def db_purge_users_wishlist(user_discord_id: int):
  """
  Deletes all rows from `badge_wishlists` where the user already has the
  badge present in `badges`
  """
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = '''
    DELETE b_w FROM badge_wishlists AS b_w
      JOIN badges AS b
        ON b_w.badge_filename = b.badge_filename
        AND b_w.user_discord_id = b.user_discord_id
      WHERE b.user_discord_id = %s
  '''
  vals = (user_discord_id,)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()
