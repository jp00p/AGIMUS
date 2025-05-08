# utils/echelon_rewards.py
from common import *

from queries.badge_instances import db_get_user_badge_instances
from queries.badge_info import db_get_all_badge_info
from queries.crystal_instances import db_increment_user_crystal_buffer, db_set_user_crystal_buffer
from queries.echelon_rewards import *
from queries.echelon_xp import *
from utils.badge_instances import create_new_badge_instance, create_new_badge_instance_by_filename, db_get_badge_instance_by_filename
from utils.prestige import PRESTIGE_TIERS

# Constants
PQIF_THRESHOLD = 0.10  # 10% remaining triggers PQIF

BASE_BUFFER_CHANCE = 20.0
BUFFER_GROWTH_FACTOR = 3.75
MAX_BUFFER_FAILURE_STREAK = 5

#    _____                           .___ __________             .___
#   /  _  \__  _  _______ _______  __| _/ \______   \_____     __| _/ ____   ____
#  /  /_\  \ \/ \/ /\__  \\_  __ \/ __ |   |    |  _/\__  \   / __ | / ___\_/ __ \
# /    |    \     /  / __ \|  | \/ /_/ |   |    |   \ / __ \_/ /_/ |/ /_/  >  ___/
# \____|__  /\/\_/  (____  /__|  \____ |   |______  /(____  /\____ |\___  / \___  >
#         \/             \/           \/          \/      \/      \/_____/      \/
async def award_level_up_badge(member) -> dict:
  """
  Awards a new badge instance to a user upon leveling up, based on their current prestige level
  and the Echelon badge reward logic.

  The function performs the following steps:
  - Determines which badge to award using `select_badge_for_level_up()`.
  - Instantiates a new badge via `create_new_badge_instance()`.
  - If the badge is from a higher prestige level than the user's current prestige level,
    updates the user's stored `prestige_level` to reflect permanent advancement.

  This function guarantees that exactly one new badge will be awarded for every level-up.

  Args:
    member (discord.Member): The user who leveled up.

  Returns:
    dict: The full badge instance record for the newly awarded badge.
  """
  badge_info_id, prestige_level = await select_badge_for_level_up(member)

  badge_instance = await create_new_badge_instance(
    user_id=member.id,
    badge_info_id=badge_info_id,
    prestige_level=prestige_level,
    event_type='level_up'
  )

  # Promote to new Prestige Tier if selected badge prestige is higher (via PQIF)
  current_prestige = await get_user_prestige_level(member)
  if prestige_level > current_prestige:
    await db_set_user_prestige_level(member.id, prestige_level)

  return badge_instance

#   _________      .__                 __  .__                ___________              .__
#  /   _____/ ____ |  |   ____   _____/  |_|__| ____   ____   \_   _____/ ____    ____ |__| ____   ____
#  \_____  \_/ __ \|  | _/ __ \_/ ___\   __\  |/  _ \ /    \   |    __)_ /    \  / ___\|  |/    \_/ __ \
#  /        \  ___/|  |_\  ___/\  \___|  | |  (  <_> )   |  \  |        \   |  \/ /_/  >  |   |  \  ___/
# /_______  /\___  >____/\___  >\___  >__| |__|\____/|___|  / /_______  /___|  /\___  /|__|___|  /\___  >
#         \/     \/          \/     \/                    \/          \/     \//_____/         \/     \/
async def select_badge_for_level_up(member: discord.Member) -> tuple[int, int]:
  """
  Selects a badge to award during a level-up, factoring in prestige tier progression,
  PQIF blending, and remaining badge pool sizes.

  This function determines the user's active PQIF base tier—the most complete, unfinished
  prestige tier—and calculates weighted selection probabilities between it and the next
  prestige tier if the user is within the PQIF threshold (10% missing or less).

  Weighting is determined by a capped cubic ease-out blend:
    - At 10% missing from Standard: ~90% Standard, ~10% Nebula
    - At 0% missing from Standard: ~10% Standard, ~90% Nebula
    - In between: weights interpolate smoothly using ease-out
    - Actual weights are then scaled by the pool sizes to maintain selection fairness

  Backfill candidates from tiers below the user's permanent prestige level are also included,
  at a static low weight (10).

  Returns:
    tuple[int, int]: A tuple of (badge_info_id, prestige_level) representing the badge to award.
  """
  user_discord_id = member.id
  current_prestige = await get_user_prestige_level(member)
  all_badges = await db_get_all_badge_info()
  full_badge_ids = {b['id'] for b in all_badges}

  async def get_owned_ids_at_prestige(level: int) -> set[int]:
    instances = await db_get_user_badge_instances(user_discord_id, prestige=level)
    return {b['badge_info_id'] for b in instances}

  active_pqif_base = current_prestige
  for tier in range(current_prestige + 1):
    owned = await get_owned_ids_at_prestige(tier)
    if len(owned) < len(full_badge_ids):
      active_pqif_base = tier
      break

  candidates = []
  base_owned = await get_owned_ids_at_prestige(active_pqif_base)
  base_missing = list(full_badge_ids - base_owned)
  base_missing_pct = len(base_missing) / max(len(full_badge_ids), 1)

  logger.info(f"[echelon] PQIF Base Prestige {active_pqif_base} – missing {len(base_missing)} / {len(full_badge_ids)}")

  next_prestige = active_pqif_base + 1
  next_owned = await get_owned_ids_at_prestige(next_prestige)
  next_missing = list(full_badge_ids - next_owned)

  if base_missing_pct <= PQIF_THRESHOLD:
    # Ease-out cubic interpolation
    t = 1 - (base_missing_pct / PQIF_THRESHOLD)
    ease = 1 - (1 - t) ** 3

    base_pool_size = len(base_missing)
    next_pool_size = len(next_missing)
    total_pool = base_pool_size + next_pool_size or 1

    # Base weight from curve, scaled by pool sizes and capped
    base_weight = max(10, int((1 - ease) * (base_pool_size / total_pool) * 100))
    next_weight = min(90, int(ease * (next_pool_size / total_pool) * 100))

    logger.info(f"[pqif] Active – {base_weight}% prestige {active_pqif_base} / {next_weight}% prestige {next_prestige}")

    candidates.extend((bid, active_pqif_base, base_weight) for bid in base_missing)
    candidates.extend((bid, next_prestige, next_weight) for bid in next_missing)

  else:
    logger.info(f"[pqif] Inactive – awarding from prestige {active_pqif_base} only")
    candidates.extend((bid, active_pqif_base, 100) for bid in base_missing)

  if current_prestige > 0:
    for lower in range(0, current_prestige):
      lower_owned = await get_owned_ids_at_prestige(lower)
      lower_missing = list(full_badge_ids - lower_owned)
      logger.debug(f"[backfill] Prestige {lower} – missing {len(lower_missing)}")
      candidates.extend((bid, lower, 10) for bid in lower_missing)
  else:
    logger.info("[backfill] Skipped – user is at Standard prestige")

  if not candidates:
    logger.warning(f"[echelon] No eligible badge candidates for user {user_discord_id} at prestige {current_prestige}")
    raise Exception("No eligible badge candidates found—unexpected scenario.")

  weighted = [item for item in candidates for _ in range(item[2])]
  selected_id, selected_prestige, _ = random.choice(weighted)

  logger.info(f"[selection] Selected badge_id={selected_id} at prestige={selected_prestige}")
  return selected_id, selected_prestige


async def award_possible_crystal_pattern_buffer(member: discord.Member) -> bool:
  """
  Attempt to grant a crystal pattern buffer to the user based on their buffer failure streak.

  Curve behavior:
    - Starts at a 20% chance to grant a crystal buffer on first level-up.
    - Each failure increases the buffer grant chance using a quadratic curve:
        `chance = 20% + (failure_streak^2 * 3.75)`
    - Failure streak increments by 1 after each unsuccessful attempt.
    - After 5 failures, the next attempt is a guaranteed 100% grant!

  If a buffer is granted, the failure streak resets to 0.
  If a buffer is not granted, the failure streak is incremented.

  Args:
    member (discord.Member): The Discord member leveling up.

  Returns:
    bool: True if a buffer was granted, False otherwise.
  """
  user_discord_id = member.id
  user_data = await db_get_echelon_progress(user_discord_id)
  failure_streak = user_data.get('buffer_failure_streak', 0)

  # Calculate chance
  if failure_streak >= MAX_BUFFER_FAILURE_STREAK:
    chance = 100.0
  else:
    chance = min(100.0, BASE_BUFFER_CHANCE + (failure_streak ** 2) * BUFFER_GROWTH_FACTOR)

  roll = random.uniform(0, 100)

  if roll <= chance:
    # SUCCESS: Grant the crystal pattern buffer
    await db_increment_user_crystal_buffer(user_discord_id)
    await db_update_buffer_failure_streak(user_discord_id, 0)
    logger.debug(f"[Crystal Buffer Reward] User {user_discord_id} granted buffer (roll: {roll:.2f} <= {chance:.2f})")
    # Currently they win a single buffer, maybe we'll change this in the future or maybe not
    return 1
  else:
    # FAIL: Increment failure streak
    await db_update_buffer_failure_streak(user_discord_id, failure_streak + 1)
    logger.debug(f"[Crystal Buffer Reward] User {user_discord_id} failed buffer (roll: {roll:.2f} > {chance:.2f}), new streak: {failure_streak + 1}")
    return False

# __________                                .___
# \______   \ ______  _  _______ _______  __| _/______
#  |       _// __ \ \/ \/ /\__  \\_  __ \/ __ |/  ___/
#  |    |   \  ___/\     /  / __ \|  | \/ /_/ |\___ \
#  |____|_  /\___  >\/\_/  (____  /__|  \____ /____  >
#         \/     \/             \/           \/    \/
async def award_initial_welcome_package(member: discord.Member):
  user_id = member.id

  # Check if user already owns the FoD badge
  existing = await db_get_badge_instance_by_filename(user_id, "Friends_Of_DeSoto.png", prestige=0)
  if existing:
    fod_badge = None  # Already owned
  else:
    fod_badge = await create_new_badge_instance_by_filename(user_id, "Friends_Of_DeSoto.png", prestige_level=0, event_type="epoch")

  # Grant initial crystal pattern buffers
  number_of_buffers_awarded = 3
  await db_set_user_crystal_buffer(user_id, number_of_buffers_awarded)

  return fod_badge, number_of_buffers_awarded

async def award_special_badge_prestige_echoes(member: discord.Member, prestige_level: int) -> list[dict]:
  """
  Awards prestige-level echoes of special badges the user already owns when advancing
  to a new prestige tier. Skips duplicates.

  Args:
    member (user.Member): The Discord Member.
    prestige_level (int): The new prestige level the user just reached.

  Returns:
    list[dict]: List of new badge_instance records created.
  """
  user_id = member.id
  # Get all special badges the user owns at any prestige
  special_badges = await db_get_user_badge_instances(user_id, special=True)
  owned_badge_ids = {b['badge_info_id'] for b in special_badges}

  # Get the subset they already own at this prestige level
  already_has_at_this_prestige = {
    b['badge_info_id']
    for b in await db_get_user_badge_instances(user_id, special=True, prestige=prestige_level)
  }

  new_instances = []

  for badge_info_id in owned_badge_ids:
    if badge_info_id in already_has_at_this_prestige:
      continue
    instance = await create_new_badge_instance(
      user_id=user_id,
      badge_info_id=badge_info_id,
      prestige_level=prestige_level,
      event_type='prestige_echo'
    )
    new_instances.append(instance)

  return new_instances


#   ___ ___         .__
#  /   |   \   ____ |  | ______   ___________  ______
# /    ~    \_/ __ \|  | \____ \_/ __ \_  __ \/  ___/
# \    Y    /\  ___/|  |_|  |_> >  ___/|  | \/\___ \
#  \___|_  /  \___  >____/   __/ \___  >__|  /____  >
#        \/       \/     |__|        \/           \/
async def is_user_within_pqif(user: discord.User, prestige_level: int) -> bool:
  """
  Returns True if the user is in the PQIF fuzzy transition zone between prestige tiers.

  PQIF is defined as active when BOTH of the following are true:
    - User has ≤ 10% missing from their current prestige level (i.e., >= 90% completion).
    - User has received < 10% of the total pool at the next prestige level.

  This creates a "blurred" handoff between prestige tiers where selection favors upward drift.

  Args:
    user (discord.User): The Discord user.
    prestige_level (int): The user's current recorded prestige level.

  Returns:
    bool: True if user is in the PQIF transition zone.
  """
  user_id = user.id
  full_pool = await db_get_full_badge_info_pool()
  total_count = len(full_pool)

  current_owned = await db_get_user_badges_at_prestige_level(user_id, prestige_level)
  next_owned = await db_get_user_badges_at_prestige_level(user_id, prestige_level + 1)

  current_pct = len(current_owned) / total_count
  next_pct = len(next_owned) / total_count

  return (current_pct >= 0.90) and (next_pct <= 0.10)


async def get_user_prestige_level(member: discord.Member) -> int:
  """
  Retrieves the user's current prestige level, which is permanently set based on the highest-tier
  badge they have received.

  Prestige level only increases and never regresses, even if lower-tier badges are traded away.

  Args:
    member (discord.Member): The Discord Member whose ID to query.

  Returns:
    int: The user's highest prestige level achieved (default is 0).
  """
  user_discord_id = member.id
  current = await db_get_echelon_progress(user_discord_id)
  return current.get('current_prestige_tier', 0) if current else 0
