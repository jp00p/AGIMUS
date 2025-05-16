import functools
import gc
import tempfile
import time

from asyncio import to_thread
from concurrent.futures import ThreadPoolExecutor
from collections import namedtuple
from emoji import EMOJI_DATA
from functools import partial
from pathlib import Path

from common import *

from queries.badge_info import *
from queries.badge_instances import *

from utils.animation_cache import *
from utils.badge_cache import *
from utils.crystal_effects import apply_crystal_effect
from utils.encode_utils import encode_webp
from utils.prestige import PRESTIGE_TIERS, PRESTIGE_THEMES
from utils.thread_utils import threaded_image_open, threaded_image_open_no_convert

BEEP_BOOPS = [
  "... beep boop beep ...",
  ". boop boop .",
  ".. boop boop ba boop ..",
  "... beep BOOP boop BEEP ...",
  ". BEEP BEEP BEEP .",
  ".. BOOP beep BOOP BOOP ..",
  ".. beep ba beep boop ba boop ..",
  "...  ..... BEEP .....  ...",
  ".. BOOP beep BOOP ..",
  "... BooOOOOoooOOoOoOooooooP ...",
  ".. beep BEEEEP beep (boop) ..",
  ".... beep-beep ba-boop-boop ....",
  ". BOOP .",
  ".. beep ba-da boop ..",
]

# -> utils.image_utils

# _________                         __                 __
# \_   ___ \  ____   ____   _______/  |______    _____/  |_  ______
# /    \  \/ /  _ \ /    \ /  ___/\   __\__  \  /    \   __\/  ___/
# \     \___(  <_> )   |  \\___ \  |  |  / __ \|   |  \  |  \___ \
#  \______  /\____/|___|  /____  > |__| (____  /___|  /__| /____  >
#         \/            \/     \/            \/     \/          \/
BADGE_PATH = "./images/badges/"
BADGE_SIZE = (300, 300)

# Icons
SPECIAL_ICON = None
LOCK_ICON = None

async def preload_image_assets():
  global SPECIAL_ICON, LOCK_ICON
  if SPECIAL_ICON is None:
    SPECIAL_ICON = await threaded_image_open("./images/templates/badges/special_icon.png")
  if LOCK_ICON is None:
    LOCK_ICON = await threaded_image_open("./images/templates/badges/lock_icon.png")

#  ____ ___   __  .__.__
# |    |   \_/  |_|__|  |   ______
# |    |   /\   __\  |  |  /  ___/
# |    |  /  |  | |  |  |__\___ \
# |______/   |__| |__|____/____  >
#                              \/

async def load_badge_image(filename):
  path = os.path.join(BADGE_PATH, filename)
  return await threaded_image_open(path)

async def load_and_prepare_badge_thumbnail(filename):
  return await get_cached_base_badge_canvas(filename)

async def prepare_badges_with_crystal_effects(badge_list: list[dict]) -> list[tuple[dict, list[Image.Image]]]:
  """
  Loads and applies crystal effects to a list of badge instances.

  Returns:
    List of tuples: (badge_dict, image_frames)
  """

  async def prepare(badge):
    badge_image = await get_cached_base_badge_canvas(badge['badge_filename'])
    result = await apply_crystal_effect(badge_image, badge)
    return badge, result

  return await asyncio.gather(*(prepare(b) for b in badge_list))

def paginate(data_list, items_per_page):
  for i in range(0, len(data_list), items_per_page):
    yield data_list[i:i + items_per_page], (i // items_per_page) + 1

def normalize_frame_stacks(row_stacks):
  max_len = max(len(stack) for stack in row_stacks)
  return [
    [frames[i % len(frames)] for i in range(max_len)]
    for frames in row_stacks
  ]



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
  colors = THEME_TO_RGBS.get(theme, THEME_TO_RGBS['green'])
  primary = colors['primary']
  highlight = colors['highlight']

  darker_primary = tuple(
    int(channel * 0.65) if index < 3 else channel
    for index, channel in enumerate(primary)
  )

  darker_highlight = tuple(
    int(channel * 0.85) if index < 3 else channel
    for index, channel in enumerate(highlight)
  )

  return ThemeColors(primary, highlight, darker_primary, darker_highlight)

THEME_TO_RGBS = {
  'orange': {
    'primary': (189, 151, 137),
    'highlight': (186, 111, 59)
  },
  'purple': {
    'primary': (100, 85, 161),
    'highlight': (87, 64, 183)
  },
  'teal': {
    'primary': (141, 185, 181),
    'highlight': (71, 170, 177)
  },
  'gold': { # Used for Trade images
    'primary': (213, 172, 91),
    'highlight': (255, 215, 0)
  },
  'green': { # Default if not explicit
    'primary': (153, 185, 141),
    'highlight': (84, 177, 69)
  },

  # Prestige Themes
  "nebula": {
    "primary": PRESTIGE_THEMES[1]["primary"],
    "highlight": PRESTIGE_THEMES[1]["highlight"]
  },
  "galaxy": {
    "primary": PRESTIGE_THEMES[2]["primary"],
    "highlight": PRESTIGE_THEMES[2]["highlight"]
  },
  "supernova": {
    "primary": PRESTIGE_THEMES[3]["primary"],
    "highlight": PRESTIGE_THEMES[3]["highlight"]
  },
  "cascade": {
    "primary": PRESTIGE_THEMES[4]["primary"],
    "highlight": PRESTIGE_THEMES[4]["highlight"]
  },
  "nexus": {
    "primary": PRESTIGE_THEMES[5]["primary"],
    "highlight": PRESTIGE_THEMES[5]["highlight"]
  },
  "transcendence": {
    "primary": PRESTIGE_THEMES[6]["primary"],
    "highlight": PRESTIGE_THEMES[6]["highlight"]
  }
}

# ___________            __
# \_   _____/___   _____/  |_  ______
#  |    __)/  _ \ /    \   __\/  ___/
#  |     \(  <_> )   |  \  |  \___ \
#  \___  / \____/|___|  /__| /____  >
#      \/             \/          \/
_FONT_CACHE = {}
def get_cached_font(font_path, size):
  cache_key = f"{font_path}__{size}"
  if _FONT_CACHE.get(cache_key):
    return _FONT_CACHE[cache_key]

  font = ImageFont.truetype(font_path, size)
  _FONT_CACHE[cache_key] = font
  return font

FontSet = namedtuple("FontSet", ["title", "footer", "total", "pages", "label", "general"])
def load_fonts(title_size=55, footer_size=50, total_size=27, page_size=40, label_size=11, general_size=35, fallback=True):
  try:
    return FontSet(
      title=get_cached_font("fonts/lcars3.ttf", title_size),
      footer=get_cached_font("fonts/lcars3.ttf", footer_size),
      total=get_cached_font("fonts/lcars3.ttf", total_size),
      pages=get_cached_font("fonts/lcars3.ttf", page_size),
      label=get_cached_font("fonts/context_bold.ttf", label_size),
      general=get_cached_font("fonts/lcars3.ttf", general_size)
    )
  except:
    if fallback:
      default = ImageFont.load_default()
      return FontSet(default, default, default, default, default, default)
    raise


# ________                              .__         ___________              __
# \______ \ ___.__. ____ _____    _____ |__| ____   \__    ___/___ ___  ____/  |_
#  |    |  <   |  |/    \\__  \  /     \|  |/ ___\    |    |_/ __ \\  \/  /\   __\
#  |    `   \___  |   |  \/ __ \|  Y Y  \  \  \___    |    |\  ___/ >    <  |  |
# /_______  / ____|___|  (____  /__|_|  /__|\___  >   |____| \___  >__/\_ \ |__|
#         \/\/         \/     \/      \/        \/               \/      \/
# (Handles dynamic resizing and emoji)
async def draw_dynamic_text(
  canvas: Image.Image,
  draw: ImageDraw.ImageDraw,
  position: tuple,
  text: str,
  max_width: int,
  font_obj: ImageFont.FreeTypeFont,
  starting_size=55,
  min_size=15,
  fill=(255, 255, 255),
  centered=False
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
  total_width = sum(get_width(cluster, font, emoji_size) for cluster in clusters)

  x, y = position
  current_x = x - total_width // 2 if centered else x

  for cluster in clusters:
    if is_emoji(cluster):
      emoji_file = EMOJI_IMAGE_PATH / emoji_to_filename(cluster)
      if emoji_file.exists():
        emoji_img = await threaded_image_open(emoji_file)
        emoji_img = emoji_img.resize((emoji_size, emoji_size))
        canvas.paste(emoji_img, (int(current_x), int(y)), emoji_img)
        current_x += emoji_size
      else:
        logger.warning(f"[emoji-missing] {cluster} → {emoji_file}")
    else:
      draw.text((current_x, y), cluster, font=font, fill=fill)
      current_x += font.getlength(cluster)

  return total_width

EMOJI_IMAGE_PATH = Path("fonts/twemoji")

def is_emoji(seq: str) -> bool:
  return seq in EMOJI_DATA

def emoji_to_filename(emoji_seq: str) -> str:
  return "-".join(f"{ord(c):x}" for c in emoji_seq) + ".png"

def split_text_into_emoji_clusters(text: str):
  return regex.findall(r'\X', text)


# _________        .__  .__                 __  .__
# \_   ___ \  ____ |  | |  |   ____   _____/  |_|__| ____   ____   ______
# /    \  \/ /  _ \|  | |  | _/ __ \_/ ___\   __\  |/  _ \ /    \ /  ___/
# \     \___(  <_> )  |_|  |_\  ___/\  \___|  | |  (  <_> )   |  \\___ \
#  \______  /\____/|____/____/\___  >\___  >__| |__|\____/|___|  /____  >
#         \/                      \/     \/                    \/     \/
async def generate_badge_collection_images(user, prestige, badge_data, collection_type, collection_label, discord_message=None):
  start = time.perf_counter()
  logger.info("[timing] Starting generate_badge_collection_images")

  layout = _get_collection_grid_layout()
  theme = (
    await get_theme_preference(user.id, collection_type)
    if prestige == 0
    else PRESTIGE_TIERS[prestige].lower()
  )

  images = []
  pages = list(paginate(badge_data, layout.badges_per_page))
  total_pages = len(pages)

  for page_badges, page_number in pages:
    if discord_message:
      try:
        await discord_message.edit(
          embed=discord.Embed(
            title="Processing Request",
            description=f"Working on Page {page_number} of {total_pages}...",
            color=discord.Color.blurple()
          ).set_footer(text=random.choice(BEEP_BOOPS))
        )
      except discord.errors.NotFound:
        # The user may have dismissed the original message so just catch and pass
        pass

    canvas_start = time.perf_counter()
    canvas = await build_collection_canvas(
      user,
      prestige,
      page_badges,
      badge_data,
      page_number,
      total_pages,
      collection_label,
      collection_type,
      theme
    )
    canvas_end = time.perf_counter()
    logger.info(f"[timing] build_collection_canvas took {round(canvas_end - canvas_start, 2)}s")

    final = await compose_badge_grid(
      canvas,
      page_badges,
      theme,
      collection_type
    )

    if isinstance(final, list):
      webp_buf = await encode_webp(final)
      images.append(discord.File(webp_buf, filename=f"collection_page{page_number}.webp"))
    else:
      buf = io.BytesIO()
      final.save(buf, format="PNG")
      buf.seek(0)
      images.append(discord.File(buf, filename=f"collection_page{page_number}.png"))

  end = time.perf_counter()
  logger.info(f"[benchmark] generate_badge_collection_images() took {round(end - start, 2)} seconds")

  gc.collect()
  return images

async def build_collection_canvas(user, prestige, page_data, all_data, page_number, total_pages, collection_label, collection_type, theme):
  total_rows = max(math.ceil(len(page_data) / 6) - 1, 0)

  if collection_type == "sets":
    title_text = f"{user.display_name}'s Badge Set ({PRESTIGE_TIERS[prestige]})"
    collected_count = len([b for b in all_data if b.get('in_user_collection')])
    total_count = len(all_data)
  else:
    title_text = f"{user.display_name}'s Badge Collection ({PRESTIGE_TIERS[prestige]})"
    collected_count = len(all_data)
    total_count = await db_get_max_badge_count()

  if collection_label:
    title_text += f": {collection_label}"

  canvas = await build_display_canvas(
    user=user,
    theme=theme,
    layout_type="collection",
    content_rows=total_rows,
    page_number=page_number,
    total_pages=total_pages,
    title_text=title_text,
    footer_left_text=f"{total_count}",
    footer_center_text=f"{collected_count} ON THE USS HOOD"
  )

  return canvas

async def compose_badge_grid(canvas, badge_data, theme, collection_type):
  logger.info("[timing] compose_badge_grid() entry")
  start_total = time.perf_counter()

  # Stage 1: load + crystal effects (async)
  logger.info("[timing] Starting Stage 1: load + crystal effects")
  t1 = time.perf_counter()
  prepared = await prepare_badges_with_crystal_effects(badge_data)
  t2 = time.perf_counter()
  logger.info(f"[timing] Stage 1 complete in {round(t2 - t1, 2)}s")

  # Stage 2: slot composition (threaded)
  logger.info("[timing] Starting Stage 2: slot composition")
  loop = asyncio.get_running_loop()
  t2b = time.perf_counter()
  # slot_frame_stacks = await asyncio.gather(*[
  #   loop.run_in_executor(
  #     THREAD_POOL,
  #     _compose_grid_slot,
  #     badge,
  #     collection_type,
  #     theme,
  #     image
  #   )
  #   for badge, image in prepared
  # ])
  slot_frame_stacks = await loop.run_in_executor(
    THREAD_POOL,
    lambda: [
      _compose_grid_slot(badge, collection_type, theme, image)
      for badge, image in prepared
    ]
  )
  t3 = time.perf_counter()
  logger.info(f"[timing] Stage 2 complete in {round(t3 - t2b, 2)}s")
  del prepared
  gc.collect()

  # Compute slot positions
  dims = _get_collection_grid_dimensions()
  layout = _get_collection_grid_layout()
  slot_dims = _get_badge_slot_dimensions()
  positions = []
  for idx in range(len(badge_data)):
    row, col = divmod(idx, layout.badges_per_row)
    x = dims.margin + col * (slot_dims.slot_width + dims.margin) + layout.init_x
    y = dims.header_height + row * dims.row_height + layout.init_y
    positions.append((x, y))

  # Stage 3: frame stitching (threaded)
  logger.info("[timing] Starting Stage 3: frame stitching")
  def _sync_stitch():
    # Build a grid-only blank canvas (grid_width × grid_height)
    badges_per_row = layout.badges_per_row
    total_rows = (len(badge_data) + badges_per_row - 1) // badges_per_row
    # Full-size slot and margin dims
    slot_w = slot_dims.slot_width
    slot_h = slot_dims.slot_height
    margin = dims.margin
    # Compute grid extents
    grid_w = badges_per_row * slot_w + (badges_per_row - 1) * margin
    grid_h = total_rows * (slot_h + margin)
    blank = Image.new("RGBA", (grid_w, grid_h), (0, 0, 0, 0))

    stitched = []
    for frame_idx in range(max(len(stack) for stack in slot_frame_stacks)):
      # blank grid region only
      empty_grid = blank.copy()
      # paste each slot onto blank grid
      for idx, stack in enumerate(slot_frame_stacks):
        row, col = divmod(idx, badges_per_row)
        x = col * (slot_w + margin)
        y = row * (slot_h + margin)
        slot_frame = stack[frame_idx % len(stack)]
        empty_grid.paste(slot_frame, (x, y), slot_frame)
      # downscale the entire grid
      half_grid = empty_grid.reduce(2)
      # overlay onto full-size canvas
      full_frame = canvas.copy()
      full_frame.paste(
        half_grid,
        (layout.init_x + dims.margin, layout.init_y + dims.header_height),
        half_grid
      )
      stitched.append(full_frame)
    return stitched

  stitched = await loop.run_in_executor(THREAD_POOL, _sync_stitch)

  t4 = time.perf_counter()
  logger.info(f"[timing] Stage 3 complete in {round(t4 - t3, 2)}s")
  logger.info(f"[timing] compose_badge_grid total duration: {round(t4 - start_total, 2)}s")

  return stitched if any(len(s) > 1 for s in slot_frame_stacks) else stitched[0]

def _compose_grid_slot(badge, collection_type, theme, badge_image):
  start = time.perf_counter()

  colors = get_theme_colors(theme)

  override_colors = None
  if collection_type == 'sets' and not badge.get('in_user_collection'):
    faded_frames = []
    frames = badge_image if isinstance(badge_image, list) else [badge_image]
    for frame in frames:
      faded = frame.copy()
      faded.putalpha(32)
      base = frame.copy()
      base.paste(faded, faded)
      faded_frames.append(base)
    badge_image = faded_frames
    override_colors = ("#909090", "#888888")
  else:
    badge_image = badge_image if isinstance(badge_image, list) else [badge_image]

  slot_frames = compose_badge_slot(badge, colors, badge_image, override_colors)

  duration = round(time.perf_counter() - start, 3)
  logger.info(f"[timing] compose_grid_slot took {duration}s for badge_id={badge.get('badge_info_id')}")
  return slot_frames


#   _   _ _   _ _
#  | | | | |_(_) |___
#  | |_| |  _| | (_-<
#   \___/ \__|_|_/__/
CollectionGridDimensions = namedtuple("CollectionGridDimensions", ["margin", "header_height", "footer_height", "row_height", "canvas_width"])
def _get_collection_grid_dimensions() -> CollectionGridDimensions:
  return CollectionGridDimensions(
    margin=6,
    header_height=265,
    footer_height=100,
    row_height=145,
    canvas_width=945
  )

CollectionGridLayout = namedtuple("CollectionGridLayout", ["badges_per_page", "badges_per_row", "init_x", "init_y"])
def _get_collection_grid_layout() -> CollectionGridLayout:
  return CollectionGridLayout(
    badges_per_page=30,
    badges_per_row=6,
    init_x=45,
    init_y=-140
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


#   _________       __    _________                       .__          __  .__
#  /   _____/ _____/  |_  \_   ___ \  ____   _____ ______ |  |   _____/  |_|__| ____   ____
#  \_____  \_/ __ \   __\ /    \  \/ /  _ \ /     \\____ \|  | _/ __ \   __\  |/  _ \ /    \
#  /        \  ___/|  |   \     \___(  <_> )  Y Y  \  |_> >  |_\  ___/|  | |  (  <_> )   |  \
# /_______  /\___  >__|    \______  /\____/|__|_|  /   __/|____/\___  >__| |__|\____/|___|  /
#         \/     \/               \/             \/|__|             \/                    \/
async def generate_badge_set_completion_images(user, prestige, badge_data, category, discord_message=None):
  """
  Renders paginated badge completion images using themed components and returns discord.File[]
  """
  dims = _get_canvas_row_dimensions()
  theme = (
    await get_theme_preference(user.id, 'sets')
    if prestige == 0
    else PRESTIGE_TIERS[prestige].lower()
  )

  rows_per_page = 7

  max_badge_count = await db_get_max_badge_count()
  collected_count = await db_get_badge_instances_count_for_user(user.id, prestige=prestige)

  filtered_rows = [r for r in badge_data if r.get("collected", 0) > 0]

  # If we have no data, early return with no data message
  if not filtered_rows:
    canvas = await build_completion_canvas(
      user=user,
      prestige=prestige,
      max_badge_count=max_badge_count,
      collected_count=collected_count,
      category=category,
      page_number=1,
      total_pages=1,
      row_count=0,
      theme=theme
    )

    row_img = await compose_empty_completion_row(theme)
    canvas.paste(row_img, (110, dims.start_y), row_img)

    image_file = buffer_image_to_discord_file(canvas, f"completion_no_data.png")
    return [image_file]

  # Otherwise, paginate out the rows and create the images
  pages = list(paginate(filtered_rows, rows_per_page))
  total_pages = len(pages)

  images = []
  for page_rows, page_number in pages:
    if discord_message:
      try:
        await discord_message.edit(
          embed=discord.Embed(
            title="Processing Request",
            description=f"Working on Page {page_number} of {total_pages}...",
            color=discord.Color.blurple()
          ).set_footer(text=random.choice(BEEP_BOOPS))
        )
      except discord.errors.NotFound:
        # The user may have dismissed the original message so just catch and pass
        pass

    canvas = await build_completion_canvas(
      user=user,
      prestige=prestige,
      max_badge_count=max_badge_count,
      collected_count=collected_count,
      category=category,
      page_number=page_number,
      total_pages=total_pages,
      row_count=len(page_rows) - 1,
      theme=theme
    )

    current_y = dims.start_y
    for row_data in page_rows:
      row_img = await compose_completion_row(row_data, theme)
      canvas.paste(row_img, (55, current_y), row_img)
      current_y += dims.row_height + dims.row_margin
      del row_img
      gc.collect()

    image_file = buffer_image_to_discord_file(canvas, f"completion_page_{page_number}.png")
    images.append(image_file)
    del canvas
    gc.collect()

  return images


async def build_completion_canvas(user, prestige, max_badge_count, collected_count, category, page_number, total_pages, row_count, theme):
  title_text = f"{user.display_name}'s Badge Completion ({PRESTIGE_TIERS[prestige]}): {category.replace('_', ' ').title()}"

  canvas = await build_display_canvas(
    user=user,
    theme=theme,
    layout_type="completion",
    content_rows=row_count,
    page_number=page_number,
    total_pages=total_pages,
    title_text=title_text,
    footer_left_text=f"{max_badge_count}",
    footer_center_text=f"{collected_count} ON THE USS HOOD",
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
  dims = _get_canvas_row_dimensions()

  row_canvas = Image.new("RGBA", (dims.row_width, dims.row_height), (0, 0, 0, 0))
  draw = ImageDraw.Draw(row_canvas)

  draw.rounded_rectangle(
    (0, 0, dims.row_width, dims.row_height),
    fill="#181818",
    outline="#181818",
    width=4,
    radius=32
  )

  fonts = load_fonts(title_size=80, general_size=60)

  title = row_data.get("name") or "Unassociated"
  draw.text((dims.offset, 40), title, font=fonts.title, fill=colors.highlight)

  draw.text(
    (dims.row_width - 10, 85),
    f"{row_data['percentage']}% ({row_data['collected']} of {row_data['total']})",
    fill=colors.highlight,
    font=fonts.general,
    anchor="rb"
  )

  await draw_completion_row_progress_bar(row_canvas, row_data, theme)

  if row_data.get("featured_badge"):
    try:
      badge_path = os.path.join(BADGE_PATH, row_data["featured_badge"])
      badge_img = await threaded_image_open(badge_path)
      badge_img.thumbnail((100, 100))
      row_canvas.paste(badge_img, (12, 12), badge_img)
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

  dims = _get_canvas_row_dimensions()

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


async def compose_empty_completion_row(theme, message: str = "No Data Available"):
  """
  Returns a fallback row image with a centered message.
  """
  colors = get_theme_colors(theme)
  dims = _get_canvas_row_dimensions()

  row_canvas = Image.new("RGBA", (dims.row_width, dims.row_height), (0, 0, 0, 0))
  draw = ImageDraw.Draw(row_canvas)

  draw.rounded_rectangle(
    (0, 0, dims.row_width, dims.row_height),
    fill="#181818",
    outline="#181818",
    width=4,
    radius=32
  )

  fonts = load_fonts(title_size=80)

  text_w = draw.textlength(message, font=fonts.title)
  draw.text(((dims.row_width - text_w) // 2, (dims.row_height // 2) - 25), message, font=fonts.title, fill=colors.highlight)

  return row_canvas


#   _   _ _   _ _
#  | | | | |_(_) |___
#  | |_| |  _| | (_-<
#   \___/ \__|_|_/__/
CanvasRowDimensions = namedtuple("CanvasRowDimensions", ["row_width", "row_height", "row_margin", "offset", "bar_margin", "bar_x", "bar_w", "bar_h", "bar_y", "start_y"])
def _get_canvas_row_dimensions() -> CanvasRowDimensions:
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
  row_width = 850
  row_height = 140
  row_margin = 5
  offset = 125
  bar_margin = 20
  bar_x = offset
  bar_w = row_width - offset - bar_margin
  bar_h = 16
  bar_y = row_height - bar_h - 15
  start_y = 122

  return CanvasRowDimensions(
    row_width, row_height, row_margin, offset,
    bar_margin, bar_x, bar_w, bar_h, bar_y,
    start_y
  )


# _________                         __         .__       _____                .__  _____                __
# \_   ___ \_______ ___.__. _______/  |______  |  |     /     \ _____    ____ |__|/ ____\____   _______/  |_
# /    \  \/\_  __ <   |  |/  ___/\   __\__  \ |  |    /  \ /  \\__  \  /    \|  \   __\/ __ \ /  ___/\   __\
# \     \____|  | \/\___  |\___ \  |  |  / __ \|  |__ /    Y    \/ __ \|   |  \  ||  | \  ___/ \___ \  |  |
#  \______  /|__|   / ____/____  > |__| (____  /____/ \____|__  (____  /___|  /__||__|  \___  >____  > |__|
#         \/        \/         \/            \/               \/     \/     \/              \/     \/
async def generate_crystal_manifest_images(user: discord.User, crystal_data: list[dict], rarity: str, emoji: str, return_buffers: bool = False) -> list[tuple[io.BytesIO, str]]:
  """
  Generates paginated inventory-style crystal manifest images for a user's unattuned crystals.

  Args:
    user: The Discord user.
    crystal_data: A list of crystal instance dicts filtered by rarity.
    rarity: The rarity name, for header labeling.
    emoji: The rarity's emoji, for footer labeling.

  Returns:
    List of (BytesIO, filename) tuples.
  """
  theme = 'teal'
  dims = _get_canvas_row_dimensions()
  rows_per_page = 7

  pages = list(paginate(crystal_data, rows_per_page))
  total_pages = len(pages)

  results = []

  for page_rows, page_number in pages:
    canvas = await build_crystal_manifest_canvas(
      user=user,
      all_crystal_data=crystal_data,
      page_number=page_number,
      total_pages=total_pages,
      row_count=max(len(page_rows) - 1, 0),
      rarity=rarity,
      emoji=emoji,
      theme=theme
    )

    if not page_rows:
      empty_row = await compose_empty_crystal_manifest_row(theme)
      frame = canvas.copy()
      frame.paste(empty_row, (55, dims.start_y), empty_row)
      buf = io.BytesIO()
      frame.save(buf, format="PNG")
      buf.seek(0)
      filename = f"crystal_manifest_{rarity}_{page_number}.png"
      results.append((buf, filename))
      continue

    prepared_rows = await asyncio.gather(*[
      compose_crystal_manifest_row(crystal, theme) for crystal in page_rows
    ])

    animated = any(isinstance(row, list) and len(row) > 1 for row in prepared_rows)
    row_stacks = [r if isinstance(r, list) else [r] for r in prepared_rows]
    aligned_stacks = normalize_frame_stacks(row_stacks)

    frame_stack = []
    for frame_index in range(len(aligned_stacks[0])):
      frame = canvas.copy()
      current_y = dims.start_y
      for row_frames in aligned_stacks:
        frame.paste(row_frames[frame_index], (55, current_y), row_frames[frame_index])
        current_y += dims.row_height + dims.row_margin
      frame_stack.append(frame)

    if animated:
      webp_buf = await encode_webp(frame_stack)
      filename = f"crystal_manifest_{rarity}_{page_number}.webp"
      results.append((webp_buf, filename))
    else:
      buf = io.BytesIO()
      frame_stack[0].save(buf, format="PNG")
      buf.seek(0)
      filename = f"crystal_manifest_{rarity}_{page_number}.png"
      results.append((buf, filename))

    del frame_stack, row_stacks, prepared_rows, aligned_stacks
    gc.collect()

  return results


async def build_crystal_manifest_canvas(user: discord.User, all_crystal_data, page_number: int, total_pages: int, row_count: int, rarity: str, emoji:str, theme: str) -> Image.Image:
  """
  Constructs the base canvas for a crystal manifest page.
  """
  canvas = await build_display_canvas(
    user=user,
    theme=theme,
    layout_type="manifest",
    content_rows=row_count,
    page_number=page_number,
    total_pages=total_pages,
    title_text=f"{user.display_name}'s {rarity.title()} Crystal Manifest",
    footer_center_text=f"{len(all_crystal_data)} Available"
  )

  # Draw the rarity emoji in the bottom left corner
  fonts = load_fonts()
  w, h = canvas.size
  draw = ImageDraw.Draw(canvas)
  await draw_dynamic_text(canvas, draw, text=emoji, position=(42, h - 65), font_obj=fonts.general, max_width=75, starting_size=60)

  return canvas

_DUMMY_BADGE_INFO_CACHE = None
async def compose_crystal_manifest_row(crystal: dict, theme: str) -> list[Image.Image]:
  """
  Composes a single crystal manifest row.
  """
  dims = _get_canvas_row_dimensions()
  colors = get_theme_colors(theme)
  row_canvas = get_crystal_manifest_row_canvas()
  draw = ImageDraw.Draw(row_canvas)

  fonts = load_fonts(title_size=70, general_size=40)

  icon_path = f"./images/templates/crystals/icons/{crystal['icon']}"
  try:
    icon_img = await threaded_image_open(icon_path)
    icon_img.thumbnail((100, 100))
    row_canvas.paste(icon_img, (15, 20), icon_img)
  except Exception as e:
    logger.warning(f"[manifest] Could not load icon at {icon_path}: {e}")

  title_x = dims.offset
  title = crystal['crystal_name']
  draw.text((title_x, 20), title, font=fonts.title, fill=colors.highlight)
  if 'instance_count' in crystal and crystal['instance_count'] > 1:
    count_text = f"(x{crystal['instance_count']})"
    # Calculate width of the name so we can offset the count right after it
    title_width = draw.textlength(title, font=fonts.title)
    count_x = title_x + title_width + 10  # small padding after name
    count_y = 40  # align with name baseline
    draw.text((count_x, count_y), count_text, font=fonts.general, fill=colors.darker_highlight)

  await draw_dynamic_text(row_canvas, draw, text=crystal['description'], font_obj=fonts.general, position=(title_x, 82), max_width=(dims.row_width - (dims.offset * 2)), starting_size=40, fill=(221, 221, 221))

  # Render preview of crystal effect on "dummy" badge
  global _DUMMY_BADGE_INFO_CACHE
  if _DUMMY_BADGE_INFO_CACHE is None:
    _DUMMY_BADGE_INFO_CACHE = await db_get_badge_info_by_name("Starfleet Crew 2160s (Kelvin)")
  dummy_badge_info = _DUMMY_BADGE_INFO_CACHE
  dummy_badge = {
    **dummy_badge_info,
    'badge_info_id': dummy_badge_info['id'],
    'crystal_id': crystal['crystal_instance_id'],
    'effect': crystal['effect']
  }

  badge_img = await get_cached_base_badge_canvas(dummy_badge['badge_filename'])
  preview_frames = await apply_crystal_effect(badge_img, dummy_badge, crystal=crystal)
  if not isinstance(preview_frames, list):
    preview_frames = [preview_frames]

  row_frames = []
  for frame in preview_frames:
    composed = row_canvas.copy()
    preview = frame.copy()
    preview.thumbnail((100, 100))
    composed.paste(preview, (dims.row_width - 120, 20), preview)
    row_frames.append(composed)

  return row_frames


async def compose_empty_crystal_manifest_row(theme: str, message: str = "No Crystals Available") -> Image.Image:
  dims = _get_canvas_row_dimensions()
  colors = get_theme_colors(theme)

  row_canvas = get_crystal_manifest_row_canvas()
  draw = ImageDraw.Draw(row_canvas)

  draw.rounded_rectangle(
    (0, 0, dims.row_width, dims.row_height),
    fill="#181818",
    outline="#181818",
    width=4,
    radius=32
  )

  fonts = load_fonts(title_size=80)

  text_w = draw.textlength(message, font=fonts.title)
  draw.text(((dims.row_width - text_w) // 2, (dims.row_height // 2) - 25), message, font=fonts.title, fill=colors.highlight)

  return row_canvas

def get_crystal_manifest_row_canvas():
  dims = _get_canvas_row_dimensions()
  start_color = (24, 24, 24, 255)
  end_color = (64, 64, 64, 255)

  row_canvas = Image.new("RGBA", (dims.row_width, dims.row_height), (0, 0, 0, 0))
  gradient = Image.new("RGBA", (dims.row_width, dims.row_height), (0, 0, 0, 0))
  grad_pixels = gradient.load()

  total_diagonal = dims.row_width + dims.row_height
  gradient_start = int(total_diagonal * 0.75)
  gradient_range = total_diagonal - gradient_start

  for y in range(dims.row_height):
    for x in range(dims.row_width):
      distance = x + y
      if distance < gradient_start:
        t = 0.0
      else:
        t = (distance - gradient_start) / gradient_range
        t = min(t, 1.0)  # Clamp to [0, 1]

      r = int(start_color[0] * (1 - t) + end_color[0] * t)
      g = int(start_color[1] * (1 - t) + end_color[1] * t)
      b = int(start_color[2] * (1 - t) + end_color[2] * t)
      a = int(start_color[3] * (1 - t) + end_color[3] * t)
      grad_pixels[x, y] = (r, g, b, a)

  # Rounded corner mask
  mask = Image.new("L", (dims.row_width, dims.row_height), 0)
  mask_draw = ImageDraw.Draw(mask)
  mask_draw.rounded_rectangle(
    (0, 0, dims.row_width, dims.row_height),
    fill=255,
    radius=32
  )

  # Paste the masked gradient into row canvas
  row_canvas.paste(gradient, (0, 0), mask)

  # Optional border
  draw = ImageDraw.Draw(row_canvas)
  draw.rounded_rectangle(
    (0, 0, dims.row_width, dims.row_height),
    outline="#181818",
    width=4,
    radius=32
  )

  return row_canvas

# __________             .___                 _________ __         .__
# \______   \_____     __| _/ ____   ____    /   _____//  |________|__|_____
#  |    |  _/\__  \   / __ | / ___\_/ __ \   \_____  \\   __\_  __ \  \____ \
#  |    |   \ / __ \_/ /_/ |/ /_/  >  ___/   /        \|  |  |  | \/  |  |_> >
#  |______  /(____  /\____ |\___  / \___  > /_______  /|__|  |__|  |__|   __/
#         \/      \/      \/_____/      \/          \/                |__|
async def compose_badge_strip(
  badge_list: list[dict],
  theme = 'gold',
  disable_overlays = False
) -> list[Image.Image]:
  """
  Renders a horizontal badge strip (1 row) using compose_badge_slot for each badge.
  Returns a list of frames (for animation).
  """
  start = time.perf_counter()
  slot_dims = _get_badge_slot_dimensions()

  colors = get_theme_colors(theme)

  padding = 24
  strip_width = len(badge_list) * slot_dims.slot_width + (len(badge_list) - 1) * padding
  strip_height = slot_dims.slot_height
  slot_y_offset = 0

  logger.info(f"[timing] Starting badge strip generation for {len(badge_list)} badges")

  # Apply crystal effects and prepare all badge image stacks
  prepared = await prepare_badges_with_crystal_effects(badge_list)

  loop = asyncio.get_running_loop()
  all_badge_frames = await asyncio.gather(*[
    loop.run_in_executor(THREAD_POOL,
      partial(compose_badge_slot, badge, colors, image_frames, disable_overlays=disable_overlays)
    )
    for badge, image_frames in prepared
  ])

  max_frames = max(len(stack) for stack in all_badge_frames)

  # Normalize frame stacks
  for i in range(len(all_badge_frames)):
    frames = all_badge_frames[i]
    if len(frames) < max_frames:
      looped = [frames[j % len(frames)] for j in range(max_frames)]
      all_badge_frames[i] = looped

  # Compose output frames using zip
  frames = []
  for frame_group in zip(*all_badge_frames):
    frame = Image.new("RGBA", (strip_width, strip_height), (0, 0, 0, 0))
    x = 0
    for badge_img in frame_group:
      frame.paste(badge_img, (x, slot_y_offset), mask=badge_img)
      x += slot_dims.slot_width + padding
    frames.append(frame)

  elapsed = time.perf_counter() - start
  logger.info(f"[timing] generate_badge_strip completed in {elapsed:.2f}s with {len(frames)} frames")

  del all_badge_frames, prepared
  gc.collect()

  return frames


#   _________.__                             .___
#  /   _____/|  |__ _____ _______   ____   __| _/
#  \_____  \ |  |  \\__  \\_  __ \_/ __ \ / __ |
#  /        \|   Y  \/ __ \|  | \/\  ___// /_/ |
# /_______  /|___|  (____  /__|    \___  >____ |
#         \/      \/     \/            \/     \/
async def generate_badge_preview(user_id, badge, crystal=None, theme=None, disable_overlays=False):
  if not theme:
    theme = await get_theme_preference(user_id, 'collection')
  colors = get_theme_colors(theme)

  badge_image = await get_cached_base_badge_canvas(badge['badge_filename'])
  effect_result = await apply_crystal_effect(badge_image, badge, crystal)

  if crystal:
    badge['crystal_icon'] = crystal.get('icon')
  slot_frames = compose_badge_slot(badge, colors, effect_result, disable_overlays=disable_overlays)

  if len(slot_frames) > 1:
    buf = await encode_webp(slot_frames)
    file = discord.File(buf, filename='preview.webp')
    url = 'attachment://preview.webp'
  else:
    buf = encode_png(slot_frames[0])
    file = discord.File(buf, filename='preview.png')
    url = 'attachment://preview.png'

  return file, url

async def generate_unowned_badge_preview(user_id, badge):
  """
  Unowned badges are never animated or have crystal effects applied to them,
  so this is just a static streamlined version of generate_badge_preview above
  """
  theme = await get_theme_preference(user_id, 'collection')
  colors = get_theme_colors(theme)

  badge_image = await get_cached_base_badge_canvas(badge['badge_filename'])

  slot_frames = compose_badge_slot(badge, colors, badge_image, disable_overlays=None)
  frame = slot_frames[0]

  buf = encode_png(frame)
  file = discord.File(buf, filename='preview.png')
  url = 'attachment://preview.png'

  return file, url

async def generate_singular_badge_slot(badge, border_color=None, crystal=None, show_crystal_icon=False):
  """
  Used by `/profile` to display/show off selected badge
  Just the badge + crystal effects image(s) placed on a simple slot
  (e.g the standard or prestige border/gradient, no badge name/etc)
  """
  dims = _get_badge_slot_dimensions()

  badge_image = await get_cached_base_badge_canvas(badge['badge_filename'])
  effect_result = await apply_crystal_effect(badge_image, badge, crystal)

  if not isinstance(effect_result, list):
    effect_result = [effect_result]

  base_slot_canvas = get_slot_canvas(badge.get('prestige_level', 0), border_color)

  slot_frames = []
  for frame in effect_result:
    slot_canvas = base_slot_canvas.copy()

    target_w = dims.slot_width
    target_h = dims.slot_height

    orig_w, orig_h = frame.size
    aspect = orig_w / orig_h

    if target_w / target_h > aspect:
      new_h = target_h
      new_w = int(new_h * aspect)
    else:
      new_w = target_w
      new_h = int(new_w / aspect)

    scaled_frame = frame.resize((int(new_w * 0.9), int(new_h * 0.9)), resample=Image.Resampling.LANCZOS)

    # Center the scaled frame inside the slot_canvas
    frame_x = round((dims.slot_width - scaled_frame.width) / 2)
    frame_y = round((dims.slot_height - scaled_frame.height) / 2)

    slot_canvas.paste(scaled_frame, (frame_x, frame_y), scaled_frame)

    crystal_icon = badge.get("crystal_icon", None)
    if crystal_icon and show_crystal_icon:
      y_offset = 16
      icon_path = f"./images/templates/crystals/icons/{crystal_icon}"
      try:
        icon_img = Image.open(icon_path).convert("RGBA")
        icon_img.thumbnail((48, 48))
        slot_canvas.paste(icon_img, (dims.slot_width - 46, y_offset), icon_img)
      except Exception as e:
        logger.warning(f"[generate_singular_badge_slot] Could not load icon at {icon_path}: {e}")

    # Final rounded mask to clip anything outside the border
    final_mask = Image.new("L", (dims.slot_width, dims.slot_height), 0)
    ImageDraw.Draw(final_mask).rounded_rectangle(
      (0, 0, dims.slot_width, dims.slot_height),
      radius=32,
      fill=255
    )
    slot_canvas.putalpha(final_mask)
    slot_frames.append(slot_canvas)

  return slot_frames


def encode_png(frame):
  buf = io.BytesIO()
  frame.save(buf, format='PNG')
  buf.seek(0)
  return buf


def compose_badge_slot(
  badge: dict,
  colors,
  image_frames: list[Image.Image],
  override_colors: tuple = None,
  disable_overlays: bool = False,
  resize: bool = False
) -> list[Image.Image]:
  """
  Renders a badge image (with crystal effects pre-applied) into a slot container with border and label.
  Returns a list of slot frames (supporting animation).

  Args:
    badge: Badge dict containing badge metadata.
    colors: ThemeColors namedtuple for current user/theme.
    image_frames: List of PIL.Image frames with effects already applied.
    override_colors: Optional (border_color, text_color) tuple.
    disable_overlays: If True, skips drawing lock/special icons.
    resize: If True, each frame will be resized to 50% after rendering.
  """
  if not isinstance(image_frames, list):
    image_frames = [image_frames]

  dims = _get_badge_slot_dimensions()
  # Use the OG font sizes explicitly
  fonts = load_fonts(
    title_size=110,
    footer_size=100,
    total_size=54,
    page_size=80,
    label_size=20,
    general_size=70
  )

  border_color, text_color = override_colors if override_colors else (colors.highlight, "#FFFFFF")
  base_slot_canvas = get_slot_canvas(badge.get('prestige_level', 0), border_color)

  slot_frames = []
  for frame in image_frames:
    slot_canvas = base_slot_canvas.copy()

    badge_canvas = Image.new('RGBA', (dims.thumbnail_width, dims.thumbnail_height), (255, 255, 255, 0))
    badge_canvas.paste(
      frame,
      ((dims.thumbnail_width - frame.size[0]) // 2, (dims.thumbnail_height - frame.size[1]) // 2),
      frame
    )

    # offset_x = min(0, dims.slot_width - badge_canvas.width) + 4
    offset_y = 20
    paste_x = (dims.slot_width - badge_canvas.width) // 2
    slot_canvas.paste(badge_canvas, (paste_x, offset_y), badge_canvas)

    draw = ImageDraw.Draw(slot_canvas)
    text = badge.get("badge_name", "")
    wrapped = textwrap.fill(text, width=24)
    text_bbox = draw.multiline_textbbox((0, 0), wrapped, font=fonts.label)
    text_block_width = text_bbox[2] - text_bbox[0]
    text_x = (dims.slot_width - text_block_width) // 2
    text_y = 218
    draw.multiline_text((text_x, text_y), wrapped, font=fonts.label, fill=text_color, align="center")

    overlay = None
    if not disable_overlays:
      if badge.get("special"):
        overlay = SPECIAL_ICON
      elif badge.get("locked"):
        overlay = LOCK_ICON
      if overlay:
        slot_canvas.paste(overlay, (dims.slot_width - 42, 16), overlay)

    crystal_icon = badge.get("crystal_icon", None)
    if crystal_icon:
      y_offset = 16
      if overlay:
        y_offset += 38
      icon_path = f"./images/templates/crystals/icons/{crystal_icon}"
      try:
        icon_img = Image.open(icon_path).convert("RGBA")
        icon_img.thumbnail((48, 48))
        slot_canvas.paste(icon_img, (dims.slot_width - 44, y_offset), icon_img)
      except Exception as e:
        logger.warning(f"[compose_badge_slot] Could not load icon at {icon_path}: {e}")

    # Final rounded mask to clip anything outside the border
    final_mask = Image.new("L", (dims.slot_width, dims.slot_height), 0)
    ImageDraw.Draw(final_mask).rounded_rectangle(
      (0, 0, dims.slot_width, dims.slot_height),
      radius=32,
      fill=255
    )
    slot_canvas.putalpha(final_mask)

    if resize:
      # slot_canvas = slot_canvas.resize(
      #   (slot_canvas.width // 2, slot_canvas.height // 2),
      #   resample=Image.Resampling.LANCZOS
      # )
      slot_canvas = slot_canvas.reduce(2)

    slot_frames.append(slot_canvas)

  return slot_frames

# def get_slot_canvas(prestige, standard_border_color):
#   pass

_SLOT_CANVAS_CACHE = {}
def get_slot_canvas(prestige, border_color):

  cache_key = prestige if prestige else border_color
  if _SLOT_CANVAS_CACHE.get(cache_key):
    return _SLOT_CANVAS_CACHE[cache_key]

  dims = _get_badge_slot_dimensions()
  slot_canvas = Image.new("RGBA", (dims.slot_width, dims.slot_height), (0, 0, 0, 0))

  if prestige:
    prestige_theme = PRESTIGE_THEMES.get(prestige)
    gradient = _create_gradient_fill((dims.slot_width, dims.slot_height), prestige_theme["gradient_start"], prestige_theme["gradient_end"])
    mask = Image.new("L", (dims.slot_width, dims.slot_height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, dims.slot_width, dims.slot_height), radius=32, fill=255)
    gradient.putalpha(mask)
    prestige_border = _create_border_overlay((dims.slot_width, dims.slot_height), prestige_theme["border_gradient_colors"])

    slot_canvas = Image.new("RGBA", (dims.slot_width, dims.slot_height), (0, 0, 0, 0))
    slot_canvas.paste(gradient, (0, 0), gradient)
    slot_canvas.paste(prestige_border, (0, 0), prestige_border)
  else:
    # Subtle dark gradient for Standard Tier badges
    gradient = _create_gradient_fill(
      (dims.slot_width, dims.slot_height),
      (5, 5, 5),
      (30, 30, 30)
    )
    mask = Image.new("L", (dims.slot_width, dims.slot_height), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
      (0, 0, dims.slot_width, dims.slot_height),
      radius=32,
      fill=255
    )
    gradient.putalpha(mask)
    border_overlay = Image.new("RGBA", (dims.slot_width, dims.slot_height), (0, 0, 0, 0))
    ImageDraw.Draw(border_overlay).rounded_rectangle(
      (0, 0, dims.slot_width, dims.slot_height),
      outline=border_color,
      width=4,
      radius=32
    )
    slot_canvas = Image.new("RGBA", (dims.slot_width, dims.slot_height), (0, 0, 0, 0))
    slot_canvas.paste(gradient, (0, 0), gradient)
    slot_canvas.paste(border_overlay, (0, 0), border_overlay)

  _SLOT_CANVAS_CACHE[cache_key] = slot_canvas
  return slot_canvas


def _create_gradient_fill(size: tuple[int, int], start_color: tuple[int, int, int], end_color: tuple[int, int, int]) -> Image.Image:
  width, height = size
  gradient = Image.new("RGBA", size)
  for y in range(height):
    for x in range(width):
      t_raw = (x + y) / (width + height)
      t = _ease_out_start(t_raw)
      r = int(start_color[0] * (1 - t) + end_color[0] * t)
      g = int(start_color[1] * (1 - t) + end_color[1] * t)
      b = int(start_color[2] * (1 - t) + end_color[2] * t)
      gradient.putpixel((x, y), (r, g, b, 255))
  return gradient

def _create_border_overlay(size: tuple[int, int], colors: list[tuple[int, int, int]]) -> Image.Image:
  assert len(colors) == 3, "Expected three-color gradient"
  width, height = size
  border = Image.new("RGBA", size)
  for y in range(height):
    for x in range(width):
      t = (x + y) / (width + height)
      if t < 0.5:
        blend = t * 2
        r = int(colors[0][0] * (1 - blend) + colors[1][0] * blend)
        g = int(colors[0][1] * (1 - blend) + colors[1][1] * blend)
        b = int(colors[0][2] * (1 - blend) + colors[1][2] * blend)
      else:
        blend = (t - 0.5) * 2
        r = int(colors[1][0] * (1 - blend) + colors[2][0] * blend)
        g = int(colors[1][1] * (1 - blend) + colors[2][1] * blend)
        b = int(colors[1][2] * (1 - blend) + colors[2][2] * blend)
      border.putpixel((x, y), (r, g, b, 255))

  mask_outer = Image.new("L", size, 0)
  mask_inner = Image.new("L", size, 0)
  draw_outer = ImageDraw.Draw(mask_outer)
  draw_inner = ImageDraw.Draw(mask_inner)
  draw_outer.rounded_rectangle((0, 0, width - 1, height - 1), radius=32, fill=255)
  draw_inner.rounded_rectangle((4, 4, width - 5, height - 5), radius=32 - 4, fill=255)
  border_mask = ImageChops.subtract(mask_outer, mask_inner)
  return Image.composite(border, Image.new("RGBA", size, (0, 0, 0, 0)), border_mask)

def _ease_out_start(t: float) -> float:
  return t ** 2



async def build_display_canvas(
  user: discord.User,
  theme: str,
  layout_type: str,
  content_rows: int,
  page_number: int,
  total_pages: int,
  title_text: str = "",
  footer_left_text: str = "",
  footer_center_text: str = "",
) -> Image.Image:
  """
  Builds a themed display canvas shared by both collection and completion layouts.
  """
  colors = get_theme_colors(theme)

  start = time.perf_counter()

  # TO-DO - Make header and footer fully generic (write all text in image generation so we can simplify this)
  if layout_type == 'collection' or layout_type == 'completion':
    asset_prefix = "images/templates/badges/badge_page_"
    header_img = await threaded_image_open(f"{asset_prefix}header_{theme}.png")
    footer_img = await threaded_image_open(f"{asset_prefix}footer_{theme}.png")
    row_img = await threaded_image_open(f"{asset_prefix}row_{theme}.png")
  else:
    asset_prefix = "images/templates/crystals/manifests/"
    header_img = await threaded_image_open(f"{asset_prefix}crystal_manifest_header.png")
    footer_img = await threaded_image_open(f"{asset_prefix}crystal_manifest_footer.png")
    row_img = await threaded_image_open(f"{asset_prefix}crystal_manifest_row.png")

  header_h = header_img.height
  footer_h = footer_img.height
  row_h = row_img.height
  base_w = header_img.width
  total_h = header_h + footer_h + row_h * content_rows

  canvas = Image.new("RGBA", (base_w, total_h), (0, 0, 0, 0))
  canvas.paste(header_img, (0, 0), header_img)

  for i in range(content_rows):
    y = header_h + i * row_h
    canvas.paste(row_img, (0, y), row_img)

  canvas.paste(footer_img, (0, header_h + content_rows * row_h), footer_img)

  fonts = load_fonts()
  draw = ImageDraw.Draw(canvas)

  await draw_canvas_labels(
    canvas=canvas,
    draw=draw,
    title_text=title_text,
    footer_center_text=footer_center_text,
    footer_left_text=footer_left_text,
    page_number=page_number,
    total_pages=total_pages,
    base_w=base_w,
    base_h=total_h,
    fonts=fonts,
    colors=colors
  )

  duration = round(time.perf_counter() - start, 3)
  logger.info(f"[timing] build_display_canvas took {duration}s")

  return canvas

async def draw_canvas_labels(canvas, draw, title_text, footer_left_text, footer_center_text, page_number, total_pages, base_w, base_h, fonts, colors):
  await draw_dynamic_text(
    canvas=canvas,
    draw=draw,
    position=(50, 32),
    text=title_text,
    max_width=base_w - 100,
    font_obj=fonts.title,
    fill=colors.highlight
  )

  draw.text(
    (295, base_h - 62),
    footer_center_text,
    font=fonts.footer,
    fill=colors.highlight
  )

  await draw_dynamic_text(
    canvas=canvas,
    draw=draw,
    position=(15, base_h - 45),
    text=footer_left_text,
    max_width=100,
    font_obj=fonts.title,
    starting_size=27,
    fill=colors.highlight
  )

  draw.text(
    (base_w - 185, base_h - 60),
    f"PAGE {page_number:02} OF {total_pages:02}",
    font=fonts.pages,
    fill=colors.highlight
  )



# ___________                  .___.__
# \__    ___/___________     __| _/|__| ____    ____
#   |    |  \_  __ \__  \   / __ | |  |/    \  / ___\
#   |    |   |  | \// __ \_/ /_/ | |  |   |  \/ /_/  >
#   |____|   |__|  (____  /\____ | |__|___|  /\___  /
#                       \/      \/         \//_____/
async def generate_badge_trade_images(
  badges: list[dict],
  header_text="",
  footer_text=""
) -> discord.File:
  """
  Generates a trade image showcasing up to 6 badge slots in a horizontal strip format.
  This does not paginate (trades never exceed 6 badges)

  Args:
    badges: List of enriched badge instance dicts.
    user: The Discord user this image is for.
    header_text: Text displayed in the trade image header.
    footer_text: Text displayed in the trade image footer.

  Returns:
    A discord.File containing the image or animation.
  """
  fonts = load_fonts()

  # 1. Load and copy the trade background once
  bg_path = Path("./images/trades/assets/trade_bg.jpg")
  base_bg = Image.open(bg_path).convert("RGBA")

  # 2. Pre-render title + footer ONTO the base_bg once
  trade_canvas = base_bg.copy()
  draw = ImageDraw.Draw(trade_canvas)

  # Title at the top
  await draw_dynamic_text(
    canvas=trade_canvas,
    draw=draw,
    position=(base_bg.width // 2, 40),
    text=header_text,
    max_width=base_bg.width - 40,
    font_obj=fonts.title,
    starting_size=100,
    min_size=38,
    fill=(255, 255, 255),
    centered=True
  )

  # Footer at the bottom
  w = fonts.footer.getlength(footer_text)
  draw.text(((base_bg.width - w) // 2, base_bg.height - 110), footer_text, font=fonts.footer, fill=(255, 255, 255))

  # Early return with empty image if no badges were passed in
  if not badges:
    # If no badges, just return the base background with header/footer text
    frame = trade_canvas.copy()
    buf = io.BytesIO()
    frame.save(buf, format="PNG")
    buf.seek(0)
    return discord.File(buf, filename="trade_showcase.png")

  # 3. Now paste each strip frame centered onto a copy of that base
  # Generate badge strip frames (each frame is a full strip of up to 6 badge slots)
  strip_frames = await compose_badge_strip(badge_list=badges, theme='gold', disable_overlays=True)

  final_frames = []
  for strip in strip_frames:
    frame = trade_canvas.copy()
    x = (frame.width - strip.width) // 2
    y = (frame.height - strip.height) // 2
    frame.paste(strip, (x, y), strip)
    final_frames.append(frame)

  if len(final_frames) == 1:
    buf = io.BytesIO()
    final_frames[0].save(buf, format="PNG")
    buf.seek(0)
    return discord.File(buf, filename="trade_showcase.png"), 'attachment://trade_showcase.png'
  else:
    buf = await encode_webp(final_frames)
    return discord.File(buf, filename="trade_showcase.webp"), 'attachment://trade_showcase.webp'


# __________              .__  .__               __
# \______   \ ____ ______ |  | |__| ____ _____ _/  |_  ___________
#  |       _// __ \\____ \|  | |  |/ ___\\__  \\   __\/  _ \_  __ \
#  |    |   \  ___/|  |_> >  |_|  \  \___ / __ \|  | (  <_> )  | \/
#  |____|_  /\___  >   __/|____/__|\___  >____  /__|  \____/|__|
#         \/     \/|__|                \/     \/
async def generate_crystal_replicator_confirmation_frames(crystal, replicator_type='standard'):
  # Purposeful 5 second delay to build suspense (cached replicator webps return very quickly once generated)...
  await asyncio.sleep(5)

  replicator_confirmation_filename = f"{replicator_type}-crystal_materialization_{crystal['crystal_name']}.webp"

  cached_path = get_cached_crystal_replicator_animation_path(crystal['crystal_name'], replicator_type)
  if cached_path:
    return discord.File(cached_path, filename=replicator_confirmation_filename), replicator_confirmation_filename

  def _sync_build_replicator():
    fps = 12
    duration_seconds = 5
    num_frames = fps * duration_seconds
    start_fade_frame = int(0.5 * fps)
    end_hold_duration = int(1.0 * fps)
    fade_duration = num_frames - start_fade_frame - end_hold_duration
    effect_start_frame = start_fade_frame + 6
    fade_out_frames = 6

    baseline_width, baseline_height = 256, 256
    cropped_align_x = 40
    cropped_align_y_bottom = 90 - 50 + 25 + 10 + baseline_height

    crystal_templates_dir = "./images/templates/crystals"
    base_bg = Image.open(f"{crystal_templates_dir}/{replicator_type}-replicator.png").convert("RGBA")
    icon = Image.open(f"{crystal_templates_dir}/icons/{crystal['icon']}").convert("RGBA")

    bbox = icon.getbbox()
    cropped = icon.crop(bbox)

    x = base_bg.width // 2 - baseline_width // 2 + cropped_align_x + (baseline_width - cropped.width) // 2
    y = cropped_align_y_bottom - cropped.height
    crystal_pos = (x, y)

    effect_dir = f"{crystal_templates_dir}/replicator_effect/"
    effect_filenames = sorted(os.listdir(effect_dir))
    shifted_effect_position = (base_bg.width // 2 - 300 // 2 + 50, 100)
    effect_total_frames = len(effect_filenames)

    frames = []
    for i in range(num_frames):
      frame = base_bg.copy()

      # Crystal fade-in
      if i >= start_fade_frame:
        fade_progress = min(1.0, (i - start_fade_frame) / fade_duration)
        crystal_temp = cropped.copy()
        alpha_mask = crystal_temp.split()[3].point(lambda p: int(p * fade_progress))
        crystal_temp.putalpha(alpha_mask)

        overlay = Image.new("RGBA", frame.size)
        overlay.paste(crystal_temp, crystal_pos, crystal_temp)
        frame = Image.alpha_composite(frame, overlay)

      # Materialization Effect
      effect_index = i - effect_start_frame
      if 0 <= effect_index < effect_total_frames:
        effect_path = os.path.join(effect_dir, effect_filenames[effect_index])
        effect = Image.open(effect_path).convert("RGBA")

        if effect_index >= effect_total_frames - fade_out_frames:
          frame_pos = effect_index - (effect_total_frames - fade_out_frames)
          linear_alpha = 1.0 - (frame_pos / (fade_out_frames - 1))
          faded_effect = effect.copy()
          alpha = faded_effect.split()[3].point(lambda p: int(p * linear_alpha))
          faded_effect.putalpha(alpha)
          effect = faded_effect

        overlay = Image.new("RGBA", frame.size)
        overlay.paste(effect, shifted_effect_position, effect)
        frame = Image.alpha_composite(frame, overlay)

      frames.append(frame)

    # Final crystal-only hold
    for _ in range(fps):
      frame = base_bg.copy()
      crystal_temp = cropped.copy()
      crystal_temp.putalpha(crystal_temp.split()[3])
      overlay = Image.new("RGBA", frame.size)
      overlay.paste(crystal_temp, crystal_pos, crystal_temp)
      frame = Image.alpha_composite(frame, overlay)
      frames.append(frame)

    return frames

  # Off-load CPU-heavy build
  loop = asyncio.get_running_loop()
  frames = await loop.run_in_executor(None, _sync_build_replicator)
  # Encode with async helper
  webp_buf = await encode_webp(frames)
  # Cache the result
  await save_cached_crystal_replicator_animation(webp_buf, crystal['crystal_name'], replicator_type)
  # Return Discord file and filename
  return discord.File(webp_buf, filename=replicator_confirmation_filename), replicator_confirmation_filename

#   _________
#  /   _____/ ________________  ______ ______   ___________
#  \_____  \_/ ___\_  __ \__  \ \____ \\____ \_/ __ \_  __ \
#  /        \  \___|  | \// __ \|  |_> >  |_> >  ___/|  | \/
# /_______  /\___  >__|  (____  /   __/|   __/ \___  >__|
#         \/     \/           \/|__|   |__|        \/
# async def generate_badge_scrapper_confirmation_frames(badges_to_scrap):
#   replicator_image = await threaded_image_open_no_convert(f"./images/templates/scrap/replicator.png")

#   base_image = Image.new("RGBA", (replicator_image.width, replicator_image.height), (0, 0, 0))
#   base_image.paste(replicator_image, (0, 0))

#   # TODO: use get_cached_base_badge_canvas for these...
#   # e.g. b1 = await get_cached_base_badge_canvas(badges_to_scrap[0]['badge_filename'])
#   b1 = await threaded_image_open(f"./images/badges/{badges_to_scrap[0]['badge_filename']}").convert("RGBA").resize((125, 125))
#   b2 = await threaded_image_open(f"./images/badges/{badges_to_scrap[1]['badge_filename']}").convert("RGBA").resize((125, 125))
#   b3 = await threaded_image_open(f"./images/badges/{badges_to_scrap[2]['badge_filename']}").convert("RGBA").resize((125, 125))

#   b_list = [b1, b2, b3]

#   frames = []
#   badge_position_x = 75
#   badge_position_y = 130

#   # Add 30 frames of just the replicator and the badges by themselves
#   for n in range(1, 31):
#     frame = base_image.copy()
#     frame_badges = [b.copy() for b in b_list]

#     current_x = badge_position_x
#     for f_b in frame_badges:
#       frame.paste(f_b, (current_x, badge_position_y), f_b)
#       current_x = current_x + 130

#     frames.append(frame)

#   # Create the badge transporter effect animation
#   for n in range(1, 71):
#     frame = base_image.copy()

#     frame_badges = [b.copy() for b in b_list]

#     current_x = badge_position_x
#     for f_b in frame_badges:
#       # Determine opacity of badge
#       # As the animation continues the opacity decreases
#       # based on the percentage of the animation length to 255 (70 total frames)
#       opacity_value = round((100 - (n / 70 * 100)) * 2.55)
#       badge_with_opacity = f_b.copy()
#       badge_with_opacity.putalpha(opacity_value)
#       f_b.paste(badge_with_opacity, f_b)

#       # Layer effect over badge image
#       badge_with_effect = Image.new("RGBA", (125, 125), (255, 255, 255, 0))
#       badge_with_effect.paste(f_b, (0, 0), f_b)
#       effect_frame = await threaded_image_open(f"./images/templates/scrap/effect/{'{:02d}'.format(n)}.png").resize((125, 125))
#       badge_with_effect.paste(effect_frame, (0, 0), effect_frame)

#       # Stick badge onto replicator background
#       frame.paste(badge_with_effect, (current_x, badge_position_y), badge_with_effect)

#       current_x = current_x + 130

#     frames.append(frame)

#   # Add 10 frames of the replicator by itself
#   for n in range(1, 11):
#     frame = base_image.copy()
#     frames.append(frame)

#   return frames



# @to_thread
# def generate_badge_scrapper_confirmation_gif(user_id, badges_to_scrap):
#   return _generate_badge_scrapper_confirmation_gif(user_id, badges_to_scrap)

# # --- Fix for invalid await inside @to_thread ---
# def _generate_badge_scrapper_confirmation_gif(user_id, badges_to_scrap):
#   frames = generate_badge_scrapper_confirmation_frames(badges_to_scrap)

#   gif_save_filepath = f"./images/scrap/{user_id}-confirm.gif"
#   frames[0].save(
#     gif_save_filepath,
#     save_all=True, append_images=frames[1:], optimize=False, duration=40, loop=0
#   )

#   while True:
#     time.sleep(0.05)
#     if os.path.isfile(gif_save_filepath):
#       break

#   return discord.File(gif_save_filepath, filename=f"scrap_{user_id}-confirm.gif")


# @to_thread
# def generate_badge_scrapper_result_gif(user_id, badge_to_add, badges_to_scrap):
#   return _generate_badge_scrapper_result_gif(user_id, badge_to_add, badges_to_scrap)

# def _generate_badge_scrapper_result_gif(user_id, badge_to_add, badges_to_scrap):
#   badge_created_filename = badge_to_add['badge_filename']
#   replicator_image = Image.open(f"./images/templates/scrap/replicator.png")

#   base_image = Image.new("RGBA", (replicator_image.width, replicator_image.height), (0, 0, 0))
#   base_image.paste(replicator_image, (0, 0))

#   frames = generate_badge_scrapper_confirmation_frames(badges_to_scrap)

#   b = Image.open(f"./images/badges/{badge_created_filename}").convert("RGBA")
#   b = b.resize((190, 190))

#   badge_position_x = 180
#   badge_position_y = 75

#   # Add 10 frames of just the replicator by itself
#   for n in range(1, 11):
#     frame = base_image.copy()
#     frames.append(frame)

#   # Create the badge transporter effect animation
#   for n in range(1, 71):
#     frame = base_image.copy()
#     frame_badge = b.copy()

#     opacity_value = round((n / 70 * 100) * 2.55)
#     badge_with_opacity = b.copy()
#     badge_with_opacity.putalpha(opacity_value)
#     frame_badge.paste(badge_with_opacity, frame_badge)

#     badge_with_effect = Image.new("RGBA", (190, 190), (255, 255, 255, 0))
#     badge_with_effect.paste(frame_badge, (0, 0), frame_badge)
#     effect_frame = Image.open(f"./images/templates/scrap/effect/{'{:02d}'.format(n)}.png").convert('RGBA')
#     badge_with_effect.paste(effect_frame, (0, 0), effect_frame)

#     frame.paste(badge_with_effect, (badge_position_x, badge_position_y), badge_with_effect)
#     frames.append(frame)

#   for n in range(1, 31):
#     frame = base_image.copy()
#     frame.paste(b, (badge_position_x, badge_position_y), b)
#     frames.append(frame)

#   gif_save_filepath = f"./images/scrap/{user_id}.gif"
#   frames[0].save(
#     gif_save_filepath,
#     save_all=True, append_images=frames[1:], optimize=False, duration=40, loop=0
#   )

#   while True:
#     time.sleep(0.10)
#     if os.path.isfile(gif_save_filepath):
#       break

#   return discord.File(gif_save_filepath, filename=f"scrap_{user_id}.gif")


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

async def db_get_user_badge_page_color_preference(user_id, type="collection"):
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
