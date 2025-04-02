from common import *

from queries.badges import db_get_user_badges

async def get_user_badges_by_shiny_level(user_id: int, level: int = 0):
  badges = await db_get_user_badges(user_id)
  return [b for b in badges if b.get("shiny_level", 0) == level]