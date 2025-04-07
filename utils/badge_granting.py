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
    if random.random() < 0.85:
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
    if crystal is not None:
      await db_set_preferred_crystal(instance['id'], crystal['id'])
  elif mode == "crystallize":
    # Otherwise, let's attach a fresh randomized crystal to it!
    instance = await db_get_badge_instance(user_id, badge_info['id'])
    await crystallize_badge(user_id)

  return {
    "filename": selected_badge_filename,
    "badge_info": badge_info,
    "badge_instance": instance,
    "crystal": crystal,
    "mode": mode
  }


async def crystallize_badge(user_id: int, instance_id: int):
  """
  Attempts to attach a new crystal to the given badge_instance,
  avoiding any duplicate crystal_type_ids.
  Weights selection based on drop_chance from crystal_ranks.
  """
  existing = await db_get_existing_crystals_for_instance(instance_id)
  existing_type_ids = {c['crystal_type_id'] for c in existing}

  available_types = await db_get_available_crystal_types()
  valid_choices = [c for c in available_types if c['id'] not in existing_type_ids]

  if not valid_choices:
    logger.info(f"User {user_id}'s badge_instance {instance_id} already has all crystals.")
    return None

  weights = [c['drop_chance'] for c in valid_choices]
  chosen = random.choices(valid_choices, weights=weights, k=1)[0]
  crystal = await db_attach_crystal_to_instance(instance_id, crystal_name=chosen['name'])

  return crystal