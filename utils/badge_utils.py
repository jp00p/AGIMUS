import io
import math
import textwrap
import time
import os
import regex

from collections import namedtuple
from emoji import EMOJI_DATA
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

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


# ___________.__                          .__
# \__    ___/|  |__   ____   _____   ____ |__| ____    ____
#   |    |   |  |  \_/ __ \ /     \_/ __ \|  |/    \  / ___\
#   |    |   |   Y  \  ___/|  Y Y  \  ___/|  |   |  \/ /_/  >
#   |____|   |___|  /\___  >__|_|  /\___  >__|___|  /\___  /
#                 \/     \/      \/     \/        \//_____/
async def get_theme_preference(user_id, theme_type):
  theme = "green"
  try:
    pref = await db_get_user_badge_page_color_preference(user_id, theme_type)
    if pref:
      theme = pref
  except:
    pass

  return theme


ThemeColors = namedtuple("ThemeColors", ("primary", "highlight", "darker_primary", "darker_highlight"))
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


# ___________            __
# \_   _____/___   _____/  |_  ______
#  |    __)/  _ \ /    \   __\/  ___/
#  |     \(  <_> )   |  \  |  \___ \
#  \___  / \____/|___|  /__| /____  >
#      \/             \/          \/
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


FontSet = namedtuple("FontSet", ["title", "footer", "total", "pages", "label", "general"])
def load_fonts(title_size=110, footer_size=100, total_size=54, page_size=80, label_size=32, general_size=70, fallback=True):
  try:
    return FontSet(
      title=ImageFont.truetype("fonts/lcars3.ttf", title_size),
      footer=ImageFont.truetype("fonts/lcars3.ttf", footer_size),
      total=ImageFont.truetype("fonts/lcars3.ttf", total_size),
      pages=ImageFont.truetype("fonts/lcars3.ttf", page_size),
      label=ImageFont.truetype("fonts/context_bold.ttf", label_size),
      general=ImageFont.truetype("fonts/lcars3.ttf", general_size)
    )
  except:
    if fallback:
      default = ImageFont.load_default()
      return FontSet(default, default, default, default, default, default)
    raise

def draw_canvas_labels(canvas, draw, user, mode, label, collected_count, total_count, page_number, total_pages, base_w, base_h, fonts, colors):
  title_text = f"{user.display_name}'s Badge {mode.title()}"
  if label:
    title_text += f": {label}"

  draw_title(
    canvas=canvas,
    draw=draw,
    position=(100, 65),
    text=title_text,
    max_width=base_w - 200,
    font_obj=fonts.title,
    fill=colors.highlight
  )

  draw.text(
    (590, base_h - 125),
    f"{collected_count} ON THE USS HOOD",
    font=fonts.footer,
    fill=colors.highlight
  )

  draw.text(
    (32, base_h - 90),
    f"{total_count}",
    font=fonts.total,
    fill=colors.highlight
  )

  draw.text(
    (base_w - 370, base_h - 115),
    f"PAGE {page_number} OF {total_pages}",
    font=fonts.pages,
    fill=colors.highlight
  )

#   _____ _ _   _
#  |_   _(_) |_| |___
#    | | | |  _| / -_)
#    |_| |_|\__|_\___|
# (Handles dynamic resizing and emoji)
def draw_title(
  canvas: Image.Image,
  draw: ImageDraw.ImageDraw,
  position: tuple,
  text: str,
  max_width: int,
  font_obj: ImageFont.FreeTypeFont,
  starting_size=110,
  min_size=30,
  fill=(255, 255, 255)
):
  font_path = font_obj.path if hasattr(font_obj, "path") else "fonts/lcars3.ttf"
  size = starting_size
  clusters = split_text_into_emoji_clusters(text)

  def get_fonts(size):
    return ImageFont.truetype(font_path, size), int(size * 0.75)

  def get_width(cluster, font, emoji_size):
    return emoji_size if is_emoji(cluster) else font.getlength(cluster)

  while size > min_size:
    font, emoji_size = get_fonts(size)
    total_width = sum(get_width(cluster, font, emoji_size) for cluster in clusters)
    if total_width <= max_width:
      break
    size -= 1

  font, emoji_size = get_fonts(size)

  x, y = position
  current_x = x

  for cluster in clusters:
    if is_emoji(cluster):
      emoji_file = EMOJI_IMAGE_PATH / emoji_to_filename(cluster)
      if emoji_file.exists():
        emoji_img = Image.open(emoji_file).convert("RGBA").resize((emoji_size, emoji_size))
        canvas.paste(emoji_img, (int(current_x), int(y)), emoji_img)
        current_x += emoji_size
      else:
        logger.error(f"[emoji-missing] {cluster} → {emoji_file}")
    else:
      draw.text((current_x, y), cluster, font=font, fill=fill)
      current_x += font.getlength(cluster)

EMOJI_IMAGE_PATH = Path("fonts/twemoji")

def is_emoji(seq: str) -> bool:
  return seq in EMOJI_DATA

def emoji_to_filename(emoji_seq: str) -> str:
  return "-".join(f"{ord(c):x}" for c in emoji_seq) + ".png"

def split_text_into_emoji_clusters(text: str):
  return regex.findall(r'\X', text)


#  ____ ___   __  .__.__
# |    |   \_/  |_|__|  |   ______
# |    |   /\   __\  |  |  /  ___/
# |    |  /  |  | |  |  |__\___ \
# |______/   |__| |__|____/____  >
#                              \/
def load_badge_image(filename):
  path = os.path.join(BADGE_PATH, filename)
  return Image.open(path).convert("RGBA")

def load_and_prepare_badge_thumbnail(filename, size=BADGE_SIZE):
  badge_image = load_badge_image(filename)
  badge_image.thumbnail(size)
  thumbnail = Image.new("RGBA", size, (255, 255, 255, 0))
  thumbnail.paste(badge_image, ((size[0]-badge_image.width)//2, (size[1]-badge_image.height)//2), badge_image)
  return thumbnail

def paginate(data_list, items_per_page):
  for i in range(0, len(data_list), items_per_page):
    yield data_list[i:i + items_per_page], (i // items_per_page) + 1

# __________             .___                 _________ __         .__
# \______   \_____     __| _/ ____   ____    /   _____//  |________|__|_____
#  |    |  _/\__  \   / __ | / ___\_/ __ \   \_____  \\   __\_  __ \  \____ \
#  |    |   \ / __ \_/ /_/ |/ /_/  >  ___/   /        \|  |  |  | \/  |  |_> >
#  |______  /(____  /\____ |\___  / \___  > /_______  /|__|  |__|  |__|   __/
#         \/      \/      \/_____/      \/          \/                |__|
def generate_badge_strip(filenames, spacing=10, badge_size=BADGE_SIZE):
  """
  Generate a horizontal strip of badge images used in compact layouts.
  Used for simple displays like trade or grant confirmation.
  """
  images = [load_and_prepare_badge_thumbnail(f, badge_size) for f in filenames]
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
async def generate_badge_set_completion_images(user, all_rows, category):
  """
  Renders paginated badge completion images using themed components and returns discord.File[]
  """
  user_id = user.id
  theme = await get_theme_preference(user_id, "sets")

  dims = _get_completion_row_dimensions()

  # We get these here and pass them so we don't have to make a DB call during every iteration
  max_badge_count = await db_get_max_badge_count()
  collected_count = await db_get_badge_count_for_user(user_id)

  filtered = [r for r in all_rows if r["percentage"] > 0]
  if not filtered:
    canvas = await build_completion_canvas(user, max_badge_count, collected_count, category, page_number=1, total_pages=1, row_count=1, theme=theme)
    row_img = await compose_empty_completion_row(dims, theme)
    canvas.paste(row_img, (0, dims.start_y), row_img)

    page = buffer_image_to_discord_file(canvas, "empty_completion_page.png")
    return [page]

  pages = []
  rows_per_page = 6
  total_pages = (len(filtered) + rows_per_page - 1) // rows_per_page

  for i in range(0, len(filtered), rows_per_page):
    chunk = filtered[i:i+rows_per_page]
    canvas = await build_completion_canvas(user, max_badge_count, collected_count, category, page_number=(i//rows_per_page)+1, total_pages=total_pages, row_count=len(chunk) - 1, theme=theme)

    current_y = dims.start_y
    for idx, row_data in enumerate(chunk):
      row_img = await compose_completion_row(row_data, theme)
      canvas.paste(row_img, (120, current_y), row_img)
      current_y += dims.row_height + dims.row_margin

    page = buffer_image_to_discord_file(canvas, f"completion_page_{i//rows_per_page+1}.png")
    pages.append(page)

  return pages


async def build_completion_canvas(user: discord.User, max_badge_count: int, collected_count: int, category: str, page_number: int, total_pages: int, row_count: int, theme: str) -> Image.Image:
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

  fonts = load_fonts()

  draw_canvas_labels(
    canvas=canvas,
    user=user,
    label=category_title,
    collected_count=collected_count,
    total_count=total_count,
    page_num=page_num,
    base_w=base_w,
    base_h=base_h,
    fonts=fonts,
    colors=colors,
    mode="completion"
  )

  return canvas


async def compose_completion_row(row_data, theme):
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
  dims = _get_completion_row_dimensions()

  row_canvas = Image.new("RGBA", (dims.row_width, dims.row_height), (0, 0, 0, 0))
  draw = ImageDraw.Draw(row_canvas)

  draw.rounded_rectangle(
    (0, 0, dims.row_width, dims.row_height),
    fill="#181818",
    outline="#181818",
    width=4,
    radius=32
  )

  fonts = load_fonts(title_size=160, general_size=120)

  title = row_data.get("name") or "Unassociated"
  draw.text((dims.offset, 40), title, font=fonts.title, fill=colors.highlight)

  draw.text(
    (dims.row_width - 20, 170),
    f"{row_data['percentage']}% ({row_data['owned']} of {row_data['total']})",
    fill=colors.highlight,
    font=fonts.general,
    anchor="rb"
  )

  await draw_completion_row_progress_bar(row_canvas, row_data, theme)

  if row_data.get("featured_badge"):
    try:
      badge_path = os.path.join(BADGE_PATH, row_data["featured_badge"])
      badge_img = Image.open(badge_path).convert("RGBA")
      badge_img.thumbnail((200, 200))
      row_canvas.paste(badge_img, (25, 25), badge_img)
    except:
      pass

  return row_canvas

async def draw_completion_row_progress_bar(row_canvas, row_data, theme):
  """
  Renders a progress bar onto the given canvas using the row data and theme colors.

  Parameters:
    row_canvas (Image): The PIL image to draw onto.
    row_data (dict): Badge set row data. Requires 'percentage' key.
    theme (str): User-selected theme name (e.g., "green", "orange").
  """

  colors = get_theme_colors(theme)
  gradient_end_color = (24, 24, 24)

  dims = _get_completion_row_dimensions()

  draw = ImageDraw.Draw(row_canvas)
  percentage_width = int((row_data["percentage"] / 100) * dims.bar_w)

  if row_data["percentage"] < 100:
    bar_fill = Image.new("RGBA", (dims.bar_w, dims.bar_h), (0, 0, 0, 0))
    gradient_start = int(percentage_width * 0.8)

    for x in range(gradient_start):
      for y in range(dims.bar_h):
        bar_fill.putpixel((x, y), (*colors.darker_highlight, 255))

    for x in range(gradient_start, percentage_width):
      fade_ratio = (x - gradient_start) / max(1, (percentage_width - gradient_start))
      r = int((colors.darker_highlight[0] * (1 - fade_ratio)) + (gradient_end_color[0] * fade_ratio))
      g = int((colors.darker_highlight[1] * (1 - fade_ratio)) + (gradient_end_color[1] * fade_ratio))
      b = int((colors.darker_highlight[2] * (1 - fade_ratio)) + (gradient_end_color[2] * fade_ratio))
      for y in range(dims.bar_h):
        bar_fill.putpixel((x, y), (r, g, b, 255))

    for x in range(percentage_width, dims.bar_w):
      for y in range(dims.bar_h):
        bar_fill.putpixel((x, y), (*gradient_end_color, 255))

    rounded_mask = Image.new("L", (dims.bar_w, dims.bar_h), 0)
    draw_mask = ImageDraw.Draw(rounded_mask)
    draw_mask.rounded_rectangle((0, 0, dims.bar_w, dims.bar_h), radius=dims.bar_h // 2, fill=255)
    row_canvas.paste(bar_fill, (dims.bar_x, dims.bar_y), rounded_mask)
  else:
    draw.rounded_rectangle(  (
        dims.bar_x,
        dims.bar_y,
        dims.bar_x + percentage_width,
        dims.bar_y + dims.bar_h
      ),
      fill=colors.darker_highlight,
      radius=dims.bar_h // 2
    )


async def compose_empty_completion_row(theme, message: str = "No badges within inventory that match this set type."):
  """
  Returns a fallback row image with a centered message.
  """
  colors = get_theme_colors(theme)
  dims = _get_completion_row_dimensions()

  empty_row_canvas = Image.new("RGBA", (dims.ROW_WIDTH, dims.ROW_HEIGHT), (0, 0, 0, 0))
  draw = ImageDraw.Draw(empty_row_canvas)

  draw.rounded_rectangle(
    (
      dims.bar_x,
      dims.bar_y,
      dims.bar_x + dims.bar_w - 1,
      dims.bar_y + dims.bar_h - 1
    ),
    fill=colors.darker_primary,
    radius=dims.bar_h // 2
  )

  fonts = load_fonts(general_size=48)

  text_w = draw.textlength(message, font=fonts.general)
  draw.text(((dims.row_width - text_w) // 2, 80), message, font=font, fill=colors.highlight)

  return empty_row_canvas


#   _   _ _   _ _
#  | | | | |_(_) |___
#  | |_| |  _| | (_-<
#   \___/ \__|_|_/__/
RowDimensions = namedtuple("RowDimensions", ["row_width", "row_height", "row_margin", "offset", "bar_margin", "bar_x", "bar_w", "bar_h", "bar_y", "start_y"])
def _get_completion_row_dimensions() -> RowDimensions:
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


# _________        .__  .__                 __  .__
# \_   ___ \  ____ |  | |  |   ____   _____/  |_|__| ____   ____   ______
# /    \  \/ /  _ \|  | |  | _/ __ \_/ ___\   __\  |/  _ \ /    \ /  ___/
# \     \___(  <_> )  |_|  |_\  ___/\  \___|  | |  (  <_> )   |  \\___ \
#  \______  /\____/|____/____/\___  >\___  >__| |__|\____/|___|  /____  >
#         \/                      \/     \/                    \/     \/
async def generate_badge_collection_images(user, badge_data, collection_type, collection_label):
  user_id = user.id
  theme = await get_theme_preference(user_id, collection_type)
  layout = _get_collection_grid_layout()

  images = []
  pages = list(paginate(badge_data, layout.badges_per_page))
  total_pages = len(pages)

  for page_badges, page_number in pages:
    canvas = await build_collection_canvas(
      user=user,
      badge_data=page_badges,
      page_number=page_number,
      total_pages=total_pages,
      collection_type=collection_type,
      collection_label=collection_label,
      theme=theme
    )

    await compose_badge_grid_page(canvas, page_badges, theme, collection_type)
    image = buffer_image_to_discord_file(canvas, f"collection_page{page_number}.png")
    images.append(image)

  return images

async def build_collection_canvas(user, badge_data, page_number, total_pages, collection_type, collection_label, theme):
  colors = get_theme_colors(theme)
  dims = _get_collection_grid_dimensions()

  width = dims.canvas_width
  total_rows = max(math.ceil(len(badge_data) / 6) - 1, 1)
  height = dims.header_height + (total_rows * dims.row_height) + dims.footer_height
  canvas = Image.new("RGBA", (width, height), (18, 18, 18, 255))
  draw = ImageDraw.Draw(canvas)

  header_path = f"./images/templates/badges/badge_page_header_{theme}.png"
  row_path = f"./images/templates/badges/badge_page_row_{theme}.png"
  footer_path = f"./images/templates/badges/badge_page_footer_{theme}.png"

  header_img = Image.open(header_path).convert("RGBA")
  row_img = Image.open(row_path).convert("RGBA")
  footer_img = Image.open(footer_path).convert("RGBA")

  canvas.paste(header_img, (0, 0), header_img)
  for i in range(total_rows):
    y = dims.header_height + i * dims.row_height
    canvas.paste(row_img, (0, y), row_img)
  canvas.paste(footer_img, (0, dims.header_height + total_rows * dims.row_height), footer_img)


  fonts = load_fonts()
  if collection_type == "sets":
    collected_count = len([b for b in badge_data if b.get('in_user_collection')])
    total_count = len(badge_data)
  else:
    collected_count = await db_get_badge_count_for_user(user.id)
    total_count = collected_count

  draw_canvas_labels(
    canvas=canvas,
    draw=draw,
    user=user,
    mode=collection_type,
    label=collection_label,
    collected_count=collected_count,
    total_count=total_count,
    page_number=page_number,
    total_pages=total_pages,
    base_w=width,
    base_h=height,
    fonts=fonts,
    colors=colors
  )

  return canvas

async def compose_badge_grid_page(canvas: Image.Image, badge_data: list, theme: str, collection_type: str):
  dims = _get_collection_grid_dimensions()
  layout = _get_collection_grid_layout()
  slot_dims = _get_badge_slot_dimensions()

  for idx, badge in enumerate(badge_data):
    row = idx // layout.badges_per_row
    col = idx % layout.badges_per_row
    x = (dims.margin + col * (slot_dims.slot_width + dims.margin)) + layout.init_x
    y = (dims.header_height + row * dims.row_height) + layout.init_y
    composed_slot = await compose_badge_slot(badge, collection_type, theme)
    canvas.paste(composed_slot, (x, y), composed_slot)

  return canvas


async def compose_badge_slot(badge: dict, collection_type, theme) -> Image.Image:
  """Composes and returns a badge image with overlays applied for locked/special badges."""

  dims = _get_badge_slot_dimensions()
  colors = get_theme_colors(theme)

  border_color = colors.highlight
  text_color = "#FFFFFF"
  add_alpha = False
  if collection_type == 'sets' and not badge.get('in_user_collection'):
    border_color = "#909090"
    text_color = "#888888"
    add_alpha = True

  # Load image and thumbnailicize
  badge_image = load_badge_image(badge['badge_filename'])
  if add_alpha:
    # Create a mask layer to apply 1/4th opacity to for uncollected badges
    badge_alpha = badge_image.copy()
    badge_alpha.putalpha(64)
    badge_image.paste(badge_alpha, badge_image)
  badge_image.thumbnail((dims.thumbnail_width, dims.thumbnail_height), Image.ANTIALIAS)

  # Create Badge Canvas
  badge_canvas = Image.new('RGBA', (dims.thumbnail_width, dims.thumbnail_height), (255, 255, 255, 0))
  badge_canvas.paste(
   badge_image, (int((dims.thumbnail_width - badge_image.size[0]) // 2), int((dims.thumbnail_width - badge_image.size[1]) // 2))
  )
  badge_canvas = badge_canvas.resize((dims.thumbnail_width, dims.thumbnail_height))

  # Create Slot Canvas
  slot_canvas = Image.new("RGBA", (dims.slot_width, dims.slot_height), (0, 0, 0, 0))
  draw = ImageDraw.Draw(slot_canvas)
  draw.rounded_rectangle( (0, 0, dims.slot_width, dims.slot_height), fill="#000000", outline=border_color, width=4, radius=32 )

  # Slot Canvas Dimensions
  b_canvas_width, b_canvas_height = badge_canvas.size
  offset_x = min(0, (dims.slot_width) - b_canvas_width) + 4 # align center, account for border
  offset_y = 20

  # Stamp Badge Canvas on Slot Canvas
  slot_canvas.paste(badge_canvas, (dims.badge_padding + offset_x, offset_y), badge_canvas)

  # Slot Text
  fonts = load_fonts()
  # Draw badge name label
  text = badge.get("badge_name", "")
  wrapped = textwrap.fill(text, width=30)

  # Calculate text block position
  text_bbox = draw.multiline_textbbox((0, 0), wrapped, font=fonts.label)
  text_block_width = text_bbox[2] - text_bbox[0]
  text_x = (dims.slot_width - text_block_width) // 2
  text_y = 222

  draw.multiline_text((text_x, text_y), wrapped, font=fonts.label, fill=text_color, align="center")

  overlay = None
  if badge.get("special"):
    overlay = Image.open(f"./images/templates/badges/special_icon.png").convert("RGBA")
  elif badge.get("locked"):
    overlay = Image.open(f"./images/templates/badges/lock_icon.png").convert("RGBA")

  if overlay:
    slot_canvas.paste(overlay, (dims.slot_width - 54, 16), overlay)

  return slot_canvas


#   _   _ _   _ _
#  | | | | |_(_) |___
#  | |_| |  _| | (_-<
#   \___/ \__|_|_/__/
CollectionGridDimensions = namedtuple("CollectionGridDimensions", ["margin", "header_height", "footer_height", "row_height", "canvas_width"])
def _get_collection_grid_dimensions() -> CollectionGridDimensions:
  return CollectionGridDimensions(
    margin=10,
    header_height=530,
    footer_height=200,
    row_height=290,
    canvas_width=1890
  )

CollectionGridLayout = namedtuple("CollectionGridLayout", ["badges_per_page", "badges_per_row", "init_x", "init_y"])
def _get_collection_grid_layout() -> CollectionGridLayout:
  return CollectionGridLayout(
    badges_per_page=30,
    badges_per_row=6,
    init_x=90,
    init_y=-280
  )

BadgeSlotDimensions = namedtuple("BadgeSlotDimensions", ["slot_width", "slot_height", "badge_width", "badge_height", "badge_padding", "thumbnail_width", "thumbnail_height"])
def _get_badge_slot_dimensions() -> BadgeSlotDimensions:
  return BadgeSlotDimensions(
    slot_width=280,
    slot_height=280,
    badge_width=200,
    badge_height=200,
    badge_padding=40,
    thumbnail_width=190,
    thumbnail_height=190
  )

def buffer_image_to_discord_file(image: Image.Image, filename: str) -> discord.File:
  buf = io.BytesIO()
  image.save(buf, format="PNG")
  buf.seek(0)
  return discord.File(buf, filename=filename)


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


# ________                      .__
# \_____  \  __ __   ___________|__| ____   ______
#  /  / \  \|  |  \_/ __ \_  __ \  |/ __ \ /  ___/
# /   \_/.  \  |  /\  ___/|  | \/  \  ___/ \___ \
# \_____\ \_/____/  \___  >__|  |__|\___  >____  >
#        \__>           \/              \/     \/
async def db_set_user_badge_page_color_preference(user_id, type, color):
  async with AgimusDB() as query:
    if type == "collection":
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

    if type == "collection":
      sql = "SELECT badge_showcase_color AS color_preference FROM user_preferences WHERE user_discord_id = %s"
    elif type == "sets":
      sql = "SELECT badge_sets_color AS color_preference FROM user_preferences WHERE user_discord_id = %s"

    await query.execute(sql, vals)
    result = await query.fetchone()
  color_preference = result['color_preference']
  return color_preference
