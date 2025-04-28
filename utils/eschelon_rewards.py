# utils/eschelon_rewards.py
from common import *

from queries.badge_instances import db_get_badge_instance_by_id
from queries.crystal_instances import db_increment_user_crystal_buffer
from queries.eschelon_rewards import *
from queries.eschelon_xp import *
from utils.badge_instances import create_new_badge_instance

# Constants
PQIF_THRESHOLD = 0.10  # 10% remaining triggers PQIF

BASE_BUFFER_CHANCE = 20.0
BUFFER_GROWTH_FACTOR = 3.75
MAX_BUFFER_FAILURE_STREAK = 5

# TODO: Move this to `utils.prestige`
PRESTIGE_LEVELS = {
  0: 'Standard',
  1: 'Nebula',
  2: 'Galaxy',
  3: 'Supernova',
  4: 'Singularity',
  5: 'Nexus',
  6: 'Transcendence'
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

  This function is a simple executor of two-part level-up reward process:
    - Selects a badge to award using `select_badge_for_level_up()`, which prioritizes:
        - Missing badges at the user's current prestige level (highest weight)
        - Missing badges from lower prestige levels (backfill, with descending priority)
        - Badges from the next prestige level upward if the user is within PQIF (Prestige Quantum Improbability Field)
    - Ensures no duplicate badge instances are ever awarded.
    - Applies embargo penalties to lower prestige badges where applicable.
    - Always guarantees a badge is awarded on level-up.

  Once a badge_info_id and prestige_level are selected, it uses create_new_badge_instance() to:
    - Create a new badge instance in `badge_instances`
    - Record the acquisition event in `badge_instance_history`
    - Return the fully enriched badge instance dictionary

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
    3. If the user is within PQIF (Prestige Quantum Improbability Field), upward displacement into the next prestige tier is allowed with a dynamically increasing probability.
       - PQIF activates when the user has less than 10% missing badges remaining at their current prestige level.
       - The closer to 0% missing, the higher the chance of receiving a badge from the next prestige tier.
       - PQIF upward displacement never respects embargoes (users can receive clean higher-tier badges).
    4. Embargo penalties are applied to lower prestige missing badges to prevent farming:
       - If a user traded away a badge at a lower prestige, it enters a 30-day eschelon embargo.
       - During this time, the chance to re-earn that badge is reduced proportionally day-by-day until fully lifted.
       - Current prestige missing badges are not embargoed.
    5. If no non-embargoed badge can be awarded from current or lower prestiges, and PQIF is inactive or fails, a fallback upward leakover into the next prestige tier is enforced to ensure that a badge is always granted.
       - This should really never happen but might as well have something in a worst case scenario.

  The final selection is weighted:
    - Current prestige badges have the highest weight (e.g., 5).
    - Lower prestige badges have descending weights depending on how far back they are (e.g., Standard missing badge gets more weight than Nebula).
    - PQIF upward badges are weighted proportionally to how close the user is to completing their current prestige level.

  Args:
    user_discord_id (str): The Discord user ID of the member leveling up.

  Returns:
    tuple[int, int]:
      - badge_info_id (int): The ID of the selected badge to award.
      - prestige_level (int): The prestige level the awarded badge should be instantiated at.
  """
  prestige_level = await get_user_prestige_level(user_discord_id)
  full_pool = await db_get_full_badge_info_pool()

  candidates = []

  # Current prestige level badges
  user_collection = await db_get_user_badges_at_prestige_level(user_discord_id, prestige_level)
  missing_badges = list(set(full_pool) - user_collection)
  for badge_id in missing_badges:
    candidates.append((badge_id, prestige_level, 5))  # Standard weight

  # Lower prestige level badges
  for lower_prestige_level in range(0, prestige_level):
    lower_user_collection = await db_get_user_badges_at_prestige_level(user_discord_id, lower_prestige_level)
    lower_embargoed_badges = await db_get_user_embargoed_badges(user_discord_id, lower_prestige_level)
    lower_missing_badges = list(set(full_pool) - lower_user_collection)

    backfill_weight = 4 - lower_prestige_level if (4 - lower_prestige_level) > 1 else 1

    for badge_id in lower_missing_badges:
      if badge_id in lower_embargoed_badges:
        penalty = calculate_embargo_penalty(lower_embargoed_badges[badge_id])
        if random.random() > penalty:
          continue  # Skip due to embargo penalty
      candidates.append((badge_id, lower_prestige_level, backfill_weight))

  # PQIF upward displacement
  if await is_user_within_pqif(user_discord_id, prestige_level):
    upward_prestige_level = prestige_level + 1
    upper_user_collection = await db_get_user_badges_at_prestige_level(user_discord_id, upward_prestige_level)
    upper_missing_badges = list(set(full_pool) - upper_user_collection)

    # Recalculate missing percentage for current prestige
    missing_percentage = len(missing_badges) / max(len(full_pool), 1)
    upward_probability = 1.0 - (missing_percentage / PQIF_THRESHOLD)
    pqif_weight = max(1, int(5 + (5 * upward_probability)))  # Upward badges can outweigh current prestige badges

    for badge_id in upper_missing_badges:
      candidates.append((badge_id, upward_prestige_level, pqif_weight))

  if not candidates:
    raise Exception("No eligible badge candidates found. This should never happen (at least until the heat death of the universe and we've exhausted the Transcendence prestige level...")

  # Weighted random selection
  badge_choices = [item for item in candidates for _ in range(item[2])]
  selected_badge_id, selected_prestige_level, _ = random.choice(badge_choices)

  return selected_badge_id, selected_prestige_level

async def award_possible_crystal_buffer_pattern(user_discord_id: str) -> bool:
  """
  Attempt to grant a crystal buffer pattern to the user based on their buffer failure streak.

  Curve behavior:
    - Starts at a 20% chance to grant a crystal buffer on first level-up.
    - Each failure increases the buffer grant chance using a quadratic curve:
        `chance = 20% + (failure_streak^2 * 3.75)`
    - Failure streak increments by 1 after each unsuccessful attempt.
    - After 5 failures, the next attempt is a guaranteed 100% grant!

  If a buffer is granted, the failure streak resets to 0.
  If a buffer is not granted, the failure streak is incremented.

  Args:
    user_discord_id (str): The Discord user ID of the member leveling up.

  Returns:
    bool: True if a buffer was granted, False otherwise.
  """
  user_data = await db_get_eschelon_progress(user_discord_id)
  failure_streak = user_data.get('buffer_failure_streak', 0)

  # Calculate chance
  if failure_streak >= MAX_BUFFER_FAILURE_STREAK:
    chance = 100.0
  else:
    chance = min(100.0, BASE_BUFFER_CHANCE + (failure_streak ** 2) * BUFFER_GROWTH_FACTOR)

  roll = random.uniform(0, 100)

  if roll <= chance:
    # SUCCESS: Grant the crystal buffer pattern
    await db_increment_user_crystal_buffer(user_discord_id)
    await db_update_buffer_failure_streak(user_discord_id, 0)
    logger.debug(f"[Crystal Buffer Reward] User {user_discord_id} granted buffer (roll: {roll:.2f} <= {chance:.2f})")
    return True
  else:
    # FAIL: Increment failure streak
    await db_update_buffer_failure_streak(user_discord_id, failure_streak + 1)
    logger.debug(f"[Crystal Buffer Reward] User {user_discord_id} failed buffer (roll: {roll:.2f} > {chance:.2f}), new streak: {failure_streak + 1}")
    return False

#   ___ ___         .__
#  /   |   \   ____ |  | ______   ___________  ______
# /    ~    \_/ __ \|  | \____ \_/ __ \_  __ \/  ___/
# \    Y    /\  ___/|  |_|  |_> >  ___/|  | \/\___ \
#  \___|_  /  \___  >____/   __/ \___  >__|  /____  >
#        \/       \/     |__|        \/           \/
async def is_user_within_pqif(user_discord_id: str, prestige_level: int) -> bool:
  full_pool = await db_get_full_badge_info_pool()
  user_collection = await db_get_user_badges_at_prestige_level(user_discord_id, prestige_level)
  missing_badges = list(set(full_pool) - user_collection)
  missing_percentage = len(missing_badges) / max(len(full_pool), 1)
  return missing_percentage <= PQIF_THRESHOLD

async def get_user_prestige_level(user_discord_id: str) -> int:
  """
  Determines the user's effective prestige level based on badge ownership.
  Users are considered to have locked into a prestige level if they own at least 10% of the badge pool at that prestige.
  """
  full_pool = await db_get_full_badge_info_pool()

  # Start checking from highest prestige down
  for prestige_level in reversed(sorted(PRESTIGE_LEVELS.keys())):
    user_collection = await db_get_user_badges_at_prestige_level(user_discord_id, prestige_level)
    owned_percentage = len(user_collection) / max(len(full_pool), 1)

    if owned_percentage >= 0.10:
      return prestige_level

  # Fallback: if nothing else matches, Standard
  return 0

def calculate_embargo_penalty(traded_at: datetime) -> float:
  elapsed_days = (datetime.utcnow() - traded_at).days
  penalty = max(0.0, min(1.0, elapsed_days / EMBARGO_DAYS))
  return penalty

async def handle_eschelon_embargo_for_user(user_discord_id: str, badge_instance_ids: list[int]):
  """
  Clears expired embargoes for the user, and if the user is currently within PQIF,
  creates new embargoes for the badge instances they are actively trading away.

  Eschelon embargoes are a mechanic that makes badges harder to re-acquire via level up while in PQIF
  to prevent deliberate re-acquisition

  Args:
    user_discord_id (str): Discord user ID of the user making the trade.
    badge_instance_ids (list[int]): List of badge instance IDs being traded away.
  """
  await db_cleanup_expired_embargoes(user_discord_id)

  prestige_level = await get_user_prestige_level(user_discord_id)

  if await is_user_within_pqif(user_discord_id, prestige_level):
    for badge_instance_id in badge_instance_ids:
      badge_instance = await db_get_badge_instance_by_id(badge_instance_id)
      if badge_instance['prestige_level'] < prestige_level:
        await db_create_embargo_for_badge_instance(badge_instance_id)
