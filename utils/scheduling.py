from discord.ext import tasks
from functools import wraps

def delayed_task_loop(*, seconds:int = 0, count:int = 1):
  """
  Decorator that turns an async method into a discord.ext.tasks.loop(count=1),
  automatically bound to the cog instance.
  """
  def wrapper(func):
    @wraps(func)
    def bound_loop(cog):
      @tasks.loop(seconds=seconds, count=count)
      async def task_wrapper():
        await func(cog)

      return task_wrapper

    return bound_loop
  return wrapper