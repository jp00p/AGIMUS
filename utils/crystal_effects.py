import asyncio
import shutil
import numpy as np
import imageio.v3 as iio

from common import *

from pathlib import Path
from scipy.ndimage import map_coordinates, binary_dilation, gaussian_filter

from utils.thread_utils import threaded_image_open, threaded_image_open_no_convert

FRAME_SIZE = (190, 190)
TOTAL_FRAMES = 24
ANIMATION_FPS = 12
ANIMATION_DURATION = 2.0


# Helpers
def get_badge_bounds(mask: Image.Image) -> tuple[int, int, int, int]:
  """
  Returns bounding box of non-transparent pixels in the alpha mask.
  """
  bbox = mask.getbbox()
  if bbox:
    return bbox
  return 0, 0, mask.width, mask.height

# --- Thread-safe loader wrappers ---
@to_thread
def load_cached_effect_image(cached_path):
  """
  Loads a cached crystal effect image (static or animated) from disk.

  If animated (APNG), returns a list of RGBA frames.
  If static (PNG), returns a single RGBA image.
  """
  img = Image.open(cached_path)
  if getattr(img, "is_animated", False):
    frames = [frame.copy().convert("RGBA") for frame in ImageSequence.Iterator(img)]
    return frames
  return img.convert("RGBA")

@to_thread
def load_overlay_image(path):
  """
  Loads an overlay image in greyscale (L mode).
  """
  return Image.open(path).convert('L')

@to_thread
def load_background_image_resized(path, size):
  """
  Loads and resizes a background image to the specified size in RGBA mode.
  """
  return Image.open(path).convert("RGBA").resize(size)

# Rarity Tier Design Philosophy:
#
# -- Common     – Simple color tints
# -- Uncommon   – Silhouette Effects
# -- Rare       – Backgrounds with Border Gradient
# -- Legendary  – Animated effects (Warping, Pulsing, Etc)
# -- Mythic     – Animated + Prestige visual effects
# -- Unobtanium - Animated + Highly Coverted Designs
#
async def apply_crystal_effect(badge_image: Image.Image, badge: dict, crystal=None) -> Image.Image | list[Image.Image]:
  """
  Applies the visual crystal effect to a badge image based on the attached crystal.

  - If no crystal is attached (`crystal_id` missing), returns the original image unchanged.
  - If a crystal effect is specified, attempts to load a cached result (PNG or APNG).
  - If no cached result is found, dynamically generates the effect using the registered handler function.
    The generated result is then cached for future use.
  - Supports both static (single image) and animated (list of frames) effects.

  Args:
    badge_image (PIL.Image.Image): The base badge image in RGBA format.
    badge (dict): Dictionary containing at minimum:
      - 'badge_info_id' (int): ID used for effect cache filenames.
      - 'crystal_id' (int, optional): Present if a crystal is attached.
      - 'effect' (str, optional): Key used to look up the registered effect handler.

  Returns:
    PIL.Image.Image or list[PIL.Image.Image]: Either a static RGBA image or a sequence of RGBA frames for animation.
  """

  effect_key = None
  if crystal:
    effect_key = crystal.get("effect")
  elif badge:
    effect_key = badge.get("crystal_effect", None)

  if not effect_key:
    return badge_image

  cached_path_png = get_cached_effect_path(effect_key, badge['badge_info_id'], extension="png")
  cached_path_apng = get_cached_effect_path(effect_key, badge['badge_info_id'], extension="apng")

  if cached_path_png.exists():
    logger.info(f"Loading cached static effect (.png) for {effect_key} (Badge ID {badge['badge_info_id']})")
    return await load_cached_effect_image(cached_path_png)

  if cached_path_apng.exists():
    logger.info(f"Loading cached animated effect (.apng) for {effect_key} (Badge ID {badge['badge_info_id']})")
    return await load_cached_effect_image(cached_path_apng)

  # If neither cache exists, generate it
  logger.info(f"Cached effect not found for {effect_key} (Badge ID {badge['badge_info_id']}) — generating...")

  fn = _EFFECT_ROUTER.get(effect_key)
  if not fn:
    logger.warning(f"No effect registered for {effect_key}. Returning base badge image.")
    return badge_image

  # Generate effect (may be single image or list of frames)
  result = await asyncio.to_thread(fn, badge_image, badge)

  # Determine correct extension based on generated result
  extension = "apng" if isinstance(result, list) else "png"
  cached_path = get_cached_effect_path(effect_key, badge['badge_info_id'], extension=extension)

  # Save to disk
  await save_cached_effect_image(result, effect_key, badge['badge_info_id'])

  # Load freshly saved result
  return await load_cached_effect_image(cached_path)



# --- Internal Effect Registry ---
_EFFECT_ROUTER = {}

def register_effect(name):
  def decorator(fn):
    _EFFECT_ROUTER[name] = fn
    return fn
  return decorator

# --- Image Cache --
# These effects, and specifically the animated effects, are expensive so
# Let's save em to disk for retrieval on-demand
CACHE_DIR = ".cache/crystal_effects"
REPLICATOR_CACHE_DIR = ".cache/crystal_replicator_animations"

def get_cached_effect_path(effect: str, badge_info_id: int, extension: str = "png") -> Path:
  """
  Constructs the full file path for a crystal effect cache entry.

  Example: .cache/crystal_effects/shimmer_flux__123.apng
  """
  safe_effect = effect.replace("/", "_")
  return Path(f".cache/crystal_effects/{safe_effect}_{badge_info_id}.{extension}")

@to_thread
def save_cached_effect_image(image: Image.Image | list[Image.Image], effect: str, badge_info_id: int):
  """
  Saves a crystal effect result to the cache.

  If `image` is a list, saves as an APNG using imageio.
  Otherwise, saves as a static PNG using Pillow.
  """
  if isinstance(image, list):
    path = get_cached_effect_path(effect, badge_info_id, extension="apng")
    path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure uniform RGBA frames
    converted = [np.array(f.convert("RGBA")) for f in image]

    # Save with correct format string
    iio.imwrite(
      path,
      converted,
      plugin="pillow",
      format="PNG",  # <== This is correct
      duration=int(1000 / 12),
      loop=0
    )

  else:
    # Static PNG fallback
    path = get_cached_effect_path(effect, badge_info_id, extension="png")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG")


def delete_crystal_effects_cache():
  """
  Deletes all cached crystal effect images.
  """
  cache_directory = Path(CACHE_DIR)
  if cache_directory.exists():
    shutil.rmtree(cache_directory)

def delete_replicator_animations_cache():
  """
  Deletes all cached replicator animations.
  """
  cache_directory = Path(REPLICATOR_CACHE_DIR)
  if cache_directory.exists():
    shutil.rmtree(cache_directory)


#  .d8888b.
# d88P  Y88b
# 888    888
# 888         .d88b.  88888b.d88b.  88888b.d88b.   .d88b.  88888b.
# 888        d88""88b 888 "888 "88b 888 "888 "88b d88""88b 888 "88b
# 888    888 888  888 888  888  888 888  888  888 888  888 888  888
# Y88b  d88P Y88..88P 888  888  888 888  888  888 Y88..88P 888  888
#  "Y8888P"   "Y88P"  888  888  888 888  888  888  "Y88P"  888  888

# Tints
@register_effect("pink_tint")
def effect_pink_tint(img: Image.Image, badge: dict) -> Image.Image:
  return _apply_tint(img, (255, 105, 180))  # Hot pink

@register_effect("blue_tint")
def effect_blue_tint(img: Image.Image, badge: dict) -> Image.Image:
  return _apply_tint(img, (102, 204, 255))  # Soft blue

@register_effect("steel_tint")
def effect_steel_tint(img: Image.Image, badge: dict) -> Image.Image:
  return _apply_tint(img, (170, 170, 170), 0.75)  # Metallic gray

@register_effect("orange_tint")
def effect_orange_tint(img: Image.Image, badge: dict) -> Image.Image:
  return _apply_tint(img, (255, 165, 90))  # Warm orange

@register_effect("purple_tint")
def effect_purple_tint(img: Image.Image, badge: dict) -> Image.Image:
  return _apply_tint(img, (180, 110, 230))  # Soft violet

@register_effect("greenmint_tint")
def effect_greenmint_tint(img: Image.Image, badge: dict) -> Image.Image:
  return _apply_tint(img, (100, 220, 180))  # Minty green

# Gradients
@register_effect("crimson_gradient")
def effect_crimson_gradient(img: Image.Image, badge: dict) -> Image.Image:
  return _apply_gradient(img, (255, 60, 60))  # Bold crimson

@register_effect("lime_gradient")
def effect_lime_gradient(img: Image.Image, badge: dict) -> Image.Image:
  return _apply_gradient(img, (140, 255, 80))  # Vivid lime

@register_effect("navy_gradient")
def effect_navy_gradient(img: Image.Image, badge: dict) -> Image.Image:
  return _apply_gradient(img, (80, 120, 255))  # Cool blue

@register_effect("gold_gradient")
def effect_yellow_gradient(img: Image.Image, badge: dict) -> Image.Image:
  return _apply_gradient(img, (245, 215, 60))  # Golden yellow

@register_effect("silver_gradient")
def effect_silver_gradient(img: Image.Image, badge: dict) -> Image.Image:
  return _apply_gradient(img, (200, 200, 200))  # Silvery

@register_effect("cyan_gradient")
def effect_cyan_gradient(img: Image.Image, badge: dict) -> Image.Image:
  return _apply_gradient(img, (90, 230, 255))  # Cyan-turquoise

@register_effect("amber_gradient")
def effect_amber_gradient(img: Image.Image, badge: dict) -> Image.Image:
  return _apply_gradient(img, (255, 140, 60))  # Amber-orange


def _apply_tint(base_img: Image.Image, color: tuple[int, int, int], opacity: float = 0.40, glow_radius: int = 6) -> Image.Image:
  if base_img.mode != 'RGBA':
    base_img = base_img.convert('RGBA')

  # Split channels
  r, g, b, a = base_img.split()
  base_rgb = Image.merge('RGB', (r, g, b))

  # Create a tint layer and blend it with the base RGB
  tint_rgb = Image.new('RGB', base_img.size, color)
  blended_rgb = Image.blend(base_rgb, tint_rgb, opacity)

  # Create mask from alpha (where pixel is visible)
  mask = a.point(lambda p: 255 if p > 0 else 0).convert('L')
  result_rgb = Image.composite(blended_rgb, base_rgb, mask)

  # Create glow mask by blurring the alpha channel
  glow_mask = a.filter(ImageFilter.GaussianBlur(radius=glow_radius))

  # Glow layer using the tint color with softened alpha
  glow_layer = Image.new('RGBA', base_img.size, color + (0,))
  glow_pixels = glow_layer.load()
  mask_pixels = glow_mask.load()
  for y in range(base_img.height):
    for x in range(base_img.width):
      glow_pixels[x, y] = color + (mask_pixels[x, y],)

  # Composite the glow behind the tinted image
  result_img = Image.alpha_composite(glow_layer, Image.merge('RGBA', (*result_rgb.split(), a)))

  return result_img


def _apply_gradient(img: Image.Image, color: tuple[int, int, int], hold_ratio: float = 0.60) -> Image.Image:
  """
  Applies a vertical color gradient to the badge pixels with a softened fade.

  Parameters:
    img (Image): RGBA badge image
    color (tuple): (R, G, B) tint color
    hold_ratio (float): Ratio of visible height to hold full intensity before fade

  Returns:
    Image: Badge image with gradient overlay
  """
  img = img.convert("RGBA")
  alpha = img.getchannel("A")
  alpha_np = np.array(alpha)

  rows = np.any(alpha_np > 10, axis=1)
  top, bottom = np.argmax(rows), len(rows) - np.argmax(rows[::-1]) - 1
  height = bottom - top + 1
  hold_until = int(top + hold_ratio * height)

  def ease_out_sine_soft(x):
    return math.sin(x * math.pi / 2) ** 2  # smoother tail

  gradient = Image.new("RGBA", img.size, (0, 0, 0, 0))
  draw = ImageDraw.Draw(gradient)

  for y in range(top, bottom + 1):
    if y <= hold_until:
      factor = 1.0
    else:
      fade_ratio = (y - hold_until) / max((bottom - hold_until), 1)
      factor = 1.0 - ease_out_sine_soft(fade_ratio)
    r, g, b = [int(c * factor) for c in color]
    draw.line([(0, y), (img.width, y)], fill=(r, g, b, int(180 * factor)))

  gradient_masked = Image.composite(gradient, Image.new("RGBA", img.size, (0, 0, 0, 0)), alpha)
  result_image = Image.alpha_composite(img, gradient_masked)

  return result_image


# Special Tints
@register_effect("latinum")
def effect_latinum(badge_image: Image.Image, badge: dict) -> Image.Image:
  """
  Golden latinum overlay.
  Applies tint, shimmer, and glow strictly to badge pixels.
  """
  if badge_image.mode != 'RGBA':
    badge_image = badge_image.convert('RGBA')

  width, height = badge_image.size
  badge_mask = badge_image.split()[3].point(lambda p: 255 if p > 0 else 0).convert('L')

  # Base tint layer
  tint_color = (255, 230, 150)
  tint_layer = Image.new('RGBA', badge_image.size, tint_color + (int(255 * 0.35),))
  tint_layer_masked = Image.composite(tint_layer, Image.new('RGBA', badge_image.size, (0, 0, 0, 0)), badge_mask)
  badge_tinted = Image.alpha_composite(badge_image, tint_layer_masked)

  # Shimmer gradient
  center_gold = (255, 230, 150)
  edge_gold = (140, 115, 70)
  band_width_ratio = 0.1875

  gradient_img = Image.new('RGBA', badge_image.size)
  draw = ImageDraw.Draw(gradient_img)
  for y in range(height):
    dist = abs((y - height // 2) / (height / 2)) / band_width_ratio
    dist = min(dist, 1.0)
    r = int(center_gold[0] * (1 - dist) + edge_gold[0] * dist)
    g = int(center_gold[1] * (1 - dist) + edge_gold[1] * dist)
    b = int(center_gold[2] * (1 - dist) + edge_gold[2] * dist)
    draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

  r, g, b, a = gradient_img.split()
  a = a.point(lambda p: int(p * 0.4))
  shimmer_masked = Image.merge('RGBA', (r, g, b, a))
  shimmer_masked = Image.composite(shimmer_masked, Image.new('RGBA', badge_image.size, (0, 0, 0, 0)), badge_mask)

  # Glow layer
  glow = shimmer_masked.filter(ImageFilter.GaussianBlur(radius=8))
  glow = ImageEnhance.Brightness(glow).enhance(1.92)  # brightness reduced ~20%
  glow = Image.composite(glow, Image.new('RGBA', badge_image.size, (0, 0, 0, 0)), badge_mask)

  base_with_glow = Image.alpha_composite(glow, badge_tinted)
  final = Image.alpha_composite(base_with_glow, shimmer_masked)

  return final


# 888     888
# 888     888
# 888     888
# 888     888 88888b.   .d8888b .d88b.  88888b.d88b.  88888b.d88b.   .d88b.  88888b.
# 888     888 888 "88b d88P"   d88""88b 888 "888 "88b 888 "888 "88b d88""88b 888 "88b
# 888     888 888  888 888     888  888 888  888  888 888  888  888 888  888 888  888
# Y88b. .d88P 888  888 Y88b.   Y88..88P 888  888  888 888  888  888 Y88..88P 888  888
#  "Y88888P"  888  888  "Y8888P "Y88P"  888  888  888 888  888  888  "Y88P"  888  888
@register_effect("optical")
def effect_isolinear(img, badge):
  return _apply_gradient_silhouette_border(img, (0, 200, 255), (140, 255, 0))

@register_effect("cryonetrium")
def effect_cryonetrium(img: Image.Image, badge: dict) -> Image.Image:
  return _apply_gradient_silhouette_border(img, (180, 240, 255), (10, 60, 140))

@register_effect("verterium_cortenide")
def effect_verterium_cortenide(img: Image.Image, badge: dict) -> Image.Image:
  return _apply_gradient_silhouette_border(img, (80, 200, 255), (90, 60, 180))

@register_effect('boridium')
def effect_boridium(img, badge):
  return _apply_energy_rings_silhouette_wrap(img, primary_color=(200, 80, 255), secondary_color=(80, 255, 255))

@register_effect("invidium")
def effect_invidium(badge_image: Image.Image, badge: dict) -> Image.Image:
  if badge_image.mode != 'RGBA':
    badge_image = badge_image.convert('RGBA')

  # Split channels
  r, g, b, a = badge_image.split()

  # Invert RGB only
  r_inv = ImageOps.invert(r)
  g_inv = ImageOps.invert(g)
  b_inv = ImageOps.invert(b)

  # Merge with original alpha
  return Image.merge('RGBA', (r_inv, g_inv, b_inv, a))

@register_effect("remalite")
def effect_remalite(img: Image.Image, badge: dict) -> Image.Image:
  return _apply_gradient_silhouette_border(img, (160, 200, 255), (140, 120, 210))

@register_effect("vokaya")
def effect_vokaya(img: Image.Image, badge: dict) -> Image.Image:
  return _apply_energy_rings_silhouette_wrap(img, primary_color=(100, 240, 200), secondary_color=(200, 255, 200))

@register_effect("kironide")
def effect_kironide(img: Image.Image, badge: dict) -> Image.Image:
  return _apply_energy_rings_silhouette_wrap(img, primary_color=(255, 230, 120), secondary_color=(140, 100, 255))

@register_effect("jevonite")
def effect_jevonite(img: Image.Image, badge: dict) -> Image.Image:
  return _apply_gradient_silhouette_border(img, (200, 40, 40), (255, 190, 80))

@register_effect("archerite")
def effect_archerite(img: Image.Image, badge: dict) -> Image.Image:
  return _apply_gradient_silhouette_border(img, (180, 255, 140), (60, 60, 60))


def _apply_gradient_silhouette_border(
  badge_image: Image.Image,
  gradient_start: tuple[int, int, int],
  gradient_end: tuple[int, int, int],
  pad: int = 10,
  max_filter_size: int = 15,
  blur_radius: int = 6
) -> Image.Image:
  """
  Applies a glowing gradient-colored silhouette border around the badge shape.

  Args:
    badge_image: RGBA badge image.
    gradient_start: RGB tuple for the starting color of the gradient.
    gradient_end: RGB tuple for the ending color of the gradient.
    pad: Padding around the badge.
    max_filter_size: Dilation size for border thickness.
    blur_radius: Gaussian blur radius for glow.

  Returns:
    RGBA image with border applied.
  """
  width, height = badge_image.size
  alpha = badge_image.split()[-1]

  # Prepare expanded canvas
  expanded_size = (width + 2 * pad, height + 2 * pad)
  expanded_image = Image.new('RGBA', expanded_size, (0, 0, 0, 0))
  expanded_alpha = Image.new('L', expanded_size, 0)
  expanded_image.paste(badge_image, (pad, pad))
  expanded_alpha.paste(alpha, (pad, pad))

  # Generate silhouette outline mask
  outer = expanded_alpha.filter(ImageFilter.MaxFilter(max_filter_size))
  outline_mask = ImageChops.subtract(outer, expanded_alpha)

  # Create gradient border
  gradient = Image.new('RGBA', expanded_size, (0, 0, 0, 0))
  for y in range(expanded_size[1]):
    for x in range(expanded_size[0]):
      t = (x + y) / (expanded_size[0] + expanded_size[1])
      r = int((1 - t) * gradient_start[0] + t * gradient_end[0])
      g = int((1 - t) * gradient_start[1] + t * gradient_end[1])
      b = int((1 - t) * gradient_start[2] + t * gradient_end[2])
      gradient.putpixel((x, y), (r, g, b, 255))

  border_colored = Image.new('RGBA', expanded_size, (0, 0, 0, 0))
  border_colored.paste(gradient, mask=outline_mask)

  # Composite with glow
  glow = border_colored.filter(ImageFilter.GaussianBlur(radius=blur_radius))
  composed = Image.alpha_composite(Image.new('RGBA', expanded_size), glow)
  composed = Image.alpha_composite(composed, border_colored)
  composed = Image.alpha_composite(composed, expanded_image)

  return composed


def _apply_energy_rings_silhouette_wrap(badge_img: Image.Image, primary_color: tuple[int, int, int], secondary_color: tuple[int, int, int], padding: int = 4) -> Image.Image:
  """
  Wraps a badge image with two procedural elliptical energy rings, layered front/back.

  Args:
    badge_img: The RGBA badge image to wrap.
    color1: RGB color tuple for the primary ring.
    color2: RGB color tuple for the secondary ring.
    padding: Padding around the badge to leave room for ring spacing.

  Returns:
    A new RGBA image with the wrapped badge.
  """
  base_w, base_h = badge_img.size
  ring_canvas = Image.new("RGBA", (base_w, base_h), (0, 0, 0, 0))

  # Slightly smaller ring bounds to stay within frame
  ring_box = (
    padding, padding,
    base_w - padding,
    base_h - padding
  )
  ring_size = (ring_box[2] - ring_box[0], ring_box[3] - ring_box[1])

  primary_ring = _generate_energy_ring_wrap(ring_size, color=primary_color, rx_scale=0.35, ry_scale=0.15)
  secondary_ring = _generate_energy_ring_wrap(ring_size, color=secondary_color, rx_scale=0.32, ry_scale=0.13)
  combined_ring = Image.alpha_composite(primary_ring, secondary_ring)

  # Composite rings into full-size frame
  ring_canvas.paste(combined_ring, ring_box[:2], combined_ring)

  # Split rings into front and back halves
  front_mask = Image.new("L", (base_w, base_h), 0)
  ImageDraw.Draw(front_mask).rectangle(
    [0, base_h // 2, base_w, base_h],
    fill=255
  )
  front_mask = front_mask.filter(ImageFilter.GaussianBlur(8))
  back_mask = ImageChops.invert(front_mask)

  front = Image.composite(ring_canvas, Image.new("RGBA", (base_w, base_h), (0, 0, 0, 0)), front_mask)
  back = Image.composite(ring_canvas, Image.new("RGBA", (base_w, base_h), (0, 0, 0, 0)), back_mask)

  # Final composite
  out = Image.new("RGBA", (base_w, base_h), (0, 0, 0, 0))
  out = Image.alpha_composite(out, back)
  out = Image.alpha_composite(out, badge_img)
  out = Image.alpha_composite(out, front)

  return out

def _generate_energy_ring_wrap(
  size=(512, 512),
  color=(200, 80, 255),
  stroke_width=2,
  num_loops=18,
  rx_scale=0.35,
  ry_scale=0.15,
  blur_radius=1.5
) -> Image.Image:
  """
  Generates a dense elliptical energy ring with customizable dimensions and color.
  """
  width, height = size
  ring = Image.new("RGBA", size, (0, 0, 0, 0))
  draw = ImageDraw.Draw(ring)
  cx, cy = width // 2, height // 2
  rx, ry = int(width * rx_scale), int(height * ry_scale)

  for _ in range(num_loops):
    angle_offset = np.random.uniform(0, 2 * np.pi)
    phase = np.random.uniform(0, 2 * np.pi)
    for t in np.linspace(0, 2 * np.pi, 500):
      angle = t + angle_offset
      x = int(cx + rx * np.cos(angle + 0.5 * np.sin(phase + angle)))
      y = int(cy + ry * np.sin(angle))
      intensity = int(255 * (0.5 + 0.5 * np.sin(3 * angle + phase)))
      draw.ellipse(
        [(x - stroke_width, y - stroke_width), (x + stroke_width, y + stroke_width)],
        fill=(color[0], color[1], color[2], intensity),
      )

  return ring.filter(ImageFilter.GaussianBlur(radius=blur_radius))


# 8888888b.
# 888   Y88b
# 888    888
# 888   d88P  8888b.  888d888 .d88b.
# 8888888P"      "88b 888P"  d8P  Y8b
# 888 T88b   .d888888 888    88888888
# 888  T88b  888  888 888    Y8b.
# 888   T88b "Y888888 888     "Y8888
RARE_BACKGROUNDS_DIR = 'images/crystal_effects/backgrounds'

def apply_rare_background_and_border(
  badge_image: Image.Image,
  background_path: str,
  border_gradient_top_left: tuple[int, int, int] = (0, 0, 0),
  border_gradient_bottom_right: tuple[int, int, int] = (0, 0, 0),
  border_width: int = 2,
  border_radius: int = 24,
  shadow_offset: tuple[int, int] = (4, 4),
  shadow_blur: int = 3,
  shadow_color: tuple[int, int, int, int] = (0, 0, 0, 180)
) -> Image.Image:
  """
  Applies a rare-tier crystal effect over the background with a drop-shadow, and adds a diagonal gradient border.

  Args:
    badge_image: The badge RGBA image.
    background_path: Path to the background image file.
    border_gradient_top_left: RGB tuple for the top-left corner color.
    border_gradient_bottom_right: RGB tuple for the bottom-right color.
    border_width: Thickness of the border.
    border_radius: Corner rounding radius.
    shadow_offset: How far away from the badge to apply the shadow
    shadow_blur: How strong to blur the shadow
    shadow_color: Different shadow color if desired

  Returns:
    Image.Image with the full visual effect applied.
  """
  badge_size = badge_image.size

  # Load and mask background
  background = Image.open(background_path).convert("RGBA").resize(badge_size)
  outer_mask = Image.new("L", badge_size, 0)
  draw_outer = ImageDraw.Draw(outer_mask)
  draw_outer.rounded_rectangle(
    [border_width // 2, border_width // 2, badge_size[0] - border_width // 2, badge_size[1] - border_width // 2],
    radius=border_radius,
    fill=255
  )
  background_cropped = Image.composite(background, Image.new("RGBA", badge_size), outer_mask)

  # Drop Shadow
  shadow = Image.new("RGBA", badge_size, (0, 0, 0, 0))
  alpha_mask = badge_image.split()[-1]
  shadow.paste(shadow_color, shadow_offset, mask=alpha_mask)
  shadow_blurred = shadow.filter(ImageFilter.GaussianBlur(radius=shadow_blur))

  # Composite background + shadow + badge
  base = Image.alpha_composite(background_cropped, shadow_blurred)
  composite = Image.alpha_composite(base, badge_image)

  # Border Gradient
  border_gradient = Image.new("RGBA", badge_size)
  for y in range(badge_size[1]):
    for x in range(badge_size[0]):
      t = (x + y) / (badge_size[0] + badge_size[1])
      r = int(border_gradient_top_left[0] * (1 - t) + border_gradient_bottom_right[0] * t)
      g = int(border_gradient_top_left[1] * (1 - t) + border_gradient_bottom_right[1] * t)
      b = int(border_gradient_top_left[2] * (1 - t) + border_gradient_bottom_right[2] * t)
      border_gradient.putpixel((x, y), (r, g, b, 255))

  inner_mask = Image.new("L", badge_size, 0)
  draw_inner = ImageDraw.Draw(inner_mask)
  draw_inner.rounded_rectangle(
    [border_width + 2, border_width + 2, badge_size[0] - border_width - 2, badge_size[1] - border_width - 2],
    radius=border_radius - 4,
    fill=255
  )
  border_mask = ImageChops.subtract(outer_mask, inner_mask)
  gradient_border = Image.composite(border_gradient, Image.new("RGBA", badge_size, (0, 0, 0, 0)), border_mask)

  return Image.alpha_composite(composite, gradient_border)

@register_effect("trilithium_banger")
def effect_trilithium_banger(badge_image: Image.Image, badge: dict) -> Image.Image:
  """
  Purple Space Explosion / Butthole background.
  Used for the Trilithium crystal (Rare tier).
  """
  bg_path = f"{RARE_BACKGROUNDS_DIR}/trilithium_banger.png"
  result = apply_rare_background_and_border(
    badge_image,
    bg_path,
    border_gradient_top_left=(196, 197, 247),
    border_gradient_bottom_right=(50, 51, 101)
  )
  return result

@register_effect("tholian_web")
def effect_tholian_web(badge_image: Image.Image, badge: dict) -> Image.Image:
  """
  Tholian Web in space background effect.
  Used for the Tholian Silk crystal (Rare tier).
  """
  bg_path = f"{RARE_BACKGROUNDS_DIR}/tholian_web.png"
  result = apply_rare_background_and_border(
    badge_image,
    bg_path,
    border_gradient_top_left=(253, 203, 99),
    border_gradient_bottom_right=(107, 59, 17)
  )
  return result

@register_effect("holo_grid")
def effect_holo_grid(badge_image: Image.Image, badge: dict) -> Image.Image:
  """
  Holodeck yellow grid background and gold border.
  Used for the Holomatrix Fragment crystal (Rare tier).
  """
  bg_path = f"{RARE_BACKGROUNDS_DIR}/holo_grid.png"
  result = apply_rare_background_and_border(
    badge_image,
    bg_path,
    border_gradient_top_left=(255, 230, 130),
    border_gradient_bottom_right=(180, 130, 20)
  )
  return result

@register_effect("crystalline_entity")
def effect_crystalline_entity(badge_image: Image.Image, badge: dict) -> Image.Image:
  """
  Crystalline Entity Spikes background.
  Used for the Silicon Shard crystal (Rare tier).
  """
  bg_path = f"{RARE_BACKGROUNDS_DIR}/crystalline_entity.png"
  result = apply_rare_background_and_border(
    badge_image,
    bg_path,
    border_gradient_top_left=(204, 205, 255),
    border_gradient_bottom_right=(49, 49, 99)
  )
  return result

@register_effect("coffee_nebula")
def effect_coffee_nebula(badge_image: Image.Image, badge: dict) -> Image.Image:
  """
  The nebula from "There's Coffee In That Nebula" background.
  Used for the Colombian Coffee Crystal (Rare tier).
  """
  bg_path = f"{RARE_BACKGROUNDS_DIR}/coffee_nebula.png"
  result = apply_rare_background_and_border(
    badge_image,
    bg_path,
    border_gradient_top_left=(157, 122, 134),
    border_gradient_bottom_right=(43, 33, 54)
  )
  return result

@register_effect("positronic_net")
def effect_positronic_net(badge_image: Image.Image, badge: dict) -> Image.Image:
  """
  Positronic Brain display from Star Trek: Picard background.
  Used for the Positron Crystal (Rare tier).
  """
  bg_path = f"{RARE_BACKGROUNDS_DIR}/positronic_net.png"
  result = apply_rare_background_and_border(
    badge_image,
    bg_path,
    border_gradient_top_left=(157, 122, 134),
    border_gradient_bottom_right=(43, 33, 54)
  )
  return result

@register_effect("isolinear_circuit")
def effect_isolinear_circuit(badge_image: Image.Image, badge: dict) -> Image.Image:
  """
  Basic black-green Isolinear Circuitry background.
  Used for the Isolinear Circuit crystal (Rare tier).
  """
  bg_path = f"{RARE_BACKGROUNDS_DIR}/isolinear_circuit.png"
  result = apply_rare_background_and_border(
    badge_image,
    bg_path,
    border_gradient_top_left=(140, 255, 0),
    border_gradient_bottom_right=(10, 50, 10)
  )
  return result


@register_effect("q_grid")
def effect_q_grid(badge_image: Image.Image, badge: dict) -> Image.Image:
  """
  Q Grid from Encounter at Farpoint background.
  Used for the Farpoint Fragment crystal (Rare tier).
  """
  bg_path = f"{RARE_BACKGROUNDS_DIR}/q_grid.png"
  result = apply_rare_background_and_border(
    badge_image,
    bg_path,
    border_gradient_top_left=(196, 197, 247),
    border_gradient_bottom_right=(50, 51, 101)
  )
  return result


@register_effect("alabama_rocks")
def effect_alabama_rocks(badge_image: Image.Image, badge: dict) -> Image.Image:
  """
  Q Grid from Encounter at Farpoint background.
  Used for the Farpoint Fragment crystal (Rare tier).
  """
  bg_path = f"{RARE_BACKGROUNDS_DIR}/alabama_rocks.png"
  result = apply_rare_background_and_border(
    badge_image,
    bg_path,
    border_gradient_top_left=(169, 165, 160),
    border_gradient_bottom_right=(227, 193, 163)
  )
  return result


@register_effect("transparency_starfield")
def effect_transparent_aluminum(badge_image: Image.Image, badge: dict) -> Image.Image:
  """
  Transparent Aluminum effect with a diagonal shine on transparent background.
  Reduces badge opacity to 70% and overlays a soft diagonal highlight across the badge shape.
  Then just throw it through apply_rare_background_and_border() with a starfield image so you can see the stars through it?
  """
  badge_image = badge_image.convert("RGBA")
  width, height = badge_image.size

  # Convert original image to grayscale to determine transparency mask
  gray = ImageOps.grayscale(badge_image)
  # Dark areas become more transparent, light areas more opaque
  transparency_mask = gray.point(lambda px: int(px * 0.4))  # 0.0–102 alpha

  # Build new image with adjusted alpha based on brightness
  r, g, b = badge_image.split()[:3]
  transparent_badge = Image.merge("RGBA", (r, g, b, transparency_mask))

  # Create a narrow diagonal white shine
  shine_overlay = Image.new("RGBA", (width, height), (255, 255, 255, 0))
  pixels = shine_overlay.load()
  for y in range(height):
    for x in range(width):
      t = (x + y) / (width + height)
      band = max(0.0, 1.0 - abs(t - 0.5) * 12.0)  # Narrow band around the diagonal
      alpha = int(10 * band)  # Max alpha = 10
      pixels[x, y] = (255, 255, 255, alpha)

  # Mask the shine to the badge's original alpha mask (for clean edges)
  alpha_mask = transparency_mask
  masked_shine = Image.new("RGBA", (width, height))
  masked_shine.paste(shine_overlay, (0, 0), mask=alpha_mask)

  # Apply shine over transparent badge
  shiny_translucent_badge = Image.alpha_composite(transparent_badge, masked_shine)

  # Composite over starfield background with border
  bg_path = f"{RARE_BACKGROUNDS_DIR}/transparency_starfield.png"
  result = apply_rare_background_and_border(
    shiny_translucent_badge,
    bg_path,
    border_gradient_top_left=(192, 192, 255),
    border_gradient_bottom_right=(96, 160, 255)
  )

  return result


@register_effect("guardian_of_forever")
def effect_guardian_of_forever(badge_image: Image.Image, badge: dict) -> Image.Image:
  """
  Guardian of the Edge of Forever Background.
  Used for the Aeon Shard crystal (Rare tier).
  """
  bg_path = f"{RARE_BACKGROUNDS_DIR}/guardian_of_forever.png"
  result = apply_rare_background_and_border(
    badge_image,
    bg_path,
    border_gradient_top_left=(118, 222, 191),
    border_gradient_bottom_right=(176, 112, 220)
  )
  return result

#       ...                                                         ..
#   .zf"` `"tu                                                    dF                                    ..
#  x88      '8N.                                      u.    u.   '88bu.                     .u    .    @L
#  888k     d88&      .u         uL          .u     x@88k u@88c. '*88888bu         u      .d88B :@8c  9888i   .dL
#  8888N.  @888F   ud8888.   .ue888Nc..   ud8888.  ^"8888""8888"   ^"*8888N     us888u.  ="8888f8888r `Y888k:*888.
#  `88888 9888%  :888'8888. d88E`"888E` :888'8888.   8888  888R   beWE "888L .@88 "8888"   4888>'88"    888E  888I
#    %888 "88F   d888 '88%" 888E  888E  d888 '88%"   8888  888R   888E  888E 9888  9888    4888> '      888E  888I
#     8"   "*h=~ 8888.+"    888E  888E  8888.+"      8888  888R   888E  888E 9888  9888    4888>        888E  888I
#   z8Weu        8888L      888E  888E  8888L        8888  888R   888E  888F 9888  9888   .d888L .+     888E  888I
#  ""88888i.   Z '8888c. .+ 888& .888E  '8888c. .+  "*88*" 8888" .888N..888  9888  9888   ^"8888*"     x888N><888'
# "   "8888888*   "88888%   *888" 888&   "88888%      ""   'Y"    `"888*""   "888*""888"     "Y"        "88"  888
#       ^"**""      "YP'     `"   "888E    "YP'                      ""       ^Y"   ^Y'                       88F
#                           .dWi   `88E                                                                      98"
#                           4888~  J8%                                                                     ./"
#                            ^"===*"`                                                                     ~`
@register_effect("warp_pulse")
def effect_warp_pulse(base_img: Image.Image, badge: dict) -> list[Image.Image]:
  """
  Emits animated outward-pulsing glow rings from the badge edge.
  Pulses originate from the perimeter and expand outward with a sigmoid fade.
  Uses a fixed 0.95 hard fade cutoff to prevent reaching the frame edges.

  Used for the Warp Plasma crystal (Legendary Tier).

  Returns:
    List of RGBA frames as PIL.Image.Image.
  """
  fps = ANIMATION_FPS
  duration = ANIMATION_DURATION
  num_frames = int(duration * fps)
  num_rings = 3
  ring_interval = num_frames // num_rings

  FRAME_SIZE = (190, 190)
  center = (FRAME_SIZE[0] // 2, FRAME_SIZE[1] // 2)
  max_radius = FRAME_SIZE[0] / 2

  midpoint = 0.65
  fade_cutoff = 0.95
  fade_steepness = 10
  alpha_max = 300  # intentionally >255 to allow brightening
  ring_thickness = 10
  blur_radius = 2
  glow_color = (20, 160, 255)  # bright electric blue

  def clamped_sigmoid(dist_ratio: float) -> float:
    if dist_ratio >= fade_cutoff:
      return 0.0
    return 1 / (1 + np.exp(fade_steepness * (dist_ratio - midpoint)))

  # Prepare base badge image
  badge_img = base_img.resize((180, 180), Image.Resampling.LANCZOS)
  badge_canvas = Image.new("RGBA", FRAME_SIZE, (0, 0, 0, 0))
  offset = ((FRAME_SIZE[0] - 180) // 2, (FRAME_SIZE[1] - 180) // 2)
  badge_canvas.paste(badge_img, offset, badge_img)

  alpha = np.array(badge_canvas.split()[-1]) > 10
  dilated = binary_dilation(alpha, iterations=1)
  edge_mask = np.logical_xor(dilated, alpha)
  edge_points = [(x, y) for y, x in np.argwhere(edge_mask)]

  frames = []
  for frame_index in range(num_frames):
    frame = Image.new("RGBA", FRAME_SIZE, (0, 0, 0, 0))
    glow = Image.new("RGBA", FRAME_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)

    for ring_i in range(num_rings):
      ring_age = (frame_index - ring_i * ring_interval) % num_frames
      ring_progress = ring_age / num_frames
      offset_dist = int(max(FRAME_SIZE) * ring_progress)
      if offset_dist <= 0:
        continue

      for x, y in edge_points:
        dx, dy = x - center[0], y - center[1]
        length = (dx**2 + dy**2) ** 0.5
        if length == 0:
          continue
        nx, ny = dx / length, dy / length
        tx = int(x + nx * offset_dist)
        ty = int(y + ny * offset_dist)

        if not (0 <= tx < FRAME_SIZE[0] and 0 <= ty < FRAME_SIZE[1]):
          continue

        dist_ratio = ((tx - center[0])**2 + (ty - center[1])**2) ** 0.5 / max_radius
        fade = clamped_sigmoid(dist_ratio)
        alpha_val = int(min(alpha_max * fade, 255))
        if alpha_val <= 0:
          continue

        draw.ellipse([
          (tx - ring_thickness // 2, ty - ring_thickness // 2),
          (tx + ring_thickness // 2, ty + ring_thickness // 2),
        ], fill=(*glow_color, alpha_val))

    blurred = glow.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    frame = Image.alpha_composite(frame, blurred)
    frame = Image.alpha_composite(frame, badge_canvas)
    frames.append(frame)

  return frames


@register_effect("subspace_ripple")
def effect_subspace_ripple(base_img: Image.Image, badge: dict) -> list[Image.Image]:
  """
  Applies an animated diagonal wave distortion across the badge.
  Distortion slows down and fades out before restarting for a rhythmic subspace ripple.
  Preserves transparency and avoids ghosting.
  """
  fps = ANIMATION_FPS
  duration = ANIMATION_DURATION
  num_frames = int(duration * fps)
  width, height = FRAME_SIZE

  amplitude = 8
  wavelength = 96

  badge_array = np.array(base_img).astype(np.float32)
  alpha_channel = badge_array[..., 3] / 255.0

  # Premultiply RGB by alpha to avoid black fringes
  for c in range(3):
    badge_array[..., c] *= alpha_channel

  Y, X = np.meshgrid(np.arange(height), np.arange(width), indexing="ij")

  def ripple_amplitude_multiplier(frame_index: int, total: int) -> float:
    t = frame_index / total
    t_scaled = t * 2 * math.pi
    return 0.5 + 0.5 * math.sin(t_scaled)

  frames = []
  for i in range(num_frames):
    amp_mult = ripple_amplitude_multiplier(i, num_frames)
    phase = (i / num_frames) * 2 * np.pi
    offset = amplitude * amp_mult * np.sin((X + Y) / wavelength * 2 * np.pi + phase)
    coords_y = Y + offset
    coords_x = X + offset
    coords = np.array([coords_y.flatten(), coords_x.flatten()])

    channels = [
      map_coordinates(badge_array[..., c], coords, order=1, mode='reflect').reshape((height, width))
      for c in range(4)
    ]
    result = np.stack(channels, axis=-1)

    # Un-premultiply-ifly RGB
    alpha = np.clip(result[..., 3], 1e-6, 255.0)
    for c in range(3):
      result[..., c] = np.clip(result[..., c] / (alpha / 255.0), 0, 255)
    result[..., 3] = np.clip(result[..., 3], 0, 255)

    final = result.astype(np.uint8)
    distorted = Image.fromarray(final, mode="RGBA")

    # Composite onto clean transparent canvas to prevent ghosting
    frame = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    frame.paste(distorted, (0, 0), distorted)
    frames.append(frame)

  return frames


@register_effect("temporal_flicker")
def effect_temporal_flicker(base_img: Image.Image, badge: dict) -> list[Image.Image]:
  """
  Introduces animated glitches such as chromatic aberation, position jitter,
  scanline shifts, scaling flickers, and frame blinks. Emulates unstable
  temporal phasing of the badge.

  Used for the Chroniton crystal (Legendary tier).

  Returns:
    List of RGBA frames as PIL.Image.Image.
  """
  fps = ANIMATION_FPS
  hold_frames, drift_frames, glitch_frames = 8, 8, 8
  drift_amount = 0.5
  scanline_indices = [4, 5, 6, 7]
  blink_scales = [1.0, 0.97, 1.08, 0.93, 1.12, 1.0, 0.95, 1.05]
  center = ((FRAME_SIZE[0] - base_img.width) // 2, (FRAME_SIZE[1] - base_img.height) // 2)
  frames = []

  def apply_linear_drift(img, i, drift):
    dx = int(drift[0] * i)
    dy = int(drift[1] * i)
    r, g, b, a = img.split()
    r = ImageChops.offset(r, 2, 0)
    b = ImageChops.offset(b, -1, 0)
    rgb = Image.merge("RGB", (r, g, b))
    merged = Image.merge("RGBA", (*rgb.split(), a))
    canvas = Image.new("RGBA", FRAME_SIZE, (0, 0, 0, 0))
    canvas.paste(merged, (center[0] + dx, center[1] + dy), merged)
    return canvas

  def apply_jitter(img, i):
    np.random.seed(i + 100)
    jitter_x, jitter_y = np.random.randint(-12, 13, size=2)
    np.random.seed(i)
    jitters = np.random.randint(-6, 7, (3, 2))
    r, g, b, a = img.split()
    r = ImageChops.offset(r, *jitters[0])
    g = ImageChops.offset(g, *jitters[1])
    b = ImageChops.offset(b, *jitters[2])
    rgb = Image.merge("RGB", (r, g, b))
    merged = Image.merge("RGBA", (*rgb.split(), a))
    canvas = Image.new("RGBA", FRAME_SIZE, (0, 0, 0, 0))
    canvas.paste(merged, (center[0] + jitter_x, center[1] + jitter_y), merged)
    return canvas

  def apply_scanline_shift(img, i):
    pixels = np.array(img)
    for y in range(0, pixels.shape[0], 2):
      shift = int(8 * math.sin(2 * math.pi * (i / 6) + y / 12))
      pixels[y] = np.roll(pixels[y], shift, axis=0)
    return Image.fromarray(pixels, "RGBA")

  for _ in range(hold_frames):
    canvas = Image.new("RGBA", FRAME_SIZE, (0, 0, 0, 0))
    canvas.paste(base_img, center, base_img)
    frames.append(canvas)

  for i in range(drift_frames):
    frames.append(apply_linear_drift(base_img, i, (drift_amount, drift_amount)))

  for i in range(glitch_frames):
    scale = blink_scales[i]
    scaled = base_img.resize((int(base_img.width * scale), int(base_img.height * scale)), Image.LANCZOS)
    frame = apply_jitter(scaled, i)
    if i in scanline_indices:
      frame = apply_scanline_shift(frame, i)
    frames.append(frame)

  snap = Image.new("RGBA", FRAME_SIZE, (0, 0, 0, 0))
  snap.paste(base_img, center, base_img)
  frames.append(snap)

  return frames


@register_effect("static_cascade")
def effect_static_cascade(base_img: Image.Image, badge) -> list[Image.Image]:
  """
  Applies a thick horizontal distortion wave that travels vertically
  across the badge, with baked-in scanlines and alpha-safe frames.

  Used for the Triaxilation Node crystal (Legendary tier).

  Returns:
    List of RGBA frames as PIL.Image.Image.
  """
  pad = 16
  total_frames = TOTAL_FRAMES
  amplitude = 14
  band_height = 31

  # Extract badge mask
  badge_alpha = base_img.split()[-1]
  badge_mask = Image.new("L", base_img.size, 0)
  badge_mask.paste(badge_alpha, mask=badge_alpha)

  # Apply scanlines only to badge pixels
  striped_badge = base_img.copy()
  pixels = striped_badge.load()
  alpha = badge_alpha.load()
  for y in range(base_img.height):
    if y % 3 in (0, 1):
      for x in range(base_img.width):
        if alpha[x, y] > 0:
          r, g, b, a = pixels[x, y]
          pixels[x, y] = (max(r - 30, 0), max(g - 30, 0), max(b - 30, 0), a)

  # Paste into padded canvas
  padded_size = (base_img.width + pad * 2, base_img.height + pad * 2)
  padded = Image.new("RGBA", padded_size, (0, 0, 0, 0))
  padded.paste(striped_badge, (pad, pad))

  # Generate distorted frames
  frames = []
  for i in range(total_frames):
    wave_center = ((i / total_frames) * (padded.height + band_height)) - (band_height // 2)
    src = padded.load()
    frame = Image.new("RGBA", padded.size)
    dst = frame.load()

    for y in range(padded.height):
      distance = abs(y - wave_center)
      if distance < band_height:
        t = 1 - (distance / band_height)
        eased = math.sin(t * math.pi / 2)
        offset = int(amplitude * eased)
      else:
        offset = 0

      for x in range(padded.width):
        new_x = x + offset
        if 0 <= new_x < padded.width:
          dst[x, y] = src[new_x, y]
        else:
          dst[x, y] = (0, 0, 0, 0)

    frames.append(frame)

  # Ensure all frames are alpha-safe for APNG disposal
  cleaned_frames = []
  for f in frames:
    canvas = Image.new("RGBA", f.size, (0, 0, 0, 0))
    canvas.paste(f, (0, 0), f)
    cleaned_frames.append(canvas)

  return cleaned_frames


@register_effect("singularity_warp")
def effect_singularity_warp(base_img: Image.Image, badge: dict) -> list[Image.Image]:
  """
  Creates a gravitational vortex effect, pulls the badge into a swirling collapse.

  Used for the Artificial Singularity crystal (Legendary tier).

  Returns:
    List of RGBA frames as PIL.Image.Image.
  """
  width, height = FRAME_SIZE
  cx, cy = width / 2, height / 2
  total_frames = TOTAL_FRAMES

  def ease_in_out(t):
    return 3 * t**2 - 2 * t**3

  frames = []
  for frame_idx in range(total_frames):
    t_raw = frame_idx / (total_frames - 1)
    t = ease_in_out(t_raw)
    collapse_strength = t * 6.0

    # Start swirl on frame 4
    delay_threshold = 3 / total_frames
    if t_raw < delay_threshold:
      swirl_strength = 0.0
    else:
      swirl_progress = (t_raw - delay_threshold) / (1 - delay_threshold)
      swirl_curve = ease_in_out(swirl_progress)
      swirl_strength = swirl_curve * 3.45

    swirl_base = 4.83

    # Get image array and coordinates
    img_array = np.array(base_img)
    y, x = np.meshgrid(np.arange(height), np.arange(width), indexing='ij')
    dx = x - cx
    dy = y - cy
    r = np.sqrt(dx**2 + dy**2) + 1e-6
    norm_r = r / r.max()
    theta = np.arctan2(dy, dx)

    r_collapsed = r * (1 + collapse_strength)

    swirl_weight = (1 - norm_r)**2
    swirl_angle = swirl_base * swirl_strength * swirl_weight
    theta += swirl_angle

    x_src = cx + r_collapsed * np.cos(theta)
    y_src = cy + r_collapsed * np.sin(theta)
    x_src = np.clip(x_src, 0, width - 1)
    y_src = np.clip(y_src, 0, height - 1)
    coords = np.array([y_src.flatten(), x_src.flatten()])

    warped = np.stack([
      map_coordinates(img_array[..., c], coords, order=1, mode='reflect').reshape((height, width))
      for c in range(4)
    ], axis=-1).astype(np.uint8)

    # Fade out near end
    if t > 0.7:
      fade_mask = norm_r
      fade_denom = max(1.0 - t, 1e-6)
      alpha_fade = np.clip((fade_mask / fade_denom)**2, 0, 1)
      warped[..., 3] = (warped[..., 3] * (1 - alpha_fade)).astype(np.uint8)

    frames.append(Image.fromarray(warped, "RGBA"))

  return frames


@register_effect("rainbow_sheen")
def effect_rainbow_sheen(badge_image: Image.Image, badge: dict) -> list[Image.Image]:
  """
  Applies a sweeping diagonal rainbow sheen from top-left to bottom-right.
  Animated loop with blurred, wide-spectrum gradient.

  Used for the Unity Prism crystal (Legendary tier).

  Returns:
    List of RGBA frames as PIL.Image.Image.
  """
  width, height = badge_image.size
  num_frames = 24
  sheen_width = 420
  blur_radius = 36
  max_alpha = 255
  frames = []

  for i in range(num_frames):
    frame = badge_image.copy()
    sheen = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(sheen)
    offset = int((width + height + sheen_width) * i / num_frames) - sheen_width

    for y in range(height):
      for x in range(width):
        pos = x + y
        if offset <= pos < offset + sheen_width:
          t = (pos - offset) / sheen_width
          r = int(127.5 * (1 + np.sin(2 * np.pi * t)))
          g = int(127.5 * (1 + np.sin(2 * np.pi * t - 2 * np.pi / 3)))
          b = int(127.5 * (1 + np.sin(2 * np.pi * t - 4 * np.pi / 3)))
          alpha = int(max_alpha * (1 - abs(t - 0.5) * 2))
          draw.point((x, y), fill=(r, g, b, alpha))

    sheen = sheen.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    mask = badge_image.split()[3]
    masked_sheen = Image.composite(sheen, Image.new("RGBA", (width, height), (0, 0, 0, 0)), mask)
    final_frame = Image.alpha_composite(frame, masked_sheen)
    frames.append(final_frame)

  return frames


#     ...     ..      ..                       s                   .
#   x*8888x.:*8888: -"888:     ..             :8      .uef^"      @88>
#  X   48888X `8888H  8888    @L             .88    :d88E         %8P
# X8x.  8888X  8888X  !888>  9888i   .dL    :888ooo `888E          .          .
# X8888 X8888  88888   "*8%- `Y888k:*888. -*8888888  888E .z8k   .@88u   .udR88N
# '*888!X8888> X8888  xH8>     888E  888I   8888     888E~?888L ''888E` <888'888k
#   `?8 `8888  X888X X888>     888E  888I   8888     888E  888E   888E  9888 'Y"
#   -^  '888"  X888  8888>     888E  888I   8888     888E  888E   888E  9888
#    dx '88~x. !88~  8888>     888E  888I  .8888Lu=  888E  888E   888E  9888
#  .8888Xf.888x:!    X888X.:  x888N><888'  ^%888*    888E  888E   888&  ?8888u../
# :""888":~"888"     `888*"    "88"  888     'Y"    m888N= 888>   R888"  "8888P'
#     "~'    "~        ""            88F             `Y"   888     ""      "P'
#                                   98"                   J88"
#                                 ./"                     @%
#                                ~`                     :"
@register_effect("borg_reconstruction")
def effect_borg_reconstruction(base_img: Image.Image, badge: dict) -> list[Image.Image]:
  """
  Animated tile-by-tile badge construction with growing green nanotiles.

  - Tiles ease in at randomized speeds but finish in sync.
  - Grayscale base, dark green overlay glow.
  - 20-frame construction + 4-frame fade-out (24fps loop).

  Returns:
    List of RGBA frames (24 total) for animated display.
  """
  total_frames = TOTAL_FRAMES
  construct_frames = 20
  fade_frames = 4
  cols, rows = 8, 8
  tile_w = base_img.width // cols
  tile_h = base_img.height // rows
  alpha = base_img.getchannel("A")
  target_green = (40, 150, 70)

  def ease_out(t):
    return 1 - (1 - t) ** 3

  def interpolate(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

  def normalized_eased_progress(t_global, scale):
    t_scaled = min(t_global * scale, 1.0)
    eased = ease_out(t_scaled)
    max_eased = ease_out(min(1.0 * scale, 1.0))
    return eased / max_eased if max_eased > 0 else 1.0

  # Generate animated tiles
  tiles = []
  for row in range(rows):
    for col in range(cols):
      x = col * tile_w
      y = row * tile_h
      tile = base_img.crop((x, y, x + tile_w, y + tile_h))
      alpha_tile = alpha.crop((x, y, x + tile_w, y + tile_h))
      gray_tile = ImageOps.grayscale(tile.convert("RGB")).convert("RGBA")
      gray_tile.putalpha(alpha_tile)

      cx = x + tile_w // 2
      cy = y + tile_h // 2
      dx = cx - base_img.width // 2
      dy = cy - base_img.height // 2
      norm = math.hypot(dx, dy) or 1
      offset_scale = random.uniform(1.5, 2.5)
      offset = (int((dx / norm) * offset_scale * tile_w),
                int((dy / norm) * offset_scale * tile_h))

      tiles.append({
        "tile": gray_tile,
        "start": (x + offset[0], y + offset[1]),
        "end": (x, y),
        "easing_scale": random.uniform(0.6, 1.4),
        "fade_scale": random.uniform(0.85, 1.0),
        "start_green": (
          random.randint(15, 40),
          random.randint(90, 130),
          random.randint(25, 50)
        )
      })

  # Build frame sequence
  frames = []
  for i in range(total_frames):
    frame = Image.new("RGBA", base_img.size, (0, 0, 0, 0))

    if i < construct_frames:
      t_global = i / (construct_frames - 1)
      glow_intensity = t_global
      opacity_mult = 1.0
    else:
      t_global = 1.0
      fade_progress = (i - construct_frames) / (fade_frames - 1)
      glow_intensity = 1.0 - ease_out(fade_progress)
      opacity_mult = glow_intensity

    for t in tiles:
      eased = normalized_eased_progress(t_global, t["easing_scale"])
      sx, sy = t["start"]
      ex, ey = t["end"]
      cx = int(sx + (ex - sx) * eased)
      cy = int(sy + (ey - sy) * eased)

      tile = t["tile"].copy()
      alpha_layer = tile.getchannel("A").point(
        lambda a: int(a * eased * opacity_mult * t["fade_scale"])
      )
      tile.putalpha(alpha_layer)

      glow_color = interpolate(t["start_green"], target_green, glow_intensity)
      overlay = Image.new("RGBA", tile.size, glow_color + (0,))
      glow_mask = alpha_layer.point(lambda a: int(a * glow_intensity * 0.7))
      overlay.putalpha(glow_mask)
      glowing_tile = Image.alpha_composite(tile, overlay)

      frame.paste(glowing_tile, (cx, cy), glowing_tile)

    frames.append(frame)

  return frames


@register_effect("celestial_temple")
def effect_celestial_temple(badge_image: Image.Image, badge: dict) -> list[Image.Image]:
  """
  Cinematic wormhole exit effect.
  A lens flare builds, the wormhole bursts into existence from nothing, and the badge swoops into view.

  Used for the Bajoran Orb crystal (Mythic tier).
  """
  canvas_size = (200, 200)
  base_path = Path("images/crystal_effects/animations/celestial_temple")

  # Load lens flare frames (00–03)
  lens_flare_frames = [
    Image.open(base_path / "lens_flare_frames" / f"{i:02}.png").convert("RGBA").resize(canvas_size)
    for i in range(4)
  ]

  # Load wormhole frames (00–16)
  wormhole_frames = [
    Image.open(base_path / "wormhole_frames" / f"{i:02}.png").convert("RGBA").resize(canvas_size)
    for i in range(17)
  ]

  output_frames = []

  # Frame 0: blank
  blank = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
  output_frames.append(blank.copy())

  # Frames 1–4: lens flare
  for frame in lens_flare_frames:
    base = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    output_frames.append(Image.alpha_composite(base, frame))

  # Frame 5: blank
  output_frames.append(blank.copy())

  # Frames 6–9: wormhole scale in
  for i in range(4):
    scale = i / 3
    wormhole = wormhole_frames[i].copy()
    size = max(1, int(wormhole.width * scale)), max(1, int(wormhole.height * scale))
    scaled = wormhole.resize(size, Image.Resampling.LANCZOS)
    base = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    offset = ((canvas_size[0] - size[0]) // 2, (canvas_size[1] - size[1]) // 2)
    base.paste(scaled, offset, scaled)
    output_frames.append(base)

  # Frames 10–15: badge scale-in
  def ease_out_cubic(t): return 1 - (1 - t) ** 3
  x_offsets = [-10, -5, -2, 1, 0, 0]
  final_scaled_badge = None

  for i in range(6):
    progress = ease_out_cubic(i / 5)
    scale = 0.10 + (1.0 - 0.10) * progress
    size = int(badge_image.width * scale), int(badge_image.height * scale)
    badge_frame = badge_image.resize(size, Image.Resampling.LANCZOS)

    if i == 0:
      badge_frame.putalpha(int(255 * 0.4))

    offset = (
      (canvas_size[0] - size[0]) // 2 + x_offsets[i],
      (canvas_size[1] - size[1]) // 2,
    )

    layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    layer.paste(badge_frame, offset, badge_frame)
    bg = wormhole_frames[i + 4]
    output_frames.append(Image.alpha_composite(bg, layer))

    if i == 5:
      final_scaled_badge = (badge_frame, offset)

  # Frames 16–22: hold final badge
  for i in range(7):
    bg = wormhole_frames[i + 10]
    layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    layer.paste(final_scaled_badge[0], final_scaled_badge[1], final_scaled_badge[0])
    output_frames.append(Image.alpha_composite(bg, layer))

  return output_frames


@register_effect("shimmer_flux")
def effect_shimmer_flux(base_img: Image.Image, badge: dict) -> list[Image.Image]:
  """
  Projects a shimmering beam diagonally across the badge while
  generating bloom, ripple distortions, and chromatic shell overlays.
  Highly animated and prism-like.

  Returns:
    List of RGBA frames as PIL.Image.Image.

  Used for the Omega Molecule crystal (Mythic tier).
  """
  frame_size = FRAME_SIZE
  fps = ANIMATION_FPS
  duration = ANIMATION_DURATION
  num_frames = int(duration * fps)
  band_width = int(128 * 0.8)
  max_displacement = 24
  beam_alpha = int(80 * 0.7)
  beam_color = (60, 120, 255, beam_alpha)
  blur_radius = 32
  width, height = frame_size

  def shimmer_flux_base(badge_img: Image.Image, frame_index: int) -> Image.Image:
    mask = badge_img.getchannel('A').point(lambda p: 255 if p > 0 else 0)

    pulse = 0.5 + 0.5 * np.sin(2 * np.pi * frame_index / num_frames)
    dilation = 4 + int(4 * pulse)
    blurred = mask.filter(ImageFilter.GaussianBlur(radius=dilation))

    cyan = Image.new("RGBA", frame_size, (40, 255, 255, 180))
    teal = Image.new("RGBA", frame_size, (0, 200, 180, 180))
    blue = Image.new("RGBA", frame_size, (80, 120, 255, 180))

    cyan.putalpha(blurred)
    teal.putalpha(blurred)
    blue.putalpha(blurred)

    cyan = ImageChops.offset(cyan, -1, 0)
    teal = ImageChops.offset(teal, 0, -1)
    blue = ImageChops.offset(blue, 1, 1)

    shell = Image.alpha_composite(Image.alpha_composite(cyan, teal), blue)

    edge = mask.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(radius=2))
    bloom = Image.new("RGBA", frame_size, (160, 140, 255, int(100 + 80 * pulse)))
    bloom.putalpha(edge)

    glow = badge_img.filter(ImageFilter.GaussianBlur(radius=6 + 4 * pulse))
    glow = ImageEnhance.Brightness(glow).enhance(1.6 + pulse * 0.8)
    combined = Image.alpha_composite(glow, badge_img)
    with_bloom = Image.alpha_composite(combined, bloom)
    final = Image.alpha_composite(shell, with_bloom)
    return final

  def shimmer_flux_frame(badge: Image.Image, frame_index: int) -> Image.Image:
    frame = shimmer_flux_base(badge, frame_index)

    center_pos = int((frame_index / num_frames) * (width + height))
    beam = Image.new("RGBA", frame_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(beam)
    for y in range(-height, 2 * height, 2):
      x = int(center_pos - y)
      draw.rectangle([(x - band_width, y), (x + band_width, y + 2)], fill=beam_color)
    beam = beam.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    mask = badge.getchannel('A').point(lambda p: 255 if p > 0 else 0)
    masked_beam = Image.composite(beam, Image.new("RGBA", frame_size, (0, 0, 0, 0)), mask)

    badge_arr = np.array(badge)
    distorted = np.copy(badge_arr)
    for y in range(height):
      for x in range(width):
        dx = x + y - center_pos
        if -band_width <= dx <= band_width:
          strength = 1 - abs(dx) / band_width
          offset = int(max_displacement * strength * np.sin(frame_index / num_frames * 2 * np.pi))
          sx = min(max(x + offset, 0), width - 1)
          distorted[y, x] = badge_arr[y, sx]

    distorted_img = Image.fromarray(distorted, mode='RGBA')
    with_distortion = Image.alpha_composite(frame, ImageChops.darker(distorted_img, badge))
    return Image.alpha_composite(with_distortion, masked_beam)

  return [shimmer_flux_frame(base_img, i) for i in range(num_frames)]


# 8888      88 b.             8     ,o888888o.     8 888888888o 8888888 8888888888   .8.          b.             8  8 8888 8 8888      88        ,8.       ,8.
# 8888      88 888o.          8  . 8888     `88.   8 8888    `88.     8 8888        .888.         888o.          8  8 8888 8 8888      88       ,888.     ,888.
# 8888      88 Y88888o.       8 ,8 8888       `8b  8 8888     `88     8 8888       :88888.        Y88888o.       8  8 8888 8 8888      88      .`8888.   .`8888.
# 8888      88 .`Y888888o.    8 88 8888        `8b 8 8888     ,88     8 8888      . `88888.       .`Y888888o.    8  8 8888 8 8888      88     ,8.`8888. ,8.`8888.
# 8888      88 8o. `Y888888o. 8 88 8888         88 8 8888.   ,88'     8 8888     .8. `88888.      8o. `Y888888o. 8  8 8888 8 8888      88    ,8'8.`8888,8^8.`8888.
# 8888      88 8`Y8o. `Y88888o8 88 8888         88 8 8888888888       8 8888    .8`8. `88888.     8`Y8o. `Y88888o8  8 8888 8 8888      88   ,8' `8.`8888' `8.`8888.
# 8888      88 8   `Y8o. `Y8888 88 8888        ,8P 8 8888    `88.     8 8888   .8' `8. `88888.    8   `Y8o. `Y8888  8 8888 8 8888      88  ,8'   `8.`88'   `8.`8888.
# 8888     ,8P 8      `Y8o. `Y8 `8 8888       ,8P  8 8888      88     8 8888  .8'   `8. `88888.   8      `Y8o. `Y8  8 8888 ` 8888     ,8P ,8'     `8.`'     `8.`8888.
#  8888   ,d8P 8         `Y8o.`  ` 8888     ,88'   8 8888    ,88'     8 8888 .888888888. `88888.  8         `Y8o.`  8 8888   8888   ,d8P ,8'       `8        `8.`8888.
#  `Y88888P'   8            `Yo     `8888888P'     8 888888888P       8 8888.8'       `8. `88888. 8            `Yo  8 8888    `Y88888P' ,8'         `         `8.`8888.
@register_effect("moopsy_swarm")
def effect_moopsy_swarm(base_img: Image.Image, badge: dict) -> list[Image.Image]:
  """
  Creates a swarm of Moopsies that travel across the top left to bottom right
  within a windowed background + bright teal border gradient.

  Returns:
    List of RGBA frames as PIL.Image.Image.

  Used for the Bone Fragment crystal (Unobtanium tier).
  """
  badge_size = (190, 190)
  total_frames = 24
  fade_frames = 3
  hold_frame = 3
  move_frames = total_frames - fade_frames - 1

  background_path = "images/crystal_effects/backgrounds/moopsy_background.png"
  moopsy_path = "images/crystal_effects/overlays/moopsy.png"

  # Load resources
  badge_img = base_img.resize((180, 180), Image.Resampling.LANCZOS)
  moopsy_img = Image.open(moopsy_path).convert("RGBA").resize((112, 112), Image.Resampling.LANCZOS)
  background = Image.open(background_path).convert("RGBA").resize(badge_size)

  # Precompute badge base
  base_frame = Image.new("RGBA", badge_size, (0, 0, 0, 0))
  offset = ((badge_size[0] - 180) // 2, (badge_size[1] - 180) // 2)
  base_frame.paste(badge_img, offset, badge_img)

  # Define border masks
  border_width = 2
  border_radius = 24
  outer_mask = Image.new("L", badge_size, 0)
  draw_outer = ImageDraw.Draw(outer_mask)
  draw_outer.rounded_rectangle(
    [border_width // 2, border_width // 2, badge_size[0] - border_width // 2, badge_size[1] - border_width // 2],
    radius=border_radius,
    fill=255
  )
  inner_mask = Image.new("L", badge_size, 0)
  draw_inner = ImageDraw.Draw(inner_mask)
  draw_inner.rounded_rectangle(
    [border_width + 2, border_width + 2, badge_size[0] - border_width - 2, badge_size[1] - border_width - 2],
    radius=border_radius - 4,
    fill=255
  )
  border_mask = ImageChops.subtract(outer_mask, inner_mask)
  background_cropped = Image.composite(background, Image.new("RGBA", badge_size), outer_mask)

  # Precompute gradient border
  top_left = (16, 115, 121)
  bottom_right = (61, 230, 239)
  border_gradient = Image.new("RGBA", badge_size)
  for y in range(badge_size[1]):
    for x in range(badge_size[0]):
      t = (x + y) / (badge_size[0] + badge_size[1])
      r = int(top_left[0] * (1 - t) + bottom_right[0] * t)
      g = int(top_left[1] * (1 - t) + bottom_right[1] * t)
      b = int(top_left[2] * (1 - t) + bottom_right[2] * t)
      border_gradient.putpixel((x, y), (r, g, b, 255))
  gradient_border = Image.composite(border_gradient, Image.new("RGBA", badge_size, (0, 0, 0, 0)), border_mask)

  # Setup moopsy swarm
  moopsy_count = 13
  swarm = []
  dx = (badge_size[0] + 96 + 60) / move_frames
  dy = (badge_size[1] + 96 + 60) / move_frames
  for row_index, count in enumerate([5, 5, 3]):
    for i in range(count):
      row_offset = row_index * 42
      delay = 0 if row_index == 0 else (-4 if row_index == 1 else -6)
      shift = 140
      spacing = 38
      start_x = -112 - (i * spacing) + shift + random.randint(-3, 3)
      start_y = -112 + (i * spacing) + row_offset + random.randint(-3, 3)
      jitter = [random.randint(-9, 9) for _ in range(total_frames)]
      swarm.append({
        "start_x": start_x,
        "start_y": start_y,
        "dx": dx,
        "dy": dy,
        "delay": delay,
        "jitter": jitter
      })
  random.shuffle(swarm)

  # Generate frames
  frames = []
  sweep_offset = 32
  for frame_idx in range(total_frames):
    if frame_idx < fade_frames:
      fade = int(255 * (frame_idx + 1) / fade_frames)
      r, g, b, a = base_frame.split()
      faded = Image.merge("RGBA", (r, g, b, a.point(lambda p: p * fade // 255)))
      shadow = Image.new("RGBA", badge_size, (0, 0, 0, 0))
      shadow.paste((0, 0, 0, 180), (4, 4), faded.split()[-1])
      shadow = shadow.filter(ImageFilter.GaussianBlur(radius=3))
      base = Image.alpha_composite(background_cropped, shadow)
      badge = Image.alpha_composite(base, faded)
      frame = Image.alpha_composite(badge, gradient_border)
      frames.append(frame)
      continue
    elif frame_idx == hold_frame:
      shadow = Image.new("RGBA", badge_size, (0, 0, 0, 0))
      shadow.paste((0, 0, 0, 180), (4, 4), base_frame.split()[-1])
      shadow = shadow.filter(ImageFilter.GaussianBlur(radius=3))
      base = Image.alpha_composite(background_cropped, shadow)
      badge = Image.alpha_composite(base, base_frame)
      frame = Image.alpha_composite(badge, gradient_border)
      frames.append(frame)
      continue

    t = (frame_idx - fade_frames - 1) / (move_frames - 1)
    diag_thresh = int((badge_size[0] + badge_size[1]) * t) + sweep_offset
    sweep_mask = Image.new("L", badge_size, 0)
    draw = ImageDraw.Draw(sweep_mask)
    for y in range(badge_size[1]):
      for x in range(badge_size[0]):
        if x + y < diag_thresh:
          sweep_mask.putpixel((x, y), 255)
    r, g, b, a = base_frame.split()
    masked = Image.merge("RGBA", (r, g, b, ImageChops.subtract(a, sweep_mask)))
    shadow = Image.new("RGBA", badge_size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 180), (4, 4), masked.split()[-1])
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=3))
    base = Image.alpha_composite(background_cropped, shadow)
    badge = Image.alpha_composite(base, masked)

    moopsy_layer = Image.new("RGBA", badge_size, (0, 0, 0, 0))
    moopsy_frame = frame_idx - (fade_frames + 1)
    for m in swarm:
      eff = moopsy_frame + m["delay"]
      if not (0 <= eff < move_frames):
        continue
      x = int(m["start_x"] + m["dx"] * eff * (move_frames / total_frames))
      y = int(m["start_y"] + m["dy"] * eff * (move_frames / total_frames) + m["jitter"][eff % len(m["jitter"])])
      moopsy_layer.paste(moopsy_img, (x, y), moopsy_img)

    moopsies_masked = Image.composite(moopsy_layer, Image.new("RGBA", badge_size, (0, 0, 0, 0)), outer_mask)
    full = Image.alpha_composite(badge, moopsies_masked)
    frame = Image.alpha_composite(full, gradient_border)
    frames.append(frame)

  return frames
