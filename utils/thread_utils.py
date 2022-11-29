import asyncio
import functools

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

