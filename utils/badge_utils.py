from common import *
import textwrap
import time
import math

# big expensive function that generates a nice grid of images for the trade display

# TODO: This code is stolen wholesale from `generate_badge_showcase_for_user`, we should
#       adapt it so we can re-use the same codepath

# returns discord.file
def generate_badge_trade_showcase(badge_list, id, title, footer):
  text_wrapper = textwrap.TextWrapper(width=22)
  title_font = ImageFont.truetype("images/tng_credits.ttf", 68)
  credits_font = ImageFont.truetype("images/tng_credits.ttf", 42)
  badge_font = ImageFont.truetype("images/context_bold.ttf", 28)

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

  # start_x = image_padding
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