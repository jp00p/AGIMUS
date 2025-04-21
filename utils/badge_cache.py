import numpy as np
from pathlib import Path

from common import *

from utils.thread_utils import threaded_image_open, to_thread
from typing import Dict


BADGE_THUMBNAIL_SIZE = 190

_base_badge_cache: Dict[str, Image.Image] = {}

async def get_cached_base_badge_canvas(badge_filename: str) -> Image.Image:
  if badge_filename in _base_badge_cache:
    return _base_badge_cache[badge_filename]

  badge_path = f'./images/badges/{badge_filename}'
  badge_img = await threaded_image_open(badge_path)

  # Apply autoshrink logic based on actual visible margin
  badge_img = autoshrink_badge(badge_img, canvas_size=(BADGE_THUMBNAIL_SIZE, BADGE_THUMBNAIL_SIZE))

  # Paste onto 190x190 canvas (centered)
  canvas = Image.new('RGBA', (BADGE_THUMBNAIL_SIZE, BADGE_THUMBNAIL_SIZE), (0, 0, 0, 0))
  offset = ((BADGE_THUMBNAIL_SIZE - badge_img.width) // 2, (BADGE_THUMBNAIL_SIZE - badge_img.height) // 2)
  canvas.paste(badge_img, offset, badge_img)

  _base_badge_cache[badge_filename] = canvas
  return canvas

def autoshrink_badge(badge_img: Image.Image, canvas_size=(200, 200), margin_ratio=0.15) -> Image.Image:
  """
  Proportionally resizes a badge to fit within 190x190, then shrinks it further if
  opaque pixels are too close to the edge. Ensures safe visual margins in a 200x200 frame.

  Parameters:
    badge_img (Image): The RGBA badge image to process.
    canvas_size (tuple): Final canvas size (default 200x200).
    margin_ratio (float): Margin safety threshold as % of canvas size.

  Returns:
    Image: The resized badge image, safely framed.
  """
  base_size = 190
  badge_img = badge_img.copy()
  badge_img.thumbnail((base_size, base_size), Image.LANCZOS)

  width, height = badge_img.size
  margin = int(canvas_size[0] * margin_ratio)

  alpha = badge_img.getchannel("A")
  alpha_np = np.array(alpha)
  rows = np.any(alpha_np > 10, axis=1)
  cols = np.any(alpha_np > 10, axis=0)
  top, bottom = np.argmax(rows), len(rows) - np.argmax(rows[::-1]) - 1
  left, right = np.argmax(cols), len(cols) - np.argmax(cols[::-1]) - 1

  too_close = top < margin or bottom > height - margin or left < margin or right > width - margin
  if too_close:
    inset = min(top, height - bottom, left, width - right)
    shrink_factor = 1.0 - ((margin - inset) / margin) * 0.4
    shrink_factor = min(max(shrink_factor, 0.75), 1.0)
    new_dim = int(min(width, height) * shrink_factor)
    return badge_img.resize((new_dim, new_dim), resample=Image.LANCZOS)

  return badge_img

