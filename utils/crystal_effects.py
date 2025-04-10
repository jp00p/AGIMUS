from common import *

from pathlib import Path

from queries.crystals import db_get_active_crystal

# Rarity Tier Design Philosophy:
#
# Common    – Simple color tints
# Uncommon  – Visual overlays (e.g. patterns)
# Rare      – Background effects (may include subtle top overlays)
# Legendary – Animated overlays or backdrops
# Mythic    – Animated + prestige visual effects
#
async def apply_crystal_effect(badge_image: Image.Image, badge: dict, crystal: dict = None) -> Image.Image:
  """
  Applies a crystal's visual effect to a badge image.
  Args:
    badge_image: PIL Image of the badge
    badge: dict containing crystal info inline OR badge_instance_id for fallback
  """
  # Try to construct crystal from badge dict if not explicitly passed
  if not crystal:
    if badge.get('effect') and badge.get('crystal_name'):
      crystal = {
        'effect': badge.get('effect'),
        'crystal_name': badge.get('crystal_name'),
        'rarity_rank': badge.get('rarity_rank'),
        'emoji': badge.get('emoji'),
        'description': badge.get('description'),
      }
    else:
      # fallback to DB if crystal info not embedded
      crystal = await db_get_active_crystal(badge['badge_instance_id'])

  if not crystal:
    return badge_image  # no crystal to apply

  effect_key = crystal.get("effect")
  if not effect_key:
    return badge_image  # crystal has no visual effect

  fn = _EFFECT_ROUTER.get(effect_key)
  if fn:
    return fn(badge_image, badge, crystal)
  return badge_image



# --- Internal Effect Registry ---
_EFFECT_ROUTER = {}

def register_effect(name):
  def decorator(fn):
    _EFFECT_ROUTER[name] = fn
    return fn
  return decorator


# --- Common Tier Tint Effects ---
@register_effect("pink_tint")
def effect_pink_tint(img: Image.Image, badge: dict, crystal: dict) -> Image.Image:
  return _apply_tint(img, (255, 105, 180))  # Hot pink

@register_effect("blue_tint")
def effect_blue_tint(img: Image.Image, badge: dict, crystal: dict) -> Image.Image:
  return _apply_tint(img, (102, 204, 255))  # Soft blue

@register_effect("steel_tint")
def effect_steel_tint(img: Image.Image, badge: dict, crystal: dict) -> Image.Image:
  return _apply_tint(img, (170, 170, 170), 0.75)  # Metallic gray

@register_effect("orange_tint")
def effect_orange_tint(img: Image.Image, badge: dict, crystal: dict) -> Image.Image:
  return _apply_tint(img, (255, 165, 90))  # Warm orange

@register_effect("purple_tint")
def effect_purple_tint(img: Image.Image, badge: dict, crystal: dict) -> Image.Image:
  return _apply_tint(img, (180, 110, 230))  # Soft violet

@register_effect("greenmint_tint")
def effect_greenmint_tint(img: Image.Image, badge: dict, crystal: dict) -> Image.Image:
  return _apply_tint(img, (100, 220, 180))  # Minty green

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


# --- Uncommon Tier Overlay Effects ---
UNCOMMON_OVERLAYS_DIR = 'images/crystal_effects/overlays/'

@register_effect("isolinear")
def effect_isolinear(badge_image: Image.Image, badge: dict, crystal: dict) -> Image.Image:
  overlay_filename = 'isolinear.png'
  overlay_path = f"{UNCOMMON_OVERLAYS_DIR}{overlay_filename}"
  overlay = Image.open(overlay_path).convert('L').resize(badge_image.size)
  mask = badge_image.split()[3].point(lambda p: 255 if p > 0 else 0).convert('L')

  # Hardcoded neon gradient (teal to magenta)
  color_top = (0, 255, 180)
  color_bottom = (255, 0, 180)

  gradient = Image.new('RGBA', badge_image.size)
  draw = ImageDraw.Draw(gradient)
  for y in range(badge_image.height):
    ratio = y / badge_image.height
    r = int(color_top[0] * (1 - ratio) + color_bottom[0] * ratio)
    g = int(color_top[1] * (1 - ratio) + color_bottom[1] * ratio)
    b = int(color_top[2] * (1 - ratio) + color_bottom[2] * ratio)
    draw.line([(0, y), (badge_image.width, y)], fill=(r, g, b, 255))

  # Apply circuitry as alpha to gradient
  gradient.putalpha(overlay)

  # Mask overlay to badge shape only
  overlay_masked = Image.composite(gradient, Image.new('RGBA', badge_image.size, (0, 0, 0, 0)), mask)

  # Glow: blur the overlay and brighten it
  glow = overlay_masked.filter(ImageFilter.GaussianBlur(radius=6))
  glow = ImageEnhance.Brightness(glow).enhance(2.5)
  glow = Image.composite(glow, Image.new('RGBA', badge_image.size, (0, 0, 0, 0)), mask)

  # Final composite
  base_with_glow = Image.alpha_composite(glow, badge_image)
  final = Image.alpha_composite(base_with_glow, overlay_masked)

  return final

@register_effect("positronic")
def effect_positronic(badge_image: Image.Image, badge: dict, crystal: dict) -> Image.Image:
  overlay_filename = 'positronic.png'
  overlay_path = f"{UNCOMMON_OVERLAYS_DIR}{overlay_filename}"
  overlay = Image.open(overlay_path).convert('L').resize(badge_image.size)

  # Radial gradient colors
  color_center = (0, 255, 255)   # bright cyan
  color_edge = (0, 100, 255)     # warp blue

  # Create radial gradient
  def create_radial_gradient(size, color_inner, color_outer):
    cx, cy = size[0] // 2, size[1] // 2
    max_radius = (cx**2 + cy**2) ** 0.5
    gradient = Image.new('RGBA', size)
    pixels = gradient.load()
    for y in range(size[1]):
      for x in range(size[0]):
        dx = x - cx
        dy = y - cy
        dist = (dx**2 + dy**2) ** 0.5 / max_radius
        r = int(color_inner[0] * (1 - dist) + color_outer[0] * dist)
        g = int(color_inner[1] * (1 - dist) + color_outer[1] * dist)
        b = int(color_inner[2] * (1 - dist) + color_outer[2] * dist)
        pixels[x, y] = (r, g, b, 255)
    return gradient

  gradient_img = create_radial_gradient(badge_image.size, color_center, color_edge)
  gradient_img.putalpha(overlay)

  # Mask to badge shape
  badge_mask = badge_image.split()[3].point(lambda p: 255 if p > 0 else 0).convert('L')
  masked_overlay = Image.composite(gradient_img, Image.new('RGBA', badge_image.size, (0, 0, 0, 0)), badge_mask)

  # Glow boost
  glow = masked_overlay.filter(ImageFilter.GaussianBlur(radius=12))
  glow = ImageEnhance.Brightness(glow).enhance(3.5)
  glow = Image.composite(glow, Image.new('RGBA', badge_image.size, (0, 0, 0, 0)), badge_mask)

  # Final composite
  combined = Image.alpha_composite(glow, badge_image)
  final = Image.alpha_composite(combined, masked_overlay)
  return final

@register_effect("optical")
def effect_optical(badge_image: Image.Image, badge: dict, crystal: dict) -> Image.Image:
  overlay_filename = 'optical.png'
  overlay_path = f"{UNCOMMON_OVERLAYS_DIR}{overlay_filename}"
  overlay = Image.open(overlay_path).convert('L').resize(badge_image.size)

  # Create vertical beam gradient (white center → dark edges)
  gradient_img = Image.new('RGBA', badge_image.size)
  draw = ImageDraw.Draw(gradient_img)
  for x in range(badge_image.width):
    dist = abs(x - badge_image.width // 2) / (badge_image.width / 2)
    bright = int(255 * (1 - dist**1.8))
    draw.line([(x, 0), (x, badge_image.height)], fill=(bright, bright, bright, 255))

  gradient_img.putalpha(overlay)

  # Mask to badge shape
  badge_mask = badge_image.split()[3].point(lambda p: 255 if p > 0 else 0).convert('L')
  masked_overlay = Image.composite(gradient_img, Image.new('RGBA', badge_image.size, (0, 0, 0, 0)), badge_mask)

  # Glow boost
  glow = masked_overlay.filter(ImageFilter.GaussianBlur(radius=12))
  glow = ImageEnhance.Brightness(glow).enhance(4.0)
  glow = Image.composite(glow, Image.new('RGBA', badge_image.size, (0, 0, 0, 0)), badge_mask)

  # Final composite
  base_with_glow = Image.alpha_composite(glow, badge_image)
  final = Image.alpha_composite(base_with_glow, masked_overlay)
  return final

@register_effect("latinum")
def effect_latinum(badge_image: Image.Image, badge: dict, crystal: dict) -> Image.Image:
  """
  Note that this effect actually uses no overlay image asset because one is unnecessary.
  """
  if badge_image.mode != 'RGBA':
    badge_image = badge_image.convert('RGBA')

  width, height = badge_image.size
  badge_mask = badge_image.split()[3].point(lambda p: 255 if p > 0 else 0).convert('L')

  # Apply a light golden tint to the badge
  tint_color = (255, 230, 150)
  tint_layer = Image.new('RGBA', badge_image.size, tint_color + (int(255 * 0.35),))
  badge_tinted = Image.alpha_composite(badge_image, tint_layer)

  # Create horizontal shimmer band gradient
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

  # Fade shimmer band to 50% opacity and mask to badge shape
  r, g, b, a = gradient_img.split()
  a = a.point(lambda p: int(p * 0.5))
  shimmer_masked = Image.merge('RGBA', (r, g, b, a))
  shimmer_masked = Image.composite(shimmer_masked, Image.new('RGBA', badge_image.size, (0, 0, 0, 0)), badge_mask)

  # Add a subtle outer glow around the shimmer
  glow = shimmer_masked.filter(ImageFilter.GaussianBlur(radius=8))
  glow = ImageEnhance.Brightness(glow).enhance(2.4)
  glow = Image.composite(glow, Image.new('RGBA', badge_image.size, (0, 0, 0, 0)), badge_mask)

  # Final composite
  base_with_glow = Image.alpha_composite(glow, badge_tinted)
  final = Image.alpha_composite(base_with_glow, shimmer_masked)
  return final

@register_effect("cryonetrium")
def effect_cryonetrium(badge_image: Image.Image, badge: dict, crystal: dict) -> Image.Image:
  overlay_filename = 'cryonetrium.png'
  overlay_path = f"{UNCOMMON_OVERLAYS_DIR}{overlay_filename}"
  overlay = Image.open(overlay_path).convert('L').resize(badge_image.size)

  if badge_image.mode != 'RGBA':
    badge_image = badge_image.convert('RGBA')

  width, height = badge_image.size
  badge_mask = badge_image.getchannel('A').point(lambda p: 255 if p > 0 else 0).convert('L')

  # Create diagonal gradient from bottom-left (purple) to top-right (blue)
  def cryonetrium_gradient(size, color_bl=(200, 100, 255), color_tr=(80, 180, 255)):
    w, h = size
    img = Image.new("RGBA", size)
    pixels = img.load()
    for y in range(h):
      for x in range(w):
        t = ((x / w) + (1 - y / h)) / 2
        r = int(color_bl[0] * (1 - t) + color_tr[0] * t)
        g = int(color_bl[1] * (1 - t) + color_tr[1] * t)
        b = int(color_bl[2] * (1 - t) + color_tr[2] * t)
        pixels[x, y] = (r, g, b, 255)
    return img

  gradient = cryonetrium_gradient(badge_image.size)
  gradient.putalpha(overlay)

  # Mask to badge shape
  overlay_masked = Image.composite(gradient, Image.new('RGBA', badge_image.size, (0, 0, 0, 0)), badge_mask)

  # Boost overlay visibility
  r, g, b, a = overlay_masked.split()
  a = a.point(lambda p: min(int(p * 2.0), 255))
  overlay_masked = Image.merge('RGBA', (r, g, b, a))

  # Glow effect
  glow = overlay_masked.filter(ImageFilter.GaussianBlur(radius=14))
  glow = ImageEnhance.Brightness(glow).enhance(3.8)
  glow = Image.composite(glow, Image.new('RGBA', badge_image.size, (0, 0, 0, 0)), badge_mask)

  # Final composite
  base_with_glow = Image.alpha_composite(glow, badge_image)
  final = Image.alpha_composite(base_with_glow, overlay_masked)
  return final


# --- Rare Tier Background Effects ---
RARE_BACKGROUNDS_DIR = 'images/crystal_effects/backgrounds/'

def _apply_radial_fade(img: Image.Image, fade_start_ratio=0.6, fade_end_ratio=0.85, feather_power=0.5) -> Image.Image:
  width, height = img.size
  cx, cy = width // 2, height // 2
  max_radius = (cx**2 + cy**2) ** 0.5
  fade_start = max_radius * fade_start_ratio
  fade_end = max_radius * fade_end_ratio
  mask = Image.new("L", img.size, 255)
  pixels = mask.load()
  for y in range(height):
    for x in range(width):
      dx = x - cx
      dy = y - cy
      distance = (dx**2 + dy**2) ** 0.5
      if distance <= fade_start:
        alpha = 255
      elif distance >= fade_end:
        alpha = 0
      else:
        ratio = (distance - fade_start) / (fade_end - fade_start)
        alpha = int(255 * (1 - ratio**feather_power))
      pixels[x, y] = max(0, min(alpha, 255))
  r, g, b, _ = img.split()
  final_radial = Image.merge("RGBA", (r, g, b, mask))
  vignette = apply_vignette_alpha(final_radial)
  return vignette

def apply_vignette_alpha(img: Image.Image, fade_start_ratio=0.025, fade_end_ratio=0.73) -> Image.Image:
  """
  Applies a strong circular alpha fade to the image corners, creating a vignette-like transparency.
  fade_start_ratio: where full opacity ends (as a % of max radius)
  fade_end_ratio: where full transparency begins (as a % of max radius)
  """
  if img.mode != "RGBA":
    img = img.convert("RGBA")

  width, height = img.size
  cx, cy = width // 2, height // 2
  max_radius = (cx**2 + cy**2) ** 0.5
  fade_start = max_radius * fade_start_ratio
  fade_end = max_radius * fade_end_ratio

  vignette = Image.new("L", (width, height), 255)
  pixels = vignette.load()

  for y in range(height):
    for x in range(width):
      dx = x - cx
      dy = y - cy
      distance = (dx**2 + dy**2) ** 0.5
      if distance <= fade_start:
        alpha = 255
      elif distance >= fade_end:
        alpha = 0
      else:
        # Ease out: steeper fade toward the edge
        ratio = (distance - fade_start) / (fade_end - fade_start)
        alpha = int(255 * (1 - ratio ** 2.5))  # sharper drop-off
      pixels[x, y] = alpha

  r, g, b, a = img.split()
  combined_alpha = ImageChops.multiply(a, vignette)
  return Image.merge("RGBA", (r, g, b, combined_alpha))

@register_effect("trilithium_banger")
def effect_trilithium_banger(badge_image: Image.Image, badge: dict, crystal: dict) -> Image.Image:
  bg_path = f"{RARE_BACKGROUNDS_DIR}trilithium_banger.png"
  background = Image.open(bg_path).convert("RGBA").resize(badge_image.size)
  faded_background = _apply_radial_fade(background)
  composite = Image.alpha_composite(faded_background, badge_image.resize(faded_background.size))
  return composite

@register_effect("tholian_web")
def effect_tholian_web(badge_image: Image.Image, badge: dict, crystal: dict) -> Image.Image:
  bg_path = f"{RARE_BACKGROUNDS_DIR}tholian_web.png"
  background = Image.open(bg_path).convert("RGBA").resize(badge_image.size)
  faded_background = _apply_radial_fade(background)
  composite = Image.alpha_composite(faded_background, badge_image.resize(faded_background.size))
  return composite

@register_effect("holo_grid")
def effect_holo_grid(badge_image: Image.Image, badge: dict, crystal: dict) -> Image.Image:
  bg_path = f"{RARE_BACKGROUNDS_DIR}holo_grid.png"
  background = Image.open(bg_path).convert("RGBA").resize(badge_image.size)
  faded_background = _apply_radial_fade(background)
  composite = Image.alpha_composite(faded_background, badge_image.resize(faded_background.size))
  return composite


# -- Legendary Animations

@register_effect("warp_pulse")
def effect_warp_pulse(base_img: Image.Image, fps: int = 12, duration: float = 3.0) -> list[Image.Image]:
  """Emits outward-pulsing vibrant blue rings from the center of the badge."""
  width, height = base_img.size
  num_frames = int(duration * fps)
  center = (width // 2, height // 2)

  frames = []
  num_rings = 3
  ring_interval = num_frames // num_rings
  max_radius = width // 2
  ring_thickness = 26

  for frame_index in range(num_frames):
    # Transparent base for layering
    frame = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
    glow_layer = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow_layer)

    for ring_i in range(num_rings):
      ring_age = (frame_index - ring_i * ring_interval) % num_frames
      ring_progress = ring_age / num_frames
      radius = int(max_radius * ring_progress)

      if radius <= 0 or radius >= max_radius:
        continue

      fade_factor = 1 - (radius / max_radius)
      alpha_val = int(255 * fade_factor)
      ring_color = (0, 200, 255, alpha_val)

      bbox = [
        center[0] - radius,
        center[1] - radius,
        center[0] + radius,
        center[1] + radius,
      ]
      draw.ellipse(bbox, outline=ring_color, width=ring_thickness)

    blurred_glow = glow_layer.filter(ImageFilter.GaussianBlur(radius=12))
    frame = Image.alpha_composite(frame, blurred_glow)
    frame = Image.alpha_composite(frame, base_img)

    frames.append(frame)

  return frames

