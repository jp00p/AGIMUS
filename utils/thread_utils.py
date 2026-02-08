import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
import os
import threading

from PIL import Image

# ___________.__                              .___.__
# \__    ___/|  |_________   ____ _____     __| _/|__| ____    ____
#   |    |   |  |  \_  __ \_/ __ \\__  \   / __ | |  |/    \  / ___\
#   |    |   |   Y  \  | \/\  ___/ / __ \_/ /_/ | |  |   |  \/ /_/  >
#   |____|   |___|  /__|    \___  >____  /\____ | |__|___|  /\___  /
#                 \/            \/     \/      \/         \//_____/
def to_thread(func):
  @functools.wraps(func)
  async def wrapper(*args, **kwargs):
    loop = asyncio.get_event_loop()
    wrapped = functools.partial(func, *args, **kwargs)
    return await loop.run_in_executor(None, wrapped)
  return wrapper

# Threaded image loads (Prevents Blocking)
@to_thread
def threaded_image_open(path: str) -> Image.Image:
  return Image.open(path).convert("RGBA")

@to_thread
def threaded_image_open_no_convert(path: str) -> Image.Image:
  return Image.open(path)

@to_thread
def threaded_image_open_resized(path: str, size: tuple[int, int]) -> Image.Image:
  return Image.open(path).convert("RGBA").resize(size, Image.LANCZOS)

# Image-thread helper
# Use a dedicated executor for PIL/OpenCV heavy work to keep the event loop responsive.
_IMAGE_THREAD_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix='img')

async def to_thread_image(func, /, *args, **kwargs):
  """Run an image-heavy callable in a dedicated thread pool."""
  loop = asyncio.get_running_loop()
  return await loop.run_in_executor(_IMAGE_THREAD_POOL, functools.partial(func, *args, **kwargs))
