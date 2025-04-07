from PIL import Image, ImageFilter

# --- Entry Point ---

def apply_crystal_effect(badge_image: Image.Image, badge: dict, crystal: dict) -> Image.Image:
  """
  Applies a crystal's visual effect to a badge image.
  Args:
    badge_image: PIL Image of the badge
    badge: dict (currently unused, but may be helpful for future context-aware effects)
    crystal: dict with keys like:
      - 'effect': str (e.g. "blue_tint")
      - 'crystal_rarity_rank': int (1 = Common, ..., 5 = Mythic)
  """
  effect_key = crystal.get("effect")
  if not effect_key:
    return badge_image  # No effect specified

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
  return _apply_tint(img, (170, 170, 170), 0.6)  # Metallic gray

@register_effect("orange_tint")
def effect_orange_tint(img: Image.Image, badge: dict, crystal: dict) -> Image.Image:
  return _apply_tint(img, (255, 165, 90))  # Warm orange


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

