import io
import math
import textwrap
import time
import os

from PIL import Image, ImageDraw, ImageFont
from collections import namedtuple

from common import *

from utils.thread_utils import to_thread

from queries.badges import (
  db_get_user_badges,
  db_get_user_locked_badges,
  db_get_user_unlocked_badges,
  db_get_user_special_badges,
  db_get_badge_count_for_user,
  db_get_total_badge_count_by_filename
)

from queries.badge_info import (
  db_get_all_badge_info,
  db_get_badge_info_by_name,
  db_get_badge_info_by_filename,
  db_get_all_affiliations,
  db_get_all_affiliation_badges,
  db_get_badge_affiliations_by_badge_name,
  db_get_badges_user_has_from_affiliation,
  db_get_random_badges_from_user_by_affiliations,
  db_get_all_franchises,
  db_get_all_franchise_badges,
  db_get_badges_user_has_from_franchise,
  db_get_random_badges_from_user_by_franchises,
  db_get_all_time_periods,
  db_get_all_time_period_badges,
  db_get_random_badges_from_user_by_time_periods,
  db_get_all_types,
  db_get_all_type_badges,
  db_get_badge_types_by_badge_name,
  db_get_badges_user_has_from_type,
  db_get_random_badges_from_user_by_types
)

from queries.wishlist import (
  db_get_user_wishlist_badges,
  db_autolock_badges_by_filenames_if_in_wishlist,
  db_add_badge_name_to_users_wishlist,
  db_add_badge_filenames_to_users_wishlist,
  db_remove_badge_name_from_users_wishlist,
  db_remove_badge_filenames_from_users_wishlist,
  db_clear_users_wishlist,
  db_purge_users_wishlist,
  db_autolock_badges_by_filenames_if_in_wishlist,
  db_get_badge_locked_status_by_name,
  db_lock_badge_by_filename,
  db_lock_badges_by_filenames,
  db_unlock_badge_by_filename,
  db_unlock_badges_by_filenames,
  db_get_wishlist_matches,
  db_get_wishlist_badge_matches,
  db_get_wishlist_inventory_matches,
  db_get_wishlist_dismissal,
  db_get_all_users_wishlist_dismissals,
  db_delete_wishlist_dismissal,
  db_add_wishlist_dismissal,
)

from queries.trade import (
  db_get_trade_requested_badges,
  db_get_trade_offered_badges,
  db_cancel_trade,
  db_get_related_badge_trades,
)

# Constants
BADGE_PATH = "./images/badges/"
BADGE_SIZE = (190, 190)
BADGE_SPACING = 30
BADGE_MARGIN = 10
ROW_WIDTH = 1000
ROW_HEIGHT = 200
ROW_MARGIN = 10

#   _________                    .__       .__ __________             .___
#  /   _____/_____   ____   ____ |__|____  |  |\______   \_____     __| _/ ____   ____   ______
#  \_____  \\____ \_/ __ \_/ ___\|  \__  \ |  | |    |  _/\__  \   / __ | / ___\_/ __ \ /  ___/
#  /        \  |_> >  ___/\  \___|  |/ __ \|  |_|    |   \ / __ \_/ /_/ |/ /_/  >  ___/ \___ \
# /_______  /   __/ \___  >\___  >__(____  /____/______  /(____  /\____ |\___  / \___  >____  >
#         \/|__|        \/     \/        \/            \/      \/      \/_____/      \/     \/
_MAX_BADGE_COUNT = None
async def db_get_max_badge_count():
  global _MAX_BADGE_COUNT

  if _MAX_BADGE_COUNT is not None:
    return _MAX_BADGE_COUNT
  """
  Return the total number of possible badges we have in the system
  :return:
  """
  _MAX_BADGE_COUNT = len(await db_get_all_badge_info())
  return _MAX_BADGE_COUNT

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
    selections = await db_get_all_affiliations()
  elif category == 'franchise':
    selections = await db_get_all_franchises()
  elif category == 'time_period':
    selections = await db_get_all_time_periods()
  elif category == 'type':
    selections = await db_get_all_types()

  return [result for result in selections if ctx.value.lower() in result.lower()]


# Load and prep badge image
def load_and_prepare_badge(filename, size=BADGE_SIZE):
  badge_path = os.path.join(BADGE_PATH, filename)
  b_raw = Image.open(badge_path).convert("RGBA")
  b_raw.thumbnail(size)
  badge_img = Image.new("RGBA", size, (255, 255, 255, 0))
  badge_img.paste(b_raw, ((size[0]-b_raw.width)//2, (size[1]-b_raw.height)//2), b_raw)
  return badge_img


async def get_theme_preference(user_id, theme_type):
  theme = "green"
  try:
    pref = await db_get_user_badge_page_color_preference(user_id, theme_type)
    if pref:
      theme = pref
  except:
    pass

  return theme


def get_theme_colors(theme: str):
  """
  Returns (primary_color, highlight_color) based on the user's theme.
  Values are RGBA tuples.
  """
  # Green by default
  primary = (153, 185, 141)
  highlight = (84, 177, 69)

  if theme == "orange":
    primary = (189, 151, 137)
    highlight = (186, 111, 59)
  elif theme == "purple":
    primary = (100, 85, 161)
    highlight = (87, 64, 183)
  elif theme == "teal":
    primary = (141, 185, 181)
    highlight = (71, 170, 177)

  darker_primary = tuple(
    int(channel * 0.65) if index < 3 else channel
    for index, channel in enumerate(primary)
  )

  darker_highlight = tuple(
    int(channel * 0.85) if index < 3 else channel
    for index, channel in enumerate(highlight)
  )

  return ThemeColors(primary, highlight, darker_primary, darker_highlight)

ThemeColors = namedtuple("ThemeColors", ("primary", "highlight", "darker_primary", "darker_highlight"))


def get_lcars_font_by_length(name: str) -> ImageFont.FreeTypeFont:
  """
  Dynamically selects a LCARS-style font size based on the length of the user's display name.
  Falls back to default font if LCARS is unavailable.
  """
  try:
    if len(name) > 21:
      return ImageFont.truetype("fonts/lcars3.ttf", 82)
    elif len(name) > 16:
      return ImageFont.truetype("fonts/lcars3.ttf", 90)
    else:
      return ImageFont.truetype("fonts/lcars3.ttf", 110)
  except:
    return ImageFont.load_default()


# ANIMATION
def generate_animation(filenames, duration=120):
  """
  Creates a looping GIF animation from a list of image filenames or pre-rendered badge images.
  """
  frames = []
  for filename in filenames:
    img = load_and_prepare_badge(filename)
    frames.append(img)

  gif_bytes = io.BytesIO()
  frames[0].save(
    gif_bytes,
    format='GIF',
    save_all=True,
    append_images=frames[1:],
    duration=duration,
    loop=0,
    disposal=2,
    transparency=0
  )
  gif_bytes.seek(0)
  return gif_bytes


# --- Utilities ---
def load_badge_image(filename):
  path = os.path.join(BADGE_PATH, filename)
  return Image.open(path).convert("RGBA")


def create_badge_canvas(columns, rows, badge_size=BADGE_SIZE, spacing=BADGE_SPACING):
  width = columns * badge_size[0] + (columns - 1) * spacing
  height = rows * badge_size[1] + (rows - 1) * spacing
  return Image.new("RGBA", (width, height), (255, 255, 255, 0))


def paste_badge(canvas, badge_img, col, row, badge_size=BADGE_SIZE, spacing=BADGE_SPACING):
  x = col * (badge_size[0] + spacing)
  y = row * (badge_size[1] + spacing)
  canvas.paste(badge_img, (x, y), badge_img)


# --- Badge Slot Composition ---
def compose_badge_slot(filename, overlay=None, badge_size=BADGE_SIZE):
  badge = load_badge_image(filename)
  badge.thumbnail(badge_size)
  slot = Image.new("RGBA", badge_size, (255, 255, 255, 0))
  offset = ((badge_size[0] - badge.width) // 2, (badge_size[1] - badge.height) // 2)
  slot.paste(badge, offset, badge)

  if overlay:
    overlay_img = load_badge_image(overlay)
    overlay_img.thumbnail(badge_size)
    slot.paste(overlay_img, (0, 0), overlay_img)

  return slot


# --- Badge Strip --
def generate_simple_badge_strip(filenames, spacing=10, badge_size=BADGE_SIZE):
  """
  Generate a horizontal strip of badge images used in compact layouts.
  Used for simple displays like trade or grant confirmation.
  """
  images = [load_and_prepare_badge(f, badge_size) for f in filenames]
  width = len(images) * badge_size[0] + (len(images) - 1) * spacing
  height = badge_size[1]
  strip = Image.new("RGBA", (width, height), (255, 255, 255, 0))

  for i, img in enumerate(images):
    x = i * (badge_size[0] + spacing)
    strip.paste(img, (x, 0), img)

  return strip


#   _________       __    _________                       .__          __  .__
#  /   _____/ _____/  |_  \_   ___ \  ____   _____ ______ |  |   _____/  |_|__| ____   ____
#  \_____  \_/ __ \   __\ /    \  \/ /  _ \ /     \\____ \|  | _/ __ \   __\  |/  _ \ /    \
#  /        \  ___/|  |   \     \___(  <_> )  Y Y  \  |_> >  |_\  ___/|  | |  (  <_> )   |  \
# /_______  /\___  >__|    \______  /\____/|__|_|  /   __/|____/\___  >__| |__|\____/|___|  /
#         \/     \/               \/             \/|__|             \/                    \/
async def generate_paginated_set_completion_images(user:discord.User, all_rows, category):
  return await generate_badge_completion_images(
      user, all_rows, category
  )

async def generate_badge_completion_images(user, all_rows, category):
  """
  Renders paginated badge completion images using themed components and returns discord.File[]
  """
  user_id = user.id
  theme = await get_theme_preference(user_id, "sets")

  r_dims = _get_completion_row_dimensions()

  # We get these here and pass them so we don't have to make a DB call during every iteration
  max_badge_count = await db_get_max_badge_count()
  collected_count = await db_get_badge_count_for_user(user_id)

  filtered = [r for r in all_rows if r["percentage"] > 0]
  if not filtered:
    base = build_completion_canvas(user, max_badge_count, collected_count, category, page_number=1, total_pages=1, row_count=1, theme=theme)
    row_img = compose_empty_completion_row(r_dims, theme)
    base.paste(row_img, (0, r_dims.start_y), row_img)

    buf = io.BytesIO()
    base.save(buf, format="PNG")
    buf.seek(0)
    return [discord.File(buf, filename="empty_completion_page.png")]

  pages = []
  rows_per_page = 6
  total_pages = (len(filtered) + rows_per_page - 1) // rows_per_page

  for i in range(0, len(filtered), rows_per_page):
    chunk = filtered[i:i+rows_per_page]
    base = build_completion_canvas(user, max_badge_count, collected_count, category, page_number=(i//rows_per_page)+1, total_pages=total_pages, row_count=len(chunk) - 1, theme=theme)

    current_y = r_dims.start_y
    for idx, row_data in enumerate(chunk):
      row_img = compose_completion_row(row_data, r_dims, theme)
      base.paste(row_img, (120, current_y), row_img)
      current_y += r_dims.row_height + r_dims.row_margin

    buf = io.BytesIO()
    base.save(buf, format="PNG")
    buf.seek(0)
    pages.append(discord.File(buf, filename=f"completion_page_{i//rows_per_page+1}.png"))

  return pages

def compose_completion_row(row_data, r_dims, theme):
  """
  Draws a single row for a badge set including:
  - Badge image (optional)
  - Set title
  - Percent collected text
  - Progress bar with gradient overlay

  Expects `row_data` with keys:
    'name', 'percentage', 'owned', 'total', 'featured_badge'
  """
  colors = get_theme_colors(theme)

  row_canvas = Image.new("RGBA", (r_dims.row_width, r_dims.row_height), (0, 0, 0, 0))
  draw = ImageDraw.Draw(row_canvas)

  draw.rounded_rectangle(
    (0, 0, r_dims.row_width, r_dims.row_height),
    fill="#181818",
    outline="#181818",
    width=4,
    radius=32
  )

  try:
    title_font = ImageFont.truetype("fonts/lcars3.ttf", 160)
    percent_font = ImageFont.truetype("fonts/lcars3.ttf", 120)
  except:
    title_font = percent_font = ImageFont.load_default()

  title = row_data.get("name") or "Unassociated"
  draw.text((r_dims.offset, 40), title, font=title_font, fill=colors.highlight)

  draw.text(
    (r_dims.row_width - 20, 170),
    f"{row_data['percentage']}% ({row_data['owned']} of {row_data['total']})",
    fill=colors.highlight,
    font=percent_font,
    anchor="rb"
  )

  draw_completion_row_progress_bar(row_canvas, row_data, r_dims, theme)

  if row_data.get("featured_badge"):
    try:
      badge_path = os.path.join(BADGE_PATH, row_data["featured_badge"])
      badge_img = Image.open(badge_path).convert("RGBA")
      badge_img.thumbnail((200, 200))
      row_canvas.paste(badge_img, (25, 25), badge_img)
    except:
      pass

  return row_canvas

def draw_completion_row_progress_bar(row_canvas, row_data, r_dims, theme):
  """
  Renders a progress bar onto the given canvas using the row data and theme colors.

  Parameters:
    row_canvas (Image): The PIL image to draw onto.
    row_data (dict): Badge set row data. Requires 'percentage' key.
    r_dims (dict): Layout dimensions for the row, as returned by _get_completion_row_dimensions().
                   Must include: bar_x, bar_y, bar_w, bar_h.
    theme (str): User-selected theme name (e.g., "green", "orange").
  """

  colors = get_theme_colors(theme)
  # Boosted fill color for visual strength
  gradient_end_color = (24, 24, 24)

  draw = ImageDraw.Draw(row_canvas)
  percentage_width = int((row_data["percentage"] / 100) * r_dims.bar_w)

  if row_data["percentage"] < 100:
    bar_fill = Image.new("RGBA", (r_dims.bar_w, r_dims.bar_h), (0, 0, 0, 0))
    gradient_start = int(percentage_width * 0.8)

    for x in range(gradient_start):
      for y in range(r_dims.bar_h):
        bar_fill.putpixel((x, y), (*colors.darker_highlight, 255))

    for x in range(gradient_start, percentage_width):
      fade_ratio = (x - gradient_start) / max(1, (percentage_width - gradient_start))
      r = int((colors.darker_highlight[0] * (1 - fade_ratio)) + (gradient_end_color[0] * fade_ratio))
      g = int((colors.darker_highlight[1] * (1 - fade_ratio)) + (gradient_end_color[1] * fade_ratio))
      b = int((colors.darker_highlight[2] * (1 - fade_ratio)) + (gradient_end_color[2] * fade_ratio))
      for y in range(r_dims.bar_h):
        bar_fill.putpixel((x, y), (r, g, b, 255))

    for x in range(percentage_width, r_dims.bar_w):
      for y in range(r_dims.bar_h):
        bar_fill.putpixel((x, y), (*gradient_end_color, 255))

    rounded_mask = Image.new("L", (r_dims.bar_w, r_dims.bar_h), 0)
    draw_mask = ImageDraw.Draw(rounded_mask)
    draw_mask.rounded_rectangle((0, 0, r_dims.bar_w, r_dims.bar_h), radius=r_dims.bar_h // 2, fill=255)
    row_canvas.paste(bar_fill, (r_dims.bar_x, r_dims.bar_y), rounded_mask)
  else:
    draw.rounded_rectangle(  (
        r_dims.bar_x,
        r_dims.bar_y,
        r_dims.bar_x + percentage_width,
        r_dims.bar_y + r_dims.bar_h
      ),
      fill=colors.darker_highlight,
      radius=r_dims.bar_h // 2
    )


def _get_completion_row_dimensions():
  """
  Returns layout metrics for drawing a single badge row and its components.

  Returns:
    dict: A dictionary containing:
      - row_width (int): Total width of the row image.
      - row_height (int): Total height of the row image.
      - offset (int): Left margin where text and content begin.
      - bar_margin (int): Right padding after progress bar.
      - bar_x (int): X-coordinate where progress bar starts.
      - bar_w (int): Width of the progress bar.
      - bar_h (int): Height of the progress bar.
      - bar_y (int): Y-coordinate of the progress bar.
      - start_y (int): Y-position of the first row on the page image.
  """
  row_width = 1700
  row_height = 280
  row_margin = 10
  offset = 250
  bar_margin = 40
  bar_x = offset
  bar_w = row_width - offset - bar_margin
  bar_h = 32
  bar_y = 280 - bar_h - 30
  start_y = 245

  return RowDimensions(
    row_width, row_height, row_margin, offset,
    bar_margin, bar_x, bar_w, bar_h, bar_y,
    start_y
  )

RowDimensions = namedtuple("RowDimensions", [
  "row_width", "row_height", "row_margin", "offset",
  "bar_margin", "bar_x", "bar_w", "bar_h", "bar_y",
  "start_y"
])

def compose_empty_completion_row(r_dims, theme, message: str = "No badges within inventory that match this set type."):
  """
  Returns a fallback row image with a centered message.
  """
  primary_color, highlight_color, darker_primary_color = get_theme_colors(theme)
  darker_primary_color = tuple(
    int(channel * 0.65) if index < 3 else channel
    for index, channel in enumerate(primary_color)
  )

  empty_row_canvas = Image.new("RGBA", (ROW_WIDTH, ROW_HEIGHT), (0, 0, 0, 0))
  draw = ImageDraw.Draw(empty_row_canvas)

  r_dims = _get_completion_row_dimensions()

  draw.rounded_rectangle(
    (
      r_dims.bar_x,
      r_dims.bar_y,
      r_dims.bar_x + r_dims.bar_w - 1,
      r_dims.bar_y + r_dims.bar_h - 1
    ),
    fill=darker_primary_color,
    radius=r_dims.bar_h // 2
  )

  try:
    font = ImageFont.truetype("fonts/lcars3.ttf", 48)
  except:
    font = ImageFont.load_default()

  text_w = draw.textlength(message, font=font)
  draw.text(((ROW_WIDTH - text_w) // 2, 80), message, font=font, fill=highlight_color)

  return empty_row_canvas

def build_completion_canvas(user: discord.User, max_badge_count: int, collected_count: int, category: str, page_number: int, total_pages: int, row_count: int, theme: str) -> Image.Image:
  """
  Builds the full badge completion page using header, row, and footer images based on the theme.
  Dynamically draws fonts on top and returns the full canvas.
  """

  # Load assets based on theme
  colors = get_theme_colors(theme)

  asset_prefix = f"images/templates/badges/badge_page_"
  header_img = Image.open(f"{asset_prefix}header_{theme}.png").convert("RGBA")
  footer_img = Image.open(f"{asset_prefix}footer_{theme}.png").convert("RGBA")
  row_img = Image.open(f"{asset_prefix}row_{theme}.png").convert("RGBA")

  header_h = header_img.height
  footer_h = footer_img.height
  row_h = row_img.height
  base_w = header_img.width
  total_h = header_h + footer_h + row_h * row_count

  canvas = Image.new("RGBA", (base_w, total_h), (0, 0, 0, 0))
  canvas.paste(header_img, (0, 0), header_img)

  for i in range(row_count):
    y = header_h + i * row_h
    canvas.paste(row_img, (0, y), row_img)

  canvas.paste(footer_img, (0, header_h + row_count * row_h), footer_img)

  # Font overlays
  display_name = remove_emoji(user.display_name)
  category_title = category.replace('_', ' ').title()

  try:
    title_font = get_lcars_font_by_length(display_name)
    collected_font = ImageFont.truetype("fonts/lcars3.ttf", 100)
    total_font = ImageFont.truetype("fonts/lcars3.ttf", 54)
    page_font = ImageFont.truetype("fonts/lcars3.ttf", 80)
  except:
    title_font = collected_font = total_font = page_font = ImageFont.load_default()

  draw = ImageDraw.Draw(canvas)
  draw.text((100, 65), f"{display_name}'s Badge Completion - {category_title}", font=title_font, fill=colors.highlight)
  draw.text((590, total_h - 125), f"{collected_count} ON THE USS HOOD", font=collected_font, fill=colors.highlight)
  draw.text((32, total_h - 90), f"{max_badge_count}", font=total_font, fill=colors.highlight)
  draw.text((base_w - 370, total_h - 115), f"PAGE {page_number:02d} OF {total_pages:02d}", font=page_font, fill=colors.highlight)

  return canvas


# _________        .__  .__                 __  .__
# \_   ___ \  ____ |  | |  |   ____   _____/  |_|__| ____   ____   ______
# /    \  \/ /  _ \|  | |  | _/ __ \_/ ___\   __\  |/  _ \ /    \ /  ___/
# \     \___(  <_> )  |_|  |_\  ___/\  \___|  | |  (  <_> )   |  \\___ \
#  \______  /\____/|____/____/\___  >\___  >__| |__|\____/|___|  /____  >
#         \/                      \/     \/                    \/     \/
# async def generate_paginated_badge_images(user:discord.User, type, all_badges, total_badges, title, collected, filename_prefix):
#   max_per_image = 30
#   all_pages = [all_badges[i:i + max_per_image] for i in range(0, len(all_badges), max_per_image)]
#   total_pages = len(all_pages)
#   badge_images = [
#     await generate_badge_images(
#       type,
#       user,
#       page,
#       page_number + 1, # Account for zero index
#       total_pages,
#       total_badges,
#       title,
#       collected,
#       filename_prefix
#     )
#     for page_number, page in enumerate(all_pages)
#   ]
#   return badge_images

async def generate_paginated_badge_images(user:discord.User, all_rows, collection_type):
  return await generate_badge_collection_images(
      user, all_rows, collection_type
  )

CollectionGridDimensions = namedtuple("CollectionGridDimensions", ["badge_size", "padding", "title_height", "footer_height"])
CollectionGridLayout = namedtuple("CollectionGridLayout", ["badges_per_page", "badges_per_row"])

def _get_collection_grid_dimensions() -> CollectionGridDimensions:
  return CollectionGridDimensions(
    badge_size=(128, 128),
    padding=20,
    title_height=80,
    footer_height=50
  )

def _get_collection_grid_layout() -> CollectionGridLayout:
  return CollectionGridLayout(
    badges_per_page=30,
    badges_per_row=5
  )

async def generate_paginated_badge_collection_images(user: discord.User, all_rows: list, collection_type: str):
  return await generate_badge_collection_images(user, all_rows, collection_type)

async def generate_badge_collection_images(
  user: discord.User,
  badge_data: list,
  collection_type: str
) -> list[discord.File]:
  """
  Generates one or more paginated grid images of a user's badge collection, themed according to
  their preferences and appropriate for /badges showcase or /badges sets displays.

  Parameters:
    user (discord.User): The Discord user whose collection is being visualized.
    badge_data (list): A list of badge dicts. Each dict must contain:
      - badge_name (str)
      - badge_filename (str)
      - locked (bool)
      - special (bool)
    collection_type (str): Context for the collection being rendered, e.g., "showcase" or "sets".

  Returns:
    list[discord.File]: A list of image files representing each page of the badge collection.
  """
  layout = _get_collection_grid_layout()
  user_id = user.id

  max_badge_count = await db_get_max_badge_count()
  collected_count = await db_get_badge_count_for_user(user_id)
  theme = await get_theme_preference(user_id, collection_type)

  title = f"{user.display_name}'s Badge {collection_type.title()}"
  collected_text = f"{collected_count} ON THE USS HOOD"

  pages = []
  for page_index in range(0, len(badge_data), layout.badges_per_page):
    page_badges = badge_data[page_index:page_index + layout.badges_per_page]
    image = draw_badge_grid_page(
      page_badges,
      title,
      collected_text,
      page_index // layout.badges_per_page + 1
    )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    pages.append(discord.File(fp=buffer, filename=f"badge_collection_page_{page_index // layout.badges_per_page + 1}.png"))

  return pages

def draw_badge_grid_page(
  badges: list,
  title: str = None,
  collected_text: str = None,
  page_number: int = 1
) -> Image.Image:
  """Draws a single badge grid page from the given badge info list."""
  import math

  dims = _get_collection_grid_dimensions()
  layout = _get_collection_grid_layout()

  rows = math.ceil(len(badges) / layout.badges_per_row)
  width = layout.badges_per_row * (dims.badge_size[0] + dims.padding) + dims.padding
  height = dims.title_height + rows * (dims.badge_size[1] + dims.padding) + dims.footer_height + dims.padding

  canvas = Image.new("RGBA", (width, height), (18, 18, 18, 255))
  draw = ImageDraw.Draw(canvas)

  # Draw title if present
  if title:
    font = ImageFont.truetype("./fonts/Roboto-Bold.ttf", 32)
    draw.text((dims.padding, dims.padding), title, font=font, fill=(255, 255, 255))

  # Draw badges
  for idx, badge in enumerate(badges):
    row = idx // layout.badges_per_row
    col = idx % layout.badges_per_row
    x = dims.padding + col * (dims.badge_size[0] + dims.padding)
    y = dims.title_height + row * (dims.badge_size[1] + dims.padding)
    composed_badge = compose_badge_slot(badge, dims)
    canvas.paste(composed_badge, (x, y), composed_badge)

  # Draw footer text
  if collected_text:
    font = ImageFont.truetype("./fonts/Roboto-Regular.ttf", 24)
    draw.text((dims.padding, height - dims.footer_height), collected_text, font=font, fill=(200, 200, 200))

  return canvas

def compose_badge_slot(badge: dict, dims: CollectionGridDimensions) -> Image.Image:
  """Composes and returns a badge image with overlays applied for locked/special badges."""
  badge_path = f"./images/badges/{badge['badge_filename']}"
  badge_img = Image.open(badge_path).convert("RGBA").resize(dims.badge_size)

  if badge.get("locked"):
    overlay = Image.new("RGBA", dims.badge_size, (0, 0, 0, 128))
    badge_img = Image.alpha_composite(badge_img, overlay)

  if badge.get("special"):
    draw = ImageDraw.Draw(badge_img)
    draw.rectangle([(0, 0), (dims.badge_size[0] - 1, dims.badge_size[1] - 1)], outline=(255, 215, 0), width=4)

  return badge_img

# async def generate_badge_images(type, user, page, page_number, total_pages, total_user_badges, title, collected, filename_prefix):
#   user_display_name = user.display_name
#   color_preference = await db_get_user_badge_page_color_preference(user.id, type)

#   if color_preference == "green":
#     title_color = "#99B98D"
#     highlight_color = "#54B145"
#   elif color_preference == "orange":
#     title_color = "#BD9789"
#     highlight_color = "#BA6F3B"
#   elif color_preference == "purple":
#     title_color = "#6455A1"
#     highlight_color = "#9593B2"
#   elif color_preference == "teal":
#     title_color = "#8DB9B5"
#     highlight_color = "#47AAB1"

#   text_wrapper = textwrap.TextWrapper(width=22)
#   title_font = ImageFont.truetype("fonts/lcars3.ttf", 110)
#   if len(user_display_name) > 16:
#     title_font = ImageFont.truetype("fonts/lcars3.ttf", 90)
#   if len(user_display_name) > 21:
#     title_font = ImageFont.truetype("fonts/lcars3.ttf", 82)
#   collected_font = ImageFont.truetype("fonts/lcars3.ttf", 100)
#   total_font = ImageFont.truetype("fonts/lcars3.ttf", 54)
#   page_number_font = ImageFont.truetype("fonts/lcars3.ttf", 80)
#   badge_font = ImageFont.truetype("fonts/context_bold.ttf", 28)

#   badge_size = 200
#   badge_padding = 40
#   badge_margin = 10
#   badge_slot_size = badge_size + (badge_padding * 2) # size of badge slot size (must be square!)
#   badges_per_row = 6

#   base_width = 1890
#   base_header_height = 530
#   base_row_height = 290
#   base_footer_height = 200

#   # If we're generating just one page we want the rows to simply expand to only what's necessary
#   # Otherwise if there's multiple pages we want to have all of them be consistent
#   if page_number == 1 and total_pages == 1:
#     number_of_rows = math.ceil((len(page) / badges_per_row)) - 1
#   else:
#     number_of_rows = 4

#   base_height = base_header_height + (base_row_height * number_of_rows) + base_footer_height

#   # create base image to paste all badges on to
#   badge_base_image = Image.new("RGBA", (base_width, base_height), (0, 0, 0))
#   base_header_image = Image.open(f"./images/templates/badges/badge_page_header_{color_preference}.png")
#   base_row_image = Image.open(f"./images/templates/badges/badge_page_row_{color_preference}.png")
#   base_footer_image = Image.open(f"./images/templates/badges/badge_page_footer_{color_preference}.png")

#   # Start image with header
#   badge_base_image.paste(base_header_image, (0, 0))

#   # Stamp rows (if needed, header includes first row)
#   base_current_y = base_header_height
#   for i in range(number_of_rows):
#     badge_base_image.paste(base_row_image, (0, base_current_y))
#     base_current_y += base_row_height

#   # Stamp footer
#   badge_base_image.paste(base_footer_image, (0, base_current_y))

#   draw = ImageDraw.Draw(badge_base_image)

#   draw.text( (100, 65), title, fill=title_color, font=title_font, align="left")
#   draw.text( (590, base_height - 125), collected, fill=highlight_color, font=collected_font, align="left")
#   draw.text( (32, base_height - 90), f"{total_user_badges}", fill=highlight_color, font=total_font, align="left")
#   draw.text( (base_width - 370, base_height - 115), f"PAGE {'{:02d}'.format(page_number)} OF {'{:02d}'.format(total_pages)}", fill=highlight_color, font=page_number_font, align="right")

#   start_x = 100
#   current_x = start_x
#   current_y = 245
#   counter = 0

#   for badge_record in page:
#     badge_border_color = highlight_color
#     badge_text_color = "white"
#     if type == 'sets' and not badge_record['in_user_collection']:
#       badge_border_color = "#575757"
#       badge_text_color = "#888888"

#     # slot
#     s = Image.new("RGBA", (badge_slot_size, badge_slot_size), (0, 0, 0, 0))
#     badge_draw = ImageDraw.Draw(s)
#     badge_draw.rounded_rectangle( (0, 0, badge_slot_size, badge_slot_size), fill="#000000", outline=badge_border_color, width=4, radius=32 )

#     # badge
#     b_raw = Image.open(f"./images/badges/{badge_record['badge_filename']}").convert("RGBA")
#     if type == 'sets' and not badge_record['in_user_collection']:
#       # Create a mask layer to apply a 1/4th opacity to
#       b2 = b_raw.copy()
#       b2.putalpha(64)
#       b_raw.paste(b2, b_raw)
#     size = (190, 190)
#     b_raw.thumbnail(size, Image.ANTIALIAS)
#     b = Image.new('RGBA', size, (255, 255, 255, 0))
#     b.paste(
#       b_raw, (int((size[0] - b_raw.size[0]) // 2), int((size[1] - b_raw.size[1]) // 2))
#     )
#     b = b.resize((190, 190))

#     w, h = b.size # badge size
#     offset_x = min(0, (badge_size+badge_padding)-w) # center badge x
#     offset_y = 5
#     badge_name = text_wrapper.wrap(badge_record['badge_name'])
#     wrapped_badge_name = ""
#     for i in badge_name[:-1]:
#       wrapped_badge_name = wrapped_badge_name + i + "\n"
#     wrapped_badge_name += badge_name[-1]
#     # add badge to slot
#     s.paste(b, (badge_padding+offset_x+4, offset_y), b)
#     badge_draw.text( (int(badge_slot_size/2), 222), f"{wrapped_badge_name}", fill=badge_text_color, font=badge_font, anchor="mm", align="center")

#     if badge_record['special']:
#       special_icon = Image.open(f"./images/templates/badges/special_icon.png").convert("RGBA")
#       s.paste(special_icon, (badge_slot_size-54, 16), special_icon)
#     elif badge_record['locked']:
#       lock_icon = Image.open(f"./images/templates/badges/lock_icon.png").convert("RGBA")
#       s.paste(lock_icon, (badge_slot_size-54, 16), lock_icon)

#     # add slot to base image
#     badge_base_image.paste(s, (current_x, current_y), s)

#     current_x += badge_slot_size + badge_margin
#     counter += 1

#     if counter % badges_per_row == 0:
#       # typewriter sound effects:
#       current_x = start_x # ding!
#       current_y += badge_slot_size + badge_margin # ka-chunk
#       counter = 0 #...

#   badge_set_filepath = f"./images/profiles/{filename_prefix}{page_number}.png"
#   badge_base_image.save(badge_set_filepath)

#   while True:
#     time.sleep(0.05)
#     if os.path.isfile(badge_set_filepath):
#       break

#   discord_image = discord.File(badge_set_filepath, filename=f"{filename_prefix}{page_number}.png")
#   return discord_image


# ___________                  .___.__
# \__    ___/___________     __| _/|__| ____    ____
#   |    |  \_  __ \__  \   / __ | |  |/    \  / ___\
#   |    |   |  | \// __ \_/ /_/ | |  |   |  \/ /_/  >
#   |____|   |__|  (____  /\____ | |__|___|  /\___  /
#                       \/      \/         \//_____/
async def generate_badge_trade_showcase(badge_list, id, title, footer):
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
    size = (190, 190)
    b_raw = Image.open(f"./images/badges/{badge}").convert("RGBA")
    b_raw.thumbnail(size, Image.ANTIALIAS)
    b = Image.new('RGBA', size, (255, 255, 255, 0))
    b.paste(
      b_raw, (int((size[0] - b_raw.size[0]) // 2), int((size[1] - b_raw.size[1]) // 2))
    )

    w, h = b.size # badge size
    offset_x = min(0, (badge_size+badge_padding)-w) # center badge x
    offset_y = 5
    badge_info = await db_get_badge_info_by_filename(badge)
    badge_name = text_wrapper.wrap(badge_info['badge_name'])
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


#   _________
#  /   _____/ ________________  ______ ______   ___________
#  \_____  \_/ ___\_  __ \__  \ \____ \\____ \_/ __ \_  __ \
#  /        \  \___|  | \// __ \|  |_> >  |_> >  ___/|  | \/
# /_______  /\___  >__|  (____  /   __/|   __/ \___  >__|
#         \/     \/           \/|__|   |__|        \/
def generate_badge_scrapper_confirmation_frames(badges_to_scrap):
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

  return frames

@to_thread
def generate_badge_scrapper_confirmation_gif(user_id, badges_to_scrap):
  frames = generate_badge_scrapper_confirmation_frames(badges_to_scrap)

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
def generate_badge_scrapper_result_gif(user_id, badge_to_add, badges_to_scrap):
  badge_created_filename = badge_to_add['badge_filename']
  replicator_image = Image.open(f"./images/templates/scrap/replicator.png")

  base_image = Image.new("RGBA", (replicator_image.width, replicator_image.height), (0, 0, 0))
  base_image.paste(replicator_image, (0, 0))

  frames = generate_badge_scrapper_confirmation_frames(badges_to_scrap)

  b = Image.open(f"./images/badges/{badge_created_filename}").convert("RGBA")
  b = b.resize((190, 190))

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
    time.sleep(0.10)
    if os.path.isfile(gif_save_filepath):
      break

  discord_image = discord.File(gif_save_filepath, filename=f"scrap_{user_id}.gif")
  return discord_image

# HELPER FUNCTIONS
def get_badge_metadata(filename):
  return db_get_badge_info_by_filename(filename)

# Check if badge was on wishlist
def was_badge_on_wishlist(badge_filename, wishlist):
  return badge_filename in [b['badge_filename'] for b in wishlist]

async def db_set_user_badge_page_color_preference(user_id, type, color):
  async with AgimusDB() as query:
    if type == "showcase":
      sql = "UPDATE user_preferences SET badge_showcase_color = %s WHERE user_discord_id = %s"
    elif type == "sets":
      sql = "UPDATE user_preferences SET badge_sets_color = %s WHERE user_discord_id = %s"
    vals = (color, user_id)
    await query.execute(sql, vals)

async def db_get_user_badge_page_color_preference(user_id, type):
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT * FROM user_preferences WHERE user_discord_id = %s"
    vals = (user_id,)
    await query.execute(sql, vals)
    result = await query.fetchone()
    if result is None:
      sql = "INSERT INTO user_preferences (user_discord_id) VALUES (%s)"
      await query.execute(sql, vals)

    if type == "showcase":
      sql = "SELECT badge_showcase_color AS color_preference FROM user_preferences WHERE user_discord_id = %s"
    elif type == "sets":
      sql = "SELECT badge_sets_color AS color_preference FROM user_preferences WHERE user_discord_id = %s"

    await query.execute(sql, vals)
    result = await query.fetchone()
  color_preference = result['color_preference']
  return color_preference
