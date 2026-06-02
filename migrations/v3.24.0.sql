-- Create "Founders' Bucket" badge metadata
INSERT INTO badge_info (
  badge_name,
  badge_filename,
  badge_url,
  quadrant,
  time_period,
  franchise,
  reference,
  special
)
VALUES (
  "Founders' Bucket",
  "Founders_Bucket.png",
  "https://greatesttrek.com/",
  "Alpha",
  "2100s",
  "The USS Hood",
  "We don't use the bucket anymore!",
  1
)
AS new
ON DUPLICATE KEY UPDATE
  badge_name = new.badge_name,
  badge_url = new.badge_url,
  quadrant = new.quadrant,
  time_period = new.time_period,
  franchise = new.franchise,
  reference = new.reference,
  special = new.special;

-- Create "FOD Pride 2026" badge metadata
INSERT INTO badge_info (
  badge_name,
  badge_filename,
  badge_url,
  quadrant,
  time_period,
  franchise,
  reference,
  special
)
VALUES (
  "FOD Pride 2026",
  "FOD_Pride_2026.png",
  "https://drunkshimoda.com/",
  "Alpha",
  "2100s",
  "The USS Hood",
  "Commemorating Pride Month 2026 on The USS Hood!",
  1
)
AS new
ON DUPLICATE KEY UPDATE
  badge_name = new.badge_name,
  badge_url = new.badge_url,
  quadrant = new.quadrant,
  time_period = new.time_period,
  franchise = new.franchise,
  reference = new.reference,
  special = new.special;

-- Grant FOD Pride 2026 badge instances at all unlocked prestige tiers
INSERT INTO badge_instances (
  badge_info_id,
  owner_discord_id,
  origin_user_id,
  status,
  prestige_level
)
SELECT
  b.id,
  ep.user_discord_id,
  ep.user_discord_id,
  'active',
  p.prestige_level
FROM echelon_progress ep
JOIN badge_info b
  ON b.badge_filename = 'FOD_Pride_2026.png'
JOIN (
  SELECT 0 AS prestige_level UNION ALL
  SELECT 1 UNION ALL
  SELECT 2 UNION ALL
  SELECT 3 UNION ALL
  SELECT 4 UNION ALL
  SELECT 5 UNION ALL
  SELECT 6
) p
WHERE ep.current_level >= 1
  AND p.prestige_level <= ep.current_prestige_tier
  AND NOT EXISTS (
    SELECT 1
    FROM badge_instances i
    WHERE i.owner_discord_id = ep.user_discord_id
      AND i.badge_info_id = b.id
      AND i.prestige_level = p.prestige_level
      AND i.status = 'active'
  );

-- Log epoch history for active FOD Pride 2026 badge instances missing epoch history
INSERT INTO badge_instance_history (
  badge_instance_id,
  from_user_id,
  to_user_id,
  event_type
)
SELECT
  i.id,
  NULL,
  i.owner_discord_id,
  'epoch'
FROM badge_instances i
JOIN badge_info b
  ON i.badge_info_id = b.id
WHERE b.badge_filename = 'FOD_Pride_2026.png'
  AND i.status = 'active'
  AND NOT EXISTS (
    SELECT 1
    FROM badge_instance_history h
    WHERE h.badge_instance_id = i.id
      AND h.event_type = 'epoch'
  );

-- Grant one new available "Unity Prism" crystal to every active user
INSERT INTO crystal_instances (
  crystal_type_id,
  owner_discord_id,
  status
)
SELECT
  ct.id,
  ep.user_discord_id,
  'available'
FROM echelon_progress ep
JOIN crystal_types ct
  ON ct.name = 'Unity Prism'
WHERE ep.current_level >= 1;

-- Log admin history for available Unity Prism crystal instances missing admin history
INSERT INTO crystal_instance_history (
  crystal_instance_id,
  event_type,
  to_user_id
)
SELECT
  c.id,
  'admin',
  c.owner_discord_id
FROM crystal_instances c
JOIN crystal_types ct
  ON c.crystal_type_id = ct.id
WHERE ct.name = 'Unity Prism'
  AND c.status = 'available'
  AND NOT EXISTS (
    SELECT 1
    FROM crystal_instance_history h
    WHERE h.crystal_instance_id = c.id
      AND h.event_type = 'admin'
  );