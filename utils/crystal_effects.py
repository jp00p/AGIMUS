import asyncio
import shutil

from common import *

from pathlib import Path
from scipy.ndimage import map_coordinates, binary_dilation, gaussian_filter

from utils.thread_utils import threaded_image_open, threaded_image_open_no_convert

FRAME_SIZE = (190, 190)
ANIMATION_FPS = 12
ANIMATION_DURATION = 2.0


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
# -- Common    – Simple color tints
# -- Uncommon  – Silhouette Effects
# -- Rare      – Backgrounds with Border Gradient
# -- Legendary – Animated effects
# -- Mythic    – Animated + Prestige visual effects
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

  If `image` is a list, saves as an APNG.
  Otherwise, saves as a single static PNG.
  """
  path = get_cached_effect_path(effect, badge_info_id, extension="apng" if isinstance(image, list) else "png")
  path.parent.mkdir(parents=True, exist_ok=True)

  if isinstance(image, list):
    # Save as animated PNG
    first, *rest = image
    first.save(
      path,
      format="PNG",
      save_all=True,
      append_images=rest,
      duration=int(1000 / 12),  # Assuming 12 fps
      loop=0,
      optimize=False,
      disposal=2  # Restore to background before next frame (important)
    )
  else:
    # Save as static PNG
    image.save(path, format="PNG")


def delete_crystal_effects_cache():
  """
  Deletes all cached crystal effect images.
  """
  cache_directory = Path(CACHE_DIR)
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

  tint_color = (255, 230, 150)
  tint_layer = Image.new('RGBA', badge_image.size, tint_color + (int(255 * 0.35),))
  tint_layer_masked = Image.composite(tint_layer, Image.new('RGBA', badge_image.size, (0, 0, 0, 0)), badge_mask)
  badge_tinted = Image.alpha_composite(badge_image, tint_layer_masked)

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
  a = a.point(lambda p: int(p * 0.5))
  shimmer_masked = Image.merge('RGBA', (r, g, b, a))
  shimmer_masked = Image.composite(shimmer_masked, Image.new('RGBA', badge_image.size, (0, 0, 0, 0)), badge_mask)

  glow = shimmer_masked.filter(ImageFilter.GaussianBlur(radius=8))
  glow = ImageEnhance.Brightness(glow).enhance(2.4)
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
@register_effect("isolinear")
def effect_isolinear(img, badge):
  return _apply_gradient_silhouette_border(img, (0, 200, 255), (140, 255, 0))

@register_effect('boridium')
def effect_boridium(img, badge):
  return _apply_energy_rings_silhouette_wrap(img, primary_color=(200, 80, 255), secondary_color=(80, 255, 255))


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
  alpha = badge_img.split()[-1]
  bounds = get_badge_bounds(alpha)
  left, top, right, bottom = bounds
  width = right - left + 2 * padding
  height = bottom - top + 2 * padding
  ring_size = (int(width * 2), int(height * 2))
  badge_offset = ((ring_size[0] - badge_img.width) // 2, (ring_size[1] - badge_img.height) // 2)

  # Generate both rings
  primary_ring = _generate_energy_ring_wrap(ring_size, color=primary_color, rx_scale=0.35, ry_scale=0.15)
  secondary_ring = _generate_energy_ring_wrap(ring_size, color=secondary_color, rx_scale=0.32, ry_scale=0.13)
  combined_ring = Image.alpha_composite(primary_ring, secondary_ring)

  # Create 50% split mask
  badge_w, badge_h = badge_img.size
  front_mask = Image.new("L", ring_size, 0)
  draw = ImageDraw.Draw(front_mask)
  draw.rectangle(
    [badge_offset[0], badge_offset[1] + badge_h // 2,
     badge_offset[0] + badge_w, badge_offset[1] + badge_h],
    fill=255
  )
  front_mask = front_mask.filter(ImageFilter.GaussianBlur(10))
  back_mask = ImageChops.invert(front_mask)

  # Split ring into front/back halves
  front_ring = Image.composite(combined_ring, Image.new("RGBA", ring_size, (0, 0, 0, 0)), front_mask)
  back_ring = Image.composite(combined_ring, Image.new("RGBA", ring_size, (0, 0, 0, 0)), back_mask)

  # Composite result
  canvas = Image.new("RGBA", ring_size, (0, 0, 0, 0))
  canvas.paste(back_ring, (0, 0), back_ring)
  canvas.paste(badge_img, badge_offset, badge_img)
  canvas.paste(front_ring, (0, 0), front_ring)

  return canvas

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
) -> Image.Image:
  """
  Applies a rare-tier crystal effect with a diagonal gradient border.

  Args:
    badge_image: The badge RGBA image.
    background_path: Path to the background image file.
    border_gradient_top_left: RGB tuple for the top-left corner color.
    border_gradient_bottom_right: RGB tuple for the bottom-right color.
    border_width: Thickness of the border.
    border_radius: Corner rounding radius.

  Returns:
    Image.Image with the full visual effect applied.
  """
  badge_size = badge_image.size

  # Load and mask the background
  background = Image.open(background_path).convert("RGBA").resize(badge_size)
  outer_mask = Image.new("L", badge_size, 0)
  draw_outer = ImageDraw.Draw(outer_mask)
  draw_outer.rounded_rectangle(
    [border_width // 2, border_width // 2, badge_size[0] - border_width // 2, badge_size[1] - border_width // 2],
    radius=border_radius,
    fill=255
  )
  background_cropped = Image.composite(background, Image.new("RGBA", badge_size), outer_mask)

  # Composite badge onto background
  composite = Image.alpha_composite(background_cropped, badge_image)

  # Create diagonal border gradient
  border_gradient = Image.new("RGBA", badge_size)
  for y in range(badge_size[1]):
    for x in range(badge_size[0]):
      t = (x + y) / (badge_size[0] + badge_size[1])
      r = int(border_gradient_top_left[0] * (1 - t) + border_gradient_bottom_right[0] * t)
      g = int(border_gradient_top_left[1] * (1 - t) + border_gradient_bottom_right[1] * t)
      b = int(border_gradient_top_left[2] * (1 - t) + border_gradient_bottom_right[2] * t)
      border_gradient.putpixel((x, y), (r, g, b, 255))

  # Create mask for just the border ring
  inner_mask = Image.new("L", badge_size, 0)
  draw_inner = ImageDraw.Draw(inner_mask)
  draw_inner.rounded_rectangle(
    [border_width + 2, border_width + 2, badge_size[0] - border_width - 2, badge_size[1] - border_width - 2],
    radius=border_radius - 4,
    fill=255
  )
  border_mask = ImageChops.subtract(outer_mask, inner_mask)
  gradient_border = Image.composite(border_gradient, Image.new("RGBA", badge_size, (0, 0, 0, 0)), border_mask)

  # Final composite with gradient border
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
  bg_path = f"{RARE_BACKGROUNDS_DIR}/cystalline_entity.png"
  result = apply_rare_background_and_border(
    badge_image,
    bg_path,
    border_gradient_top_left=(204, 205, 255),
    border_gradient_bottom_right=(49, 49, 99)
  )
  return result

@register_effect("q_grid")
def effect_q_grid(badge_image: Image.Image, badge: dict) -> Image.Image:
  """
  Q Grid from Encounter at Farpoint background.
  Used for the Continuum crystal (Rare tier).
  """
  bg_path = f"{RARE_BACKGROUNDS_DIR}/q_grid.png"
  result = apply_rare_background_and_border(
    badge_image,
    bg_path,
    border_gradient_top_left=(196, 197, 247),
    border_gradient_bottom_right=(50, 51, 101)
  )
  return result

@register_effect("coffee_nebula")
def effect_trilithium_banger(badge_image: Image.Image, badge: dict) -> Image.Image:
  """
  The nebula from "There's Coffee In That Nebula" background.
  Used for the Colombian Coffee Crystal (Rare tier).
  """
  bg_path = f"{RARE_BACKGROUNDS_DIR}/q_grid.png"
  result = apply_rare_background_and_border(
    badge_image,
    bg_path,
    border_gradient_top_left=(157, 122, 134),
    border_gradient_bottom_right=(43, 33, 54)
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


@register_effect("shimmer_flux")
def effect_shimmer_flux(base_img: Image.Image, badge: dict) -> list[Image.Image]:
  """
  Projects a shimmering beam diagonally across the badge while
  generating bloom, ripple distortions, and chromatic shell overlays.
  Highly animated and prism-like.

  Returns:
    List of RGBA frames as PIL.Image.Image.

  Used for the Omega Molecule crystal (Legendary tier).
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
@register_effect("phase_flicker")
def effect_phase_flicker(base_img: Image.Image, badge: dict) -> list[Image.Image]:
  """
  Introduces animated glitches such as chromatic aberation, position jitter,
  scanline shifts, scaling flickers, and frame blinks. Emulates unstable
  temporal phasing of the badge.

  Used for the Chroniton crystal (Mythic tier).

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

@register_effect("celestial_temple")
def effect_celestial_temple(badge_image: Image.Image, badge: dict) -> list[Image.Image]:
  """
  Cinematic wormhole exit effect.
  A lens flare builds, the wormhole bursts into existence from nothing, and the badge swoops into view.

  Used for the Bajoran Orb crystal (Mythic tier).
  """
  canvas_size = (200, 200)
  base_path = Path("./images/crystal_effects/animations/celestial_temple")

  # Load lens flare frames (01–07)
  lens_flare_frames = []
  for i in range(1, 8):
    path = base_path / "lens_flare" / f"{i:02}.png"
    lens_flare_frames.append(Image.open(path).convert("RGBA"))

  # Load wormhole frames (01–17)
  wormhole_frames = []
  for i in range(1, 18):
    path = base_path / "wormhole" / f"{i:02}.png"
    wormhole_frames.append(Image.open(path).convert("RGBA"))

  output_frames = []

  # Frames 0–6: lens flare only
  for i in range(7):
    base = Image.new("RGBA", canvas_size, (0, 0, 0, 255))
    output_frames.append(Image.alpha_composite(base, lens_flare_frames[i]))

  # Frames 7–10: wormhole scales in from 0% → 100%
  for i in range(4):
    scale = i / 3  # 0.0, 0.33, 0.66, 1.0
    wormhole = wormhole_frames[i].copy()
    size = max(1, int(wormhole.width * scale)), max(1, int(wormhole.height * scale))
    scaled = wormhole.resize(size, Image.LANCZOS)

    base = Image.new("RGBA", canvas_size, (0, 0, 0, 255))
    offset = (
      (canvas_size[0] - size[0]) // 2,
      (canvas_size[1] - size[1]) // 2,
    )
    base.paste(scaled, offset, scaled)
    output_frames.append(base)

  # Frames 11–16: badge scale-in (ease-out cubic)
  def ease_out_cubic(t): return 1 - (1 - t) ** 3
  x_offsets = [-10, -5, -2, 1, 0, 0]

  for i in range(6):
    progress = ease_out_cubic(i / 5)
    scale = 0.10 + (1.0 - 0.10) * progress
    size = int(badge_image.width * scale), int(badge_image.height * scale)
    badge_frame = badge_image.resize(size, Image.LANCZOS)

    if i == 0:
      badge_frame.putalpha(int(255 * 0.4))  # subtle fade-in on first frame

    offset = (
      (canvas_size[0] - size[0]) // 2 + x_offsets[i],
      (canvas_size[1] - size[1]) // 2,
    )

    layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    layer.paste(badge_frame, offset, badge_frame)
    bg = wormhole_frames[i + 4].copy().resize(canvas_size, Image.LANCZOS)
    output_frames.append(Image.alpha_composite(bg, layer))

  # Frames 17–23: hold at full badge
  for i in range(7):
    bg = wormhole_frames[i + 10].copy().resize(canvas_size, Image.LANCZOS)
    layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    offset = (
      (canvas_size[0] - badge_image.width) // 2,
      (canvas_size[1] - badge_image.height) // 2,
    )
    layer.paste(badge_image, offset, badge_image)
    output_frames.append(Image.alpha_composite(bg, layer))

  return output_frames


# Helpers
def get_badge_bounds(mask: Image.Image) -> tuple[int, int, int, int]:
  """
  Returns bounding box of non-transparent pixels in the alpha mask.
  """
  bbox = mask.getbbox()
  if bbox:
    return bbox
  return 0, 0, mask.width, mask.height
