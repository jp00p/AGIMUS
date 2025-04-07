from common import *
from queries.badge_info import *
from queries.badge_inventory import *
from queries.crystals import *


async def award_level_up_badge(user_id):
  """
  Awards a new badge instance and default crystal to the user as part of level-up flow.
  Logic prefers new, unowned standard badges with a weighted chance.

  Returns a badge object with filename and metadata to be used in the embed.
  """

  all_badges = await db_get_all_badge_info()
  owned_badges = await db_get_user_badges(user_id)

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
    # But, there's a 15% chance we will grant them a crystal instead
    else:
      selected_badge_filename = random.choice(list(owned_badge_filenames))
      mode = "crystallize"

  badge_info = filename_to_badge_info.get(selected_badge_filename)
  if not badge_info:
    raise(f"Badge filename {selected_badge_filename} not found in badge_info")

  if mode == "grant":
    # If we're granting a badge, create the instance and attach the default crystal to it
    instance = await db_create_badge_instance_if_missing(user_id, badge_info['id'])
    if instance is None:
      raise(f"User {user_id} already owns badge {selected_badge_filename} (race condition?)")
    crystal = await db_attach_crystal_to_instance(instance['id'], crystal_name="Dilithium")
    # TODO: Commented out below, we actaully shouldn't be setting the default as the slotted crystal
    # before checking with the user's auto-slot preferences
    #
    # if crystal is not None:
    #   await db_set_slotted_crystal(instance['id'], crystal['id'])
  elif mode == "crystallize":
    # Otherwise, let's attach a fresh randomized crystal to it!
    instance = await db_get_badge_instance(user_id, badge_info['id'])
    crystal = await crystallize_badge(user_id, instance['id'])
    # TODO: Check the user's auto-slot preferences here and either slot it in or not

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
  badges = await db_get_user_badges(user_id)
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