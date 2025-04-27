import math
from common import *

from queries.eschelon_xp import *

#   ______________________________
#  /  _____/\_   _____/\__    ___/_____
# /   \  ___ |    __)_   |    | /  ___/
# \    \_\  \|        \  |    | \___ \
#  \______  /_______  /  |____|/____  >
#         \/        \/              \/
async def get_user_eschelon_progress(user_discord_id: str) -> dict:
  """
  Retrieve the user's full eschelon_progress record.
  Intended for internal lookups and validation.
  """
  return await db_get_eschelon_progress(user_discord_id)

async def get_xp_summary(user_discord_id: str) -> dict:
  """
  Return a summary dictionary with user's level, XP into level, XP required to next level, and total XP.
  Useful for user-facing displays like profiles or progress bars.
  """
  progress = await db_get_eschelon_progress(user_discord_id)

  if not progress:
    return {
      "level": 1,
      "xp_into_level": 0,
      "xp_required": xp_required_for_level(1),
      "total_xp": 0
    }

  total_xp = progress['current_xp']
  level, xp_into_level, xp_required = xp_progress_within_level(total_xp)

  return {
    "level": level,
    "xp_into_level": xp_into_level,
    "xp_required": xp_required,
    "total_xp": total_xp
  }

# ____  _____________  _________
# \   \/  /\______   \ \_   ___ \ __ ____________  __ ____
#  \     /  |     ___/ /    \  \/|  |  \_  __ \  \/ // __ \
#  /     \  |    |     \     \___|  |  /|  | \/\   /\  ___/
# /___/\  \ |____|      \______  /____/ |__|    \_/  \___  >
#       \_/                    \/                        \/
def xp_required_for_level(level: int) -> int:
  """
  Calculate the amount of XP required to level up from the given level.
  Applies cubic ease-in/ease-out curve up to Level 170, then flat 420 XP per level.
  """
  if level <= 0:
    return 0
  if level > 170:
    return 420

  t = (level - 1) / (170 - 1)
  ease = 3 * (t**2) - 2 * (t**3)
  return int(69 + (420 - 69) * ease)

def level_for_total_xp(total_xp: int) -> int:
  """
  Calculate the amount of XP required to level up from the given level.
  Applies cubic ease-in/ease-out curve up to Level 170, then flat 420 XP per level.
  """
  xp = 0
  level = 1

  while True:
    needed = xp_required_for_level(level)
    if xp + needed > total_xp:
      break
    xp += needed
    level += 1

  return level

def xp_progress_within_level(total_xp: int) -> tuple[int, int, int]:
  """
  Returns the user's current level, how much XP they have into that level,
  and the XP required to reach the next level.
  Useful for progress bars and UI displays.
  """
  level = level_for_total_xp(total_xp)
  xp_at_level_start = sum(xp_required_for_level(lvl) for lvl in range(1, level))
  xp_into_level = total_xp - xp_at_level_start
  xp_required = xp_required_for_level(level)
  return level, xp_into_level, xp_required

def calculate_next_level_xp_gap(level: int) -> int:
  """
  Shortcut function to return how much XP is needed to level up from a given level.
  """
  return xp_required_for_level(level)

# ____  _____________     _____                           .___.__
# \   \/  /\______   \   /  _  \__  _  _______ _______  __| _/|__| ____    ____
#  \     /  |     ___/  /  /_\  \ \/ \/ /\__  \\_  __ \/ __ | |  |/    \  / ___\
#  /     \  |    |     /    |    \     /  / __ \|  | \/ /_/ | |  |   |  \/ /_/  >
# /___/\  \ |____|     \____|__  /\/\_/  (____  /__|  \____ | |__|___|  /\___  /
#       \_/                    \/             \/           \/         \//_____/
async def award_xp(user_discord_id: str, amount: int, reason: str):
  """
  Award XP to a user, check if they level up, update their record, and log the award.
  Main entry point for normal XP gain events.
  """
  current = await db_get_eschelon_progress(user_discord_id)

  if current:
    new_total_xp = current['current_xp'] + amount
  else:
    new_total_xp = amount

  new_level = level_for_total_xp(new_total_xp)

  await db_update_eschelon_progress(user_discord_id, new_total_xp, new_level)
  await db_insert_eschelon_history(user_discord_id, amount, new_level, reason)

async def bulk_award_xp(user_discord_ids: list[str], amount: int, reason: str):
  """
  Award XP to multiple users at once.
  Useful for mass event rewards or promotions.
  """
  for user_id in user_discord_ids:
    await award_xp(user_id, amount, reason)

async def deduct_xp(user_discord_id: str, amount: int, reason: str):
  """
  Deduct XP from a user.
  Mainly for admin corrections or penalties.
  """
  current = await db_get_eschelon_progress(user_discord_id)
  if not current:
    return

  new_total_xp = max(current['current_xp'] - amount, 0)
  new_level = level_for_total_xp(new_total_xp)

  await db_update_eschelon_progress(user_discord_id, new_total_xp, new_level)
  await db_insert_eschelon_history(user_discord_id, -amount, new_level, reason)

async def force_set_xp(user_discord_id: str, new_xp: int, reason: str):
  """
  Forcefully set a user's XP to a specific value.
  Only used by admins during emergency fixes or migrations.
  """
  new_level = level_for_total_xp(new_xp)

  await db_update_eschelon_progress(user_discord_id, new_xp, new_level)
  await db_insert_eschelon_history(user_discord_id, 0, new_level, reason)  # 0 xp gained, just admin override


