from common import *
from queries.badge_rewards import *
from queries.badge_info import *
from queries.badge_instances import *
from queries.crystals import *
from queries.wishlist import *


async def award_random_badge(user_id: int):
  """
  Awards a random badge the user doesn't already own and that isn't special.
  Handles wishlist autolock + purge.
  Returns the full badge instance dict, or None if no badge was awarded.
  """
  valid_badge_filenames = await db_get_valid_reward_filenames(user_id)
  if not valid_badge_filenames:
    return None

  badge_filename = random.choice(valid_badge_filenames)
  badge_instance = await db_create_badge_instance_if_missing(user_id, badge_filename)
  if badge_instance is None:
    return None

  # Auto-Lock wishlist
  user_wishlist = await db_get_user_wishlist_badges(user_id)
  wishlisted_filenames = [b['badge_filename'] for b in user_wishlist]
  if badge_filename in wishlisted_filenames:
    await db_autolock_badges_by_filenames_if_in_wishlist(user_id, [badge_filename])

  await db_purge_users_wishlist(user_id)
  return badge_instance


async def award_specific_badge(user_id: int, badge_filename: str):
  """
  Awards a specific badge by filename to the user.
  Handles wishlist autolock + purge.
  Returns the full badge instance dict, or None if the badge couldn't be awarded.
  """
  badge_instance = await db_create_badge_instance_if_missing(user_id, badge_filename)
  if badge_instance is None:
    return None

  # Auto-lock if it was on the wishlist
  user_wishlist = await db_get_user_wishlist_badges(user_id)
  wishlisted_filenames = [b['badge_filename'] for b in user_wishlist]
  if badge_filename in wishlisted_filenames:
    await db_autolock_badges_by_filenames_if_in_wishlist(user_id, [badge_filename])

  await db_purge_users_wishlist(user_id)
  return badge_instance


async def award_level_up_badge(user_id):
  """
  Awards a new badge instance and default crystal to the user as part of level-up flow.
  Logic prefers new, unowned standard badges with a weighted chance.

  Returns the full badge instance dict
  """

  all_badges = await db_get_all_badge_info()
  owned_badges = await db_get_user_badge_instances(user_id)

  all_badge_filenames = [b['badge_filename'] for b in all_badges]
  filename_to_badge_info = {b["badge_filename"]: b for b in all_badges}

  owned_badge_filenames = {b["badge_filename"] for b in all_badges if b["id"] in owned_badges}
  unowned_badge_filenames = [fn for fn in all_badge_filenames if fn not in owned_badge_filenames]

  if not unowned_badge_filenames:
    # If the user owns all badges, then we're going into 'crystallize' mode automatically
    selected_badge_filename = random.choice(list(owned_badge_filenames))
    mode = "crystallize"
  else:
    # Otherwise, we're going to heavily weigh towards granting the user a badge they don't already own
    if random.random() < 0.75:
      selected_badge_filename = random.choice(unowned_badge_filenames)
      mode = "grant"
    else:
      selected_badge_filename = random.choice(list(owned_badge_filenames))
      mode = "crystallize"

  badge_info = filename_to_badge_info.get(selected_badge_filename)
  if not badge_info:
    raise(f"Badge filename {selected_badge_filename} not found in badge_info")

  instance = None
  crystal = None

  if mode == "grant":
    instance = await db_create_badge_instance_if_missing(user_id, badge_info['id'])
    if instance is None:
      raise(f"User {user_id} already owns badge {selected_badge_filename} (race condition?)")
    crystal = await db_attach_crystal_to_instance(instance['id'], crystal_name="Dilithium")
    if crystal:
      await apply_autoslot_preference(user_id, instance['id'], crystal['id'])

  elif mode == "crystallize":
    instance = await db_get_badge_instance_by_badge_info_id(user_id, badge_info['id'])
    crystal = await crystallize_badge(user_id, instance['id'])

    if not crystal:
      # Fallback to any eligible badge instance
      crystal = await crystallize_random_owned_badge(user_id)

      if crystal:
        instance_row = await db_get_instance_by_attached_crystal_id(crystal['id'])
        if instance_row:
          instance = {'id': instance_row['badge_instance_id']}

    if crystal and instance:
      await apply_autoslot_preference(user_id, instance['id'], crystal['id'])

  return {
    "filename": selected_badge_filename,
    "badge_info": badge_info,
    "badge_instance": instance,
    "crystal": crystal,
    "mode": mode
  }


async def crystallize_badge(user_id: int, badge_instance_id: int, rarity_rank: int | None = None) -> dict | None:
  """
  Attempts to attach a new crystal to a badge instance.
  If rarity_rank is provided, tries only that tier.
  If not, rolls based on rarity drop weights and falls back down tiers.
  Returns the crystal dict if successful, or None if no eligible crystal could be attached.
  """
  if rarity_rank is not None:
    # Only attempt the given rarity
    crystals = await db_get_crystals_by_rarity(rarity_rank)
    random.shuffle(crystals)

    for crystal in crystals:
      already_attached = await db_check_crystal_attached(badge_instance_id, crystal['id'])
      if already_attached:
        continue

      success = await db_attach_crystal_to_instance(badge_instance_id, crystal['id'])
      if success:
        return crystal
    return None

  # No rarity passed in — roll using weights
  rarity_weights_data = await db_get_crystal_rarity_weights()
  if not rarity_weights_data:
    logger.warning("No rarity weights found in crystal_ranks table.")
    return None

  rarity_weights_data.sort(key=lambda r: r['rarity_rank'], reverse=True)
  rarities = [r['rarity_rank'] for r in rarity_weights_data]
  weights = [r['drop_chance'] for r in rarity_weights_data]

  selected_rarity = random.choices(rarities, weights=weights, k=1)[0]

  for rarity in range(selected_rarity, 0, -1):
    crystals = await db_get_crystals_by_rarity(rarity)
    random.shuffle(crystals)

    for crystal in crystals:
      already_attached = await db_check_crystal_attached(badge_instance_id, crystal['id'])
      if already_attached:
        continue

      success = await db_attach_crystal_to_instance(badge_instance_id, crystal['id'])
      if success:
        return crystal

  logger.info(f"User {user_id} received no crystal after fallback for badge instance {badge_instance_id}.")
  return None


async def crystallize_random_owned_badge(user_id: int) -> dict | None:
  """
  Iterates through user's badge instances in random order and attempts to crystallize each.
  Returns the first successful crystal awarded, or None if all fail.
  """
  badges = await db_get_user_badge_instances(user_id)
  if not badges:
    return None

  random.shuffle(badges)

  for badge in badges:
    instance_id = badge['badge_instance_id']
    crystal = await crystallize_badge(user_id, instance_id)
    if crystal:
      return crystal

  logger.info(f"User {user_id} has no eligible badge instances for crystallization.")
  return None


async def apply_autoslot_preference(user_id: int, badge_instance_id: int, new_crystal_id: int):
  """
  Applies user's auto-slot crystallization preference by either slotting the new crystal
  or leaving it unslotted based on their configured preference.
  """
  preference = await db_get_crystallize_autoslot_preference(user_id)

  if preference == 'manual':
    # User prefers manual selection; do nothing.
    return False

  if preference == 'auto_rarest':
    # Fetch all crystals for this badge and select the rarest
    all_crystals = await db_get_attached_crystals(badge_instance_id)
    rarest_crystal = await get_rarest_crystal(all_crystals)
    new_crystal = await db_get_crystal_by_id(new_crystal_id)
    if new_crystal['rarity_rank'] >= rarest_crystal['rarity_rank']:
      await db_set_active_crystal(badge_instance_id, new_crystal_id)
      return True
    else:
      return False

  if preference == 'auto_newest':
    # Automatically slot the newly obtained crystal
    await db_set_active_crystal(badge_instance_id, new_crystal_id)
    return True

  # Default fallback: do nothing
  return False
