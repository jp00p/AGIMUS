from pathlib import Path

from common import *

CRYSTAL_REPLICATOR_CACHE_DIR = ".cache/crystal_replicator_animations"

@to_thread
def load_cached_crystal_replicator_animation(cached_path):
  """
  Loads a cached repliactor animation from disk.

  If animated, returns a list of RGBA frames.
  """
  img = Image.open(cached_path)
  return [frame.copy().convert("RGBA") for frame in ImageSequence.Iterator(img)]

@to_thread
def save_cached_crystal_replicator_animation(buf: Image.Image | list[Image.Image], crystal_name):
  """
  Saves a Crystal Repliactor Animation to the cache.

  Saves as an animated webp.
  """
  path = construct_cached_crystal_replicator_animation_path(crystal_name)
  path.parent.mkdir(parents=True, exist_ok=True)

  with open(path, "wb") as f:
    f.write(buf.getvalue())

  return path

def construct_cached_crystal_replicator_animation_path(crystal_name) -> Path:
  """
  Constructs the full file path for a replicator animation cache entry.

  Example: .cache/crystal_replicator_animations/holomatrix_fragment__replicator_animation.webp
  """
  filename = f"{crystal_name}__replicator_animation.webp"
  return Path(CRYSTAL_REPLICATOR_CACHE_DIR) / filename

def get_cached_crystal_replicator_animation_path(crystal_name) -> Path | None:
  """
  Checks if a cached replicator animation image exists.

  Returns the path if found, otherwise None.
  """
  path = construct_cached_crystal_replicator_animation_path(crystal_name)
  return path if path.exists() else None
