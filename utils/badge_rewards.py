# utils/badge_rewards.py
from common import *

from queries.badge_rewards import *
from utils.badge_instances import create_new_badge_instance

# Constants
PQIF_THRESHOLD = 0.10  # 10% remaining triggers PQIF

# TODO: Move this to `utils.prestige`
PRESTIGE_LEVELS = {
  0: 'Standard',
  1: 'Nebula',
  2: 'Galaxy',
  3: 'Supernova',
  4: 'Singularity',
  5: 'Continuum',
}

#    _____                           .___ __________             .___
#   /  _  \__  _  _______ _______  __| _/ \______   \_____     __| _/ ____   ____
#  /  /_\  \ \/ \/ /\__  \\_  __ \/ __ |   |    |  _/\__  \   / __ | / ___\_/ __ \
# /    |    \     /  / __ \|  | \/ /_/ |   |    |   \ / __ \_/ /_/ |/ /_/  >  ___/
# \____|__  /\/\_/  (____  /__|  \____ |   |______  /(____  /\____ |\___  / \___  >
#         \/             \/           \/          \/      \/      \/_____/      \/
async def award_level_up_badge(member) -> dict:
  """
  Awards a new badge instance to a user upon level-up, following Prestige system rules.

  This function orchestrates the full level-up reward process:
    - Selects a badge to award using `select_badge_for_level_up()`, which prioritizes:
        - Missing badges at the user's current prestige level (highest weight),
        - Missing badges from lower prestige levels (backfill, with descending priority),
        - Badges from the next prestige level upward if the user is within PQIF (Prestige Quantum Improbability Field),
    - Ensures no duplicate badge instances are ever awarded.
    - Applies embargo penalties to lower prestige badges where applicable.
    - Always guarantees a badge is awarded on level-up.

  Once a badge_info_id and prestige_level are selected, it uses utils.badge_instance's create_new_badge_instance() to:
    - Create a new badge instance in `badge_instances`,
    - Record the acquisition event in `badge_instance_history`,
    - Return the fully enriched badge instance dictionary.

  Args:
    member (discord.Member): The Discord member object representing the user leveling up.

  Returns:
    dict: The complete badge instance data for the newly awarded badge, ready for display or follow-up processing.
  """
  badge_info_id, prestige_level = await select_badge_for_level_up(member.id)

  badge_instance = await create_new_badge_instance(
    user_id=member.id,
    badge_info_id=badge_info_id,
    prestige_level=prestige_level,
    event_type='level_up'
  )

  return badge_instance

#   _________      .__                 __  .__                ___________              .__
#  /   _____/ ____ |  |   ____   _____/  |_|__| ____   ____   \_   _____/ ____    ____ |__| ____   ____
#  \_____  \_/ __ \|  | _/ __ \_/ ___\   __\  |/  _ \ /    \   |    __)_ /    \  / ___\|  |/    \_/ __ \
#  /        \  ___/|  |_\  ___/\  \___|  | |  (  <_> )   |  \  |        \   |  \/ /_/  >  |   |  \  ___/
# /_______  /\___  >____/\___  >\___  >__| |__|\____/|___|  / /_______  /___|  /\___  /|__|___|  /\___  >
#         \/     \/          \/     \/                    \/          \/     \//_____/         \/     \/
async def select_badge_for_level_up(user_discord_id: str) -> tuple[int, int]:
  """
  Selects a badge_info_id and prestige_level to award when a user levels up, following the Eschelon Prestige Badge System rules.

  This function orchestrates the badge selection process, ensuring that:
    - No duplicate badge instances are ever awarded.
    - Badge awarding respects prestige progression, missing badges, and embargo penalties.
    - Every level-up results in a badge reward.

  Badge selection logic operates in the following priority order:
    1. Missing badges at the user's current prestige level are favored most heavily.
    2. Missing badges from lower prestige levels (Standard, Nebula, Galaxy, etc.) are backfilled with gradually decreasing probability as prestige level rises.
       - The lower the prestige, the higher the backfill priority (Standard > Nebula > Galaxy > ...).
       - This ensures that older missing badges have a better chance of being filled naturally over time.
    3. If the user is within PQIF (Prestige Quantum Improbability Field), upward leakover into the next prestige tier is allowed with a dynamically increasing probability.
       - PQIF activates when the user has less than 10% missing badges remaining at their current prestige level.
       - The closer to 0% missing, the higher the chance of receiving a badge from the next prestige tier.
       - PQIF upward leakover never respects embargoes (users can receive clean higher-tier badges).
    4. Embargo penalties are applied to lower prestige missing badges to prevent farming:
       - If a user traded away a badge at a lower prestige, it enters a 30-day embargo.
       - During this time, the chance to re-earn that badge is reduced proportionally day-by-day until fully lifted.
       - Current prestige missing badges are not embargoed.
    5. If no non-embargoed badge can be awarded from current or lower prestiges, and PQIF is inactive or fails, a fallback upward leakover into the next prestige tier is enforced to ensure that a badge is always granted.
       - This should really never happen but might as well have something in a worst case scenario.

  The final selection is weighted:
    - Current prestige badges have the highest weight (e.g., 5).
    - Lower prestige badges have descending weights depending on how far back they are (e.g., Standard missing badge gets more weight than Nebula).
    - PQIF upward badges are weighted equally to current prestige badges.

  Args:
    user_discord_id (str): The Discord user ID of the member leveling up.

  Returns:
    tuple[int, int]:
      - badge_info_id (int): The ID of the selected badge to award.
      - prestige_level (int): The prestige level the awarded badge should be instantiated at.
  """
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


#   ___ ___         .__
#  /   |   \   ____ |  | ______   ___________  ______
# /    ~    \_/ __ \|  | \____ \_/ __ \_  __ \/  ___/
# \    Y    /\  ___/|  |_|  |_> >  ___/|  | \/\___ \
#  \___|_  /  \___  >____/   __/ \___  >__|  /____  >
#        \/       \/     |__|        \/           \/
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
