-- Tongo admin settings
CREATE TABLE IF NOT EXISTS tongo_settings (
  id INT PRIMARY KEY CHECK (id = 1),
  block_new_games BOOLEAN NOT NULL DEFAULT FALSE
);

-- Ensure a row always exists
INSERT INTO tongo_settings (id, block_new_games)
VALUES (1, FALSE)
ON DUPLICATE KEY UPDATE id = id;

-- Grant missing Echelon Veteran badge instances at all unlocked prestige tiers
INSERT INTO badge_instances (
  badge_info_id,
  owner_discord_id,
  origin_user_id,
  status,
  prestige_level
)
SELECT
  b.id,
  r.user_discord_id,
  r.user_discord_id,
  'active',
  p.prestige_level
FROM legacy_xp_records r
JOIN badge_info b ON b.badge_filename = 'Echelon_Veteran.png'
JOIN (
  SELECT 0 AS prestige_level UNION ALL
  SELECT 1 UNION ALL
  SELECT 2 UNION ALL
  SELECT 3 UNION ALL
  SELECT 4 UNION ALL
  SELECT 5 UNION ALL
  SELECT 6
) p
JOIN echelon_progress ep ON ep.user_discord_id = r.user_discord_id
WHERE r.legacy_level >= 2
  AND p.prestige_level <= ep.current_prestige_level
  AND NOT EXISTS (
    SELECT 1 FROM badge_instances i
    WHERE i.owner_discord_id = r.user_discord_id
      AND i.badge_info_id = b.id
      AND i.prestige_level = p.prestige_level
  );

-- Log instance history for newly created Echelon Veteran badges
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
JOIN badge_info b ON i.badge_info_id = b.id
WHERE b.badge_filename = 'Echelon_Veteran.png'
  AND NOT EXISTS (
    SELECT 1 FROM badge_instance_history h
    WHERE h.badge_instance_id = i.id
      AND h.event_type = 'epoch'
  );

-- Grant missing FOD Pride 2025 badge instances at all unlocked prestige tiers
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
JOIN badge_info b ON b.badge_filename = 'FOD_Pride_2025.png'
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
  AND p.prestige_level <= ep.current_prestige_level
  AND NOT EXISTS (
    SELECT 1 FROM badge_instances i
    WHERE i.owner_discord_id = ep.user_discord_id
      AND i.badge_info_id = b.id
      AND i.prestige_level = p.prestige_level
  );

-- Log instance history for newly created FOD Pride 2025 badges
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
JOIN badge_info b ON i.badge_info_id = b.id
WHERE b.badge_filename = 'FOD_Pride_2025.png'
  AND NOT EXISTS (
    SELECT 1 FROM badge_instance_history h
    WHERE h.badge_instance_id = i.id
      AND h.event_type = 'epoch'
  );
