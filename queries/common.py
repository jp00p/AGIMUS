# queries/common.py

BADGE_INSTANCE_COLUMNS = """
  b_i.id AS badge_info_id,
  b_i.badge_filename,
  b_i.badge_name,
  b_i.badge_url,
  b_i.quadrant,
  b_i.time_period,
  b_i.franchise,
  b_i.reference,
  b_i.special,

  b.id AS badge_instance_id,
  b.badge_info_id,
  b.owner_discord_id,
  b.prestige_level,
  b.locked,
  b.origin_user_id,
  b.acquired_at,
  b.active_crystal_id,
  b.status,
  b.active,

  c.id AS badge_crystal_id,

  ci.id AS crystal_instance_id,
  ci.status AS crystal_status,
  ci.created_at AS crystal_created_at,

  t.id AS crystal_type_id,
  t.name AS crystal_name,
  t.icon AS crystal_icon,
  t.effect as crystal_effect,
  t.rarity_rank as crystal_rarity_rank
"""