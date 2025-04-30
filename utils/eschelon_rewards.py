# utils/eschelon_rewards.py
from common import *

from queries.badge_instances import db_get_user_badge_instances
from queries.crystal_instances import db_increment_user_crystal_buffer, db_set_user_crystal_buffer
from queries.eschelon_rewards import *
from queries.eschelon_xp import *
from utils.badge_instances import create_new_badge_instance, create_new_badge_instance_by_filename

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
  Awards a new badge instance to a user upon leveling up, based on their current prestige level
  and the Eschelon badge reward logic.

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

  await update_user_prestige_level(member, prestige_level)

  return badge_instance

#   _________      .__                 __  .__                ___________              .__
#  /   _____/ ____ |  |   ____   _____/  |_|__| ____   ____   \_   _____/ ____    ____ |__| ____   ____
#  \_____  \_/ __ \|  | _/ __ \_/ ___\   __\  |/  _ \ /    \   |    __)_ /    \  / ___\|  |/    \_/ __ \
#  /        \  ___/|  |_\  ___/\  \___|  | |  (  <_> )   |  \  |        \   |  \/ /_/  >  |   |  \  ___/
# /_______  /\___  >____/\___  >\___  >__| |__|\____/|___|  / /_______  /___|  /\___  /|__|___|  /\___  >
#         \/     \/          \/     \/                    \/          \/     \//_____/         \/     \/
async def select_badge_for_level_up(member: discord.Member) -> tuple[int, int]:
  """
  Selects a badge to award during a level-up, factoring in prestige level, missing badges,
  and PQIF (Prestige Quantum Improbability Field) mechanics.

  The badge selection logic prioritizes badge pools using a weighted system:

  1. Badges from the user's current prestige level are given full weight by default.
  2. If the user has ≤10% missing badges at their current prestige level, PQIF activates:
     - PQIF introduces a probability curve that increasingly favors next-tier prestige badges
       the closer the user gets to full completion.
     - Badges from the next prestige level are awarded with rising probability.
     - Badges from the current prestige level decrease in probability accordingly.
  3. Badges from lower prestige tiers are always available as low-weighted backfill options.

  The function ensures:
  - A badge is always awarded.
  - No duplicates are granted.
  - Weighting smoothly transitions user upward via PQIF as they approach prestige boundaries.

  Args:
    user_discord_id (str): The Discord user ID of the leveler.

  Returns:
    tuple[int, int]: A tuple of (badge_info_id, prestige_level) to award.
  """
  user_discord_id = member.id
  prestige_level = await get_user_prestige_level(member)
  full_pool = await db_get_full_badge_info_pool()
  candidates = []

  current_collection = await db_get_user_badges_at_prestige_level(user_discord_id, prestige_level)
  current_missing_badges = list(set(full_pool) - current_collection)

  if await is_user_within_pqif(user_discord_id, prestige_level):
    current_missing_pct = len(current_missing_badges) / max(len(full_pool), 1)
    next_prestige_level = prestige_level + 1
    next_collection = await db_get_user_badges_at_prestige_level(user_discord_id, next_prestige_level)
    next_missing_badges = list(set(full_pool) - next_collection)

    next_weight = int((1.0 - current_missing_pct / PQIF_THRESHOLD) * 100)
    current_weight = 100 - next_weight

    for badge_id in current_missing_badges:
      candidates.append((badge_id, prestige_level, current_weight))
    for badge_id in next_missing_badges:
      candidates.append((badge_id, next_prestige_level, next_weight))
  else:
    for badge_id in current_missing_badges:
      candidates.append((badge_id, prestige_level, 100))

  for lower_prestige_level in range(0, prestige_level):
    lower_collection = await db_get_user_badges_at_prestige_level(user_discord_id, lower_prestige_level)
    lower_missing_badges = list(set(full_pool) - lower_collection)
    for badge_id in lower_missing_badges:
      candidates.append((badge_id, lower_prestige_level, 10))

  if not candidates:
    raise Exception("No eligible badge candidates found—unexpected scenario.")

  badge_choices = [item for item in candidates for _ in range(item[2])]
  selected_badge_id, selected_prestige_level, _ = random.choice(badge_choices)

  return selected_badge_id, selected_prestige_level

async def award_possible_crystal_buffer_pattern(member: discord.Member) -> bool:
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
    member (discord.Member): The Discord member leveling up.

  Returns:
    bool: True if a buffer was granted, False otherwise.
  """
  user_discord_id = member.id
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

  # Standard Friends of DeSoto Badge reward for joining
  fod_badge = await create_new_badge_instance_by_filename(user_id, "Friends_Of_DeSoto.png", event_type="first_promotion")
  # Give em N crystal buffers to play with
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
  Determines whether the user is currently within the Prestige Quantum Improbability Field (PQIF)
  for their current prestige boundary.

  PQIF represents a transitional state where the user is nearing full completion of their current
  prestige tier, causing badge rewards to probabilistically favor the next prestige level.

  Specifically, PQIF activates when the user has ≤10% missing badges from their current prestige
  pool. As they approach 100% completion, the chance of receiving next-tier badges increases
  smoothly.

  This function calculates the user's current missing badge percentage and returns True if PQIF
  should be considered active.

  Args:
    user (discord.User): The Discord User
    prestige_level (int): The current prestige level of the user.

  Returns:
    bool: True if the user is within PQIF range, otherwise False.
  """
  user_discord_id = user.id
  full_pool = await db_get_full_badge_info_pool()
  current_collection = await db_get_user_badges_at_prestige_level(user_discord_id, prestige_level)
  current_missing = len(set(full_pool) - current_collection)
  current_missing_pct = current_missing / max(len(full_pool), 1)
  return current_missing_pct <= PQIF_THRESHOLD


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
  current = await db_get_eschelon_progress(user_discord_id)
  return current.get('current_prestige_level', 0) if current else 0


async def update_user_prestige_level(member: discord.Member, new_prestige: int):
  """
  Permanently updates the user's prestige level in the database if the newly awarded prestige
  is higher than their current recorded prestige.

  Prestige level advancement is permanent and never decreases, even if lower-tier badges are
  lost or traded later.

  Args:
    member (discord.Member): The Discord Member whose ID to query.
    new_prestige (int): The prestige level to record if higher than current.
  """
  user_discord_id = member.id
  current = await db_get_eschelon_progress(user_discord_id)
  if current and new_prestige > current.get('current_prestige_level', 0):
    await db_set_user_prestige_level(user_discord_id, new_prestige)
