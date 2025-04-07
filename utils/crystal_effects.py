from PIL import Image

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

@register_effect("blue_tint")
def effect_blue_tint(img: Image.Image, badge: dict, crystal: dict) -> Image.Image:
  return _apply_tint(img, (102, 204, 255))  # Soft blue

@register_effect("steel_tint")
def effect_steel_tint(img: Image.Image, badge: dict, crystal: dict) -> Image.Image:
  return _apply_tint(img, (170, 170, 170))  # Metallic gray

@register_effect("orange_tint")
def effect_orange_tint(img: Image.Image, badge: dict, crystal: dict) -> Image.Image:
  return _apply_tint(img, (255, 165, 90))  # Warm orange

def _apply_tint(base_img: Image.Image, color: tuple[int, int, int], opacity: float = 0.25) -> Image.Image:
  overlay = Image.new("RGBA", base_img.size, color + (int(255 * opacity),))
  return Image.alpha_composite(base_img.convert("RGBA"), overlay)
