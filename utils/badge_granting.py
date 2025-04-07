from common import *
from queries.badge_info import db_get_badge_info_by_filename
from queries.badge_instances import (
  db_insert_badge_instance_if_missing,
  db_attach_crystal_to_instance,
  db_set_preferred_crystal
)


async def grant_level_up_badge_award(user, source_details):
  """
  Awards a new badge instance and default crystal to the user as part of level-up flow.

  Returns a badge object with filename and metadata to be used in the embed.
  """
  # Placeholder logic — replace with actual badge selection algorithm
  badge_filename = "example_badge.png"

  badge_info = await db_get_badge_info_by_filename(badge_filename)
  if not badge_info:
    logger.warning(f"Badge filename {badge_filename} not found in badge_info")
    return None

  instance = await db_insert_badge_instance_if_missing(user.id, badge_info["id"])
  if instance is None:
    logger.info(f"User {user.id} already owns badge {badge_filename}")
    return None

  crystal_id = await db_attach_crystal_to_instance(instance["id"], crystal_name="Dilithium")
  if crystal_id is not None:
    await db_set_preferred_crystal(instance["id"], crystal_id)

  return {
    "filename": badge_filename,
    "badge_info_id": badge_info["id"],
    "badge_instance_id": instance["id"],
    "crystal_id": crystal_id,
    "user_id": user.id
  }
