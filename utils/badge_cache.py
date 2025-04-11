from PIL import Image
from utils.thread_utils import threaded_image_open
from typing import Dict

BADGE_THUMBNAIL_SIZE = 190
SHRINK_PERCENT = 0.9

_base_badge_cache: Dict[str, Image.Image] = {}

async def get_cached_base_badge_canvas(badge_filename: str) -> Image.Image:
  if badge_filename in _base_badge_cache:
    return _base_badge_cache[badge_filename]

  badge_path = f'./images/badges/{badge_filename}'
  badge_img = await threaded_image_open(badge_path)

  shrink_size = int(BADGE_THUMBNAIL_SIZE * SHRINK_PERCENT)
  badge_img = badge_img.resize((shrink_size, shrink_size), Image.LANCZOS)

  canvas = Image.new('RGBA', (BADGE_THUMBNAIL_SIZE, BADGE_THUMBNAIL_SIZE), (0, 0, 0, 0))
  offset = ((BADGE_THUMBNAIL_SIZE - shrink_size) // 2, (BADGE_THUMBNAIL_SIZE - shrink_size) // 2)
  canvas.paste(badge_img, offset, badge_img)

  _base_badge_cache[badge_filename] = canvas
  return canvas