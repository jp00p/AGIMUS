from common import *

from pathlib import Path
from scipy.ndimage import map_coordinates

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


#  .d8888b.
# d88P  Y88b
# 888    888
# 888         .d88b.  88888b.d88b.  88888b.d88b.   .d88b.  88888b.
# 888        d88""88b 888 "888 "88b 888 "888 "88b d88""88b 888 "88b
# 888    888 888  888 888  888  888 888  888  888 888  888 888  888
# Y88b  d88P Y88..88P 888  888  888 888  888  888 Y88..88P 888  888
#  "Y8888P"   "Y88P"  888  888  888 888  888  888  "Y88P"  888  888
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


# 888     888
# 888     888
# 888     888
# 888     888 88888b.   .d8888b .d88b.  88888b.d88b.  88888b.d88b.   .d88b.  88888b.
# 888     888 888 "88b d88P"   d88""88b 888 "888 "88b 888 "888 "88b d88""88b 888 "88b
# 888     888 888  888 888     888  888 888  888  888 888  888  888 888  888 888  888
# Y88b. .d88P 888  888 Y88b.   Y88..88P 888  888  888 888  888  888 Y88..88P 888  888
#  "Y88888P"  888  888  "Y8888P "Y88P"  888  888  888 888  888  888  "Y88P"  888  888
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


# 8888888b.
# 888   Y88b
# 888    888
# 888   d88P  8888b.  888d888 .d88b.
# 8888888P"      "88b 888P"  d8P  Y8b
# 888 T88b   .d888888 888    88888888
# 888  T88b  888  888 888    Y8b.
# 888   T88b "Y888888 888     "Y8888
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
  """
  Purple Space Explosion / Butthole.
  Used for the Trilithium crystal.
  """
  bg_path = f"{RARE_BACKGROUNDS_DIR}trilithium_banger.png"
  background = Image.open(bg_path).convert("RGBA").resize(badge_image.size)
  faded_background = _apply_radial_fade(background)
  composite = Image.alpha_composite(faded_background, badge_image.resize(faded_background.size))
  return composite

@register_effect("tholian_web")
def effect_tholian_web(badge_image: Image.Image, badge: dict, crystal: dict) -> Image.Image:
  """
  The Tholian Web in space.
  Used for the Tholian Silk crystal.
  """
  bg_path = f"{RARE_BACKGROUNDS_DIR}tholian_web.png"
  background = Image.open(bg_path).convert("RGBA").resize(badge_image.size)
  faded_background = _apply_radial_fade(background)
  composite = Image.alpha_composite(faded_background, badge_image.resize(faded_background.size))
  return composite

@register_effect("holo_grid")
def effect_holo_grid(badge_image: Image.Image, badge: dict, crystal: dict) -> Image.Image:
  """
  Classic Holodeck Grid
  Used for the Photonic Shard crystal.
  """
  bg_path = f"{RARE_BACKGROUNDS_DIR}holo_grid.png"
  background = Image.open(bg_path).convert("RGBA").resize(badge_image.size)
  faded_background = _apply_radial_fade(background)
  composite = Image.alpha_composite(faded_background, badge_image.resize(faded_background.size))
  return composite


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
def effect_warp_pulse(base_img: Image.Image, fps: int = 12, duration: float = 3.0) -> list[Image.Image]:
  """
  Emits outward-pulsing vibrant blue rings from the center of the badge.
  Used for the Warp Plasma crystal.
  """
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


@register_effect("subspace_ripple")
def effect_subspace_ripple(base_img: Image.Image, fps: int = 12, duration: float = 2.0) -> list[Image.Image]:
  """
  Applies a diagonal subspace ripple distortion to the badge, simulating wave-like temporal displacement.
  Used for the Tetryon crystal.
  """
  # Resize for performance consistency
  size = (512, 512)
  base_img = base_img.resize(size, Image.LANCZOS)
  badge_array = np.array(base_img)
  height, width = size

  # Ripple parameters
  amplitude = 8
  wavelength = 96
  num_frames = int(duration * fps)
  speed = 2 * np.pi / num_frames

  Y, X = np.meshgrid(np.arange(height), np.arange(width), indexing="ij")
  frames = []

  for i in range(num_frames):
    phase = i * speed
    offset = amplitude * np.sin((X + Y) / wavelength * 2 * np.pi + phase)
    coords_y = Y + offset
    coords_x = X + offset
    coords = np.array([coords_y.flatten(), coords_x.flatten()])

    # Apply the distortion to each RGBA channel
    channels = [
      map_coordinates(badge_array[..., c], coords, order=1, mode='reflect').reshape((height, width))
      for c in range(4)
    ]
    distorted = np.stack(channels, axis=-1).astype(np.uint8)
    frames.append(Image.fromarray(distorted, mode="RGBA"))

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
@register_effect("phase_flicker")
def effect_phase_flicker(base_img: Image.Image, badge: dict, crystal: dict) -> list[Image.Image]:
  """
  Applies chromatic aberation, jitters, drift, size-popping, and scanline distortion.
  Used for the Chroniton crystal.
  """
  frame_size = (512, 512)
  fps = 12
  hold_frames = 8
  drift_frames = 8
  glitch_frames = 8
  drift_amount = 0.5
  scanline_indices = [4, 5, 6, 7]
  flicker_pattern = [1, 0, 1, 0, 1, 1, 1, 1]
  blink_scales = [1.0, 0.97, 1.08, 0.93, 1.12, 1.0, 0.95, 1.05]

  def apply_linear_drift(badge_img: Image.Image, frame_index: int, drift_per_frame: tuple[float, float]) -> Image.Image:
    dx = int(drift_per_frame[0] * frame_index)
    dy = int(drift_per_frame[1] * frame_index)
    r, g, b, a = badge_img.split()
    r = ImageChops.offset(r, 2, 0)
    b = ImageChops.offset(b, -1, 0)
    rgb = Image.merge("RGB", (r, g, b))
    img = Image.merge("RGBA", (*rgb.split(), a))
    canvas = Image.new("RGBA", frame_size, (0, 0, 0, 0))
    offset = ((frame_size[0] - badge_img.width) // 2 + dx, (frame_size[1] - badge_img.height) // 2 + dy)
    canvas.paste(img, offset, img)
    return canvas

  def apply_jitter(badge_img: Image.Image, frame_index: int) -> Image.Image:
    np.random.seed(frame_index + 100)
    jitter_x, jitter_y = np.random.randint(-12, 13, size=2)
    np.random.seed(frame_index)
    jitters = np.random.randint(-6, 7, (3, 2))
    r, g, b, a = badge_img.split()
    r = ImageChops.offset(r, *jitters[0])
    g = ImageChops.offset(g, *jitters[1])
    b = ImageChops.offset(b, *jitters[2])
    rgb = Image.merge("RGB", (r, g, b))
    img = Image.merge("RGBA", (*rgb.split(), a))
    canvas = Image.new("RGBA", frame_size, (0, 0, 0, 0))
    offset = ((frame_size[0] - badge_img.width) // 2 + jitter_x, (frame_size[1] - badge_img.height) // 2 + jitter_y)
    canvas.paste(img, offset, img)
    return canvas

  def apply_scanline_shift(img: Image.Image, frame_index: int) -> Image.Image:
    pixels = np.array(img)
    for y in range(0, pixels.shape[0], 2):
      shift = int(8 * math.sin(2 * math.pi * (frame_index / 6) + y / 12))
      pixels[y] = np.roll(pixels[y], shift, axis=0)
    return Image.fromarray(pixels, "RGBA")

  def flicker_frame(img: Image.Image, visible: bool) -> Image.Image:
    return img if visible else Image.new("RGBA", img.size, (0, 0, 0, 0))

  base_img = base_img.resize(frame_size, Image.LANCZOS)
  center = ((frame_size[0] - base_img.width) // 2, (frame_size[1] - base_img.height) // 2)
  frames = []

  for _ in range(hold_frames):
    canvas = Image.new("RGBA", frame_size, (0, 0, 0, 0))
    canvas.paste(base_img, center, base_img)
    frames.append(canvas)

  for i in range(drift_frames):
    frame = apply_linear_drift(base_img, i, (drift_amount, drift_amount))
    frames.append(frame)

  for i in range(glitch_frames):
    scale = blink_scales[i]
    scaled = base_img.resize((int(base_img.width * scale), int(base_img.height * scale)), Image.LANCZOS)
    frame = apply_jitter(scaled, i)
    if i in scanline_indices:
      frame = apply_scanline_shift(frame, i)
    frame = flicker_frame(frame, bool(flicker_pattern[i]))
    frames.append(frame)

  snap = Image.new("RGBA", frame_size, (0, 0, 0, 0))
  snap.paste(base_img, center, base_img)
  frames.append(snap)

  return frames


@register_effect("shimmer_flux")
def effect_shimmer_flux(base_img: Image.Image, badge: dict, crystal: dict) -> list[Image.Image]:
  """
  Animated shimmering flux effect using a diagonal sweep beam, distortion ripple,
  prism shell and bloom. Used for the Omega Molecule crystal.
  """
  frame_size = (512, 512)
  fps = 12
  num_frames = 24
  band_width = int(128 * 0.8)
  max_displacement = 24
  beam_alpha = 12
  beam_color = (100, 180, 255, beam_alpha)
  blur_radius = 32

  base_img = base_img.resize(frame_size).convert("RGBA")
  width, height = frame_size

  def shimmer_flux_base(badge_img: Image.Image, frame_index: int) -> Image.Image:
    badge = badge_img.resize(frame_size)
    mask = badge.getchannel('A').point(lambda p: 255 if p > 0 else 0)

    pulse = 0.5 + 0.5 * np.sin(2 * np.pi * frame_index / num_frames)
    dilation = 4 + int(4 * pulse)
    blurred = mask.filter(ImageFilter.GaussianBlur(radius=dilation))

    red = Image.new("RGBA", frame_size, (255, 90, 90, 40))
    green = Image.new("RGBA", frame_size, (90, 255, 180, 40))
    blue = Image.new("RGBA", frame_size, (100, 140, 255, 40))

    red.putalpha(blurred)
    green.putalpha(blurred)
    blue.putalpha(blurred)

    red = ImageChops.offset(red, -1, 0)
    green = ImageChops.offset(green, 0, -1)
    blue = ImageChops.offset(blue, 1, 1)

    shell = Image.alpha_composite(Image.alpha_composite(red, green), blue)

    edge = mask.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(radius=2))
    bloom = Image.new("RGBA", frame_size, (140, 120, 255, int(60 + 40 * pulse)))
    bloom.putalpha(edge)

    glow = badge.filter(ImageFilter.GaussianBlur(radius=6 + 4 * pulse))
    glow = ImageEnhance.Brightness(glow).enhance(1.6 + pulse * 0.8)
    combined = Image.alpha_composite(glow, badge)
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

  frames = [shimmer_flux_frame(base_img, i) for i in range(num_frames)]
  return frames
