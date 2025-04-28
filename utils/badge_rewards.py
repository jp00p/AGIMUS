# utils/badge_rewards.py
from common import *

from queries.badge_rewards import *

# Constants
PQIF_THRESHOLD = 0.10  # 10% remaining triggers PQIF

PRESTIGE_LEVELS = {
  0: 'Standard',
  1: 'Nebula',
  2: 'Galaxy',
  3: 'Supernova',
  4: 'Singularity',
  5: 'Continuum',
}

# --- Helpers ---
def calculate_embargo_penalty(traded_at: datetime) -> float:
  elapsed_days = (datetime.utcnow() - traded_at).days
  penalty = max(0.0, min(1.0, elapsed_days / EMBARGO_DAYS))
  return penalty

async def is_user_within_pqif(user_discord_id: str, prestige_level: int) -> bool:
  full_pool = await db_get_full_badge_info_pool()
  user_collection = await db_get_user_badges_at_prestige_level(user_discord_id, prestige_level)
  missing_badges = list(set(full_pool) - user_collection)
  missing_percentage = len(missing_badges) / max(len(full_pool), 1)
  return missing_percentage <= PQIF_THRESHOLD

# --- Main Selection Engine ---

async def select_badge_for_level_up(user_discord_id: str) -> tuple[int, int]:
  prestige_level = await db_get_user_prestige_level(user_discord_id)
  selected_prestige_level = prestige_level
  full_pool = await db_get_full_badge_info_pool()
  user_collection = await db_get_user_badges_at_prestige_level(user_discord_id, prestige_level)
  embargoed_badges = await db_get_user_embargoed_badges(user_discord_id, prestige_level)

  # Determine missing badges
  missing_badges = list(set(full_pool) - user_collection)
  missing_percentage = len(missing_badges) / max(len(full_pool), 1)

  eligible_badges = missing_badges

  if await is_user_within_pqif(user_discord_id, prestige_level):
    # PQIF Activation
    lower_prestige_level = max(prestige_level - 1, 0)
    lower_user_collection = await db_get_user_badges_at_prestige_level(user_discord_id, lower_prestige_level)
    lower_embargoed_badges = await db_get_user_embargoed_badges(user_discord_id, lower_prestige_level)
    lower_missing_badges = list(set(full_pool) - lower_user_collection)

    upward_prestige_level = prestige_level + 1
    upper_user_collection = await db_get_user_badges_at_prestige_level(user_discord_id, upward_prestige_level)
    upper_missing_badges = list(set(full_pool) - upper_user_collection)

    upward_probability = 1.0 - (missing_percentage / PQIF_THRESHOLD)

    if random.random() < upward_probability and upper_missing_badges:
      eligible_badges = upper_missing_badges
      embargoed_badges = {}  # No embargoes when leaking upward
      selected_prestige_level = upward_prestige_level
    elif lower_missing_badges:
      eligible_badges = lower_missing_badges
      embargoed_badges = lower_embargoed_badges
      selected_prestige_level = lower_prestige_level

  # Apply embargo penalties
  weighted_candidates = []
  for badge_id in eligible_badges:
    if badge_id in embargoed_badges:
      penalty = calculate_embargo_penalty(embargoed_badges[badge_id])
      if random.random() > penalty:
        continue  # Skip due to penalty
    weighted_candidates.append(badge_id)

  if not weighted_candidates:
    # No eligible badges, fallback to full pool
    weighted_candidates = full_pool

  selected_badge = random.choice(weighted_candidates)
  return selected_badge, selected_prestige_level

# --- Awarding Entry Point ---

async def award_level_up_badge(member) -> dict:
  """
  Entry point for awarding a level-up badge.
  Selects a badge, creates an instance, returns enriched badge instance data.
  """
  badge_info_id, prestige_level = await select_badge_for_level_up(member.id)

  # TODO: Actually create a badge instance here and enrich the return data.
  # For now, return a stub.

  return {
    'badge_info_id': badge_info_id,
    'prestige_level': prestige_level,
    'awarded_to': member.id,
    'awarded_at': datetime.utcnow(),
  }
