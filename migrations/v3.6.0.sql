-- Create "Echelon Veteran" badge metadata
INSERT INTO badge_info (
  badge_name, badge_filename, badge_url, quadrant, time_period, franchise, reference, special
)
VALUES (
  "Echelon Veteran",
  "Echelon_Veteran.png",
  "https://drunkshimoda.com/",
  "Alpha",
  "2100s",
  "The USS Hood",
  "Commemorating Legacy Levels Before The Echelon System!",
  1
)
AS new
ON DUPLICATE KEY UPDATE badge_name = new.badge_name;

-- Grant 'Echelon Veteran' badge instance to users who had legacy_level >= 2
INSERT INTO badge_instances (
  badge_info_id,
  owner_discord_id,
  origin_user_id,
  status
)
SELECT
  b.id AS badge_info_id,
  r.user_discord_id,
  r.user_discord_id,
  'active'
FROM legacy_xp_records r
JOIN badge_info b ON b.badge_filename = 'Echelon_Veteran.png'
WHERE r.legacy_level >= 2
  AND NOT EXISTS (
    SELECT 1 FROM badge_instances i
    WHERE i.owner_discord_id = r.user_discord_id
      AND i.badge_info_id = b.id
  );

-- Log these badge grants in badge_instance_history
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

-- Create "FOD Pride 2025" badge metadata
INSERT INTO badge_info (
  badge_name, badge_filename, badge_url, quadrant, time_period, franchise, reference, special
)
VALUES (
  "FOD Pride 2025",
  "FOD_Pride_2025.png",
  "https://drunkshimoda.com/",
  "Alpha",
  "2100s",
  "The USS Hood",
  "Commemorating Pride Month 2025 on The USS Hood!",
  1
)
AS new
ON DUPLICATE KEY UPDATE badge_name = new.badge_name;

-- Grant 'FOD Pride 2025' badge instance to users who have reached at least Level 1 in Echelon
INSERT INTO badge_instances (
  badge_info_id,
  owner_discord_id,
  origin_user_id,
  status
)
SELECT
  b.id AS badge_info_id,
  p.user_discord_id,
  p.user_discord_id,
  'active'
FROM echelon_progress p
JOIN badge_info b ON b.badge_filename = 'FOD_Pride_2025.png'
WHERE p.current_level >= 1
  AND NOT EXISTS (
    SELECT 1 FROM badge_instances i
    WHERE i.owner_discord_id = p.user_discord_id
      AND i.badge_info_id = b.id
  );

-- Log these badge grants in badge_instance_history
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

-- Create 'Unity Prism' crystal
INSERT INTO crystal_types (name, rarity_rank, icon, effect, description) VALUES
('Unity Prism', 4, 'unity_prism.png', 'rainbow_sheen', "A point of Pride! Emits gaydiation particles.");

-- Add 'admin' to the event_type enum in crystal_instance_history
ALTER TABLE crystal_instance_history
MODIFY COLUMN event_type ENUM(
  'replicated',
  'trade',
  'attuned',
  'admin'
) NOT NULL;

-- Grant 'Unity Prism' to all active users
-- First, resolve the crystal_type_id
SET @crystal_type_id = (
  SELECT id FROM crystal_types WHERE name = 'Unity Prism'
);

-- Insert into crystal_instances
INSERT INTO crystal_instances (
  crystal_type_id,
  owner_discord_id,
  status
)
SELECT
  @crystal_type_id,
  p.user_discord_id,
  'available'
FROM echelon_progress p
WHERE p.current_level >= 1
  AND NOT EXISTS (
    SELECT 1 FROM crystal_instances c
    WHERE c.owner_discord_id = p.user_discord_id
      AND c.crystal_type_id = @crystal_type_id
  );

-- Log the history for each inserted crystal
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
WHERE c.crystal_type_id = @crystal_type_id
  AND c.status = 'available'
  AND NOT EXISTS (
    SELECT 1 FROM crystal_instance_history h
    WHERE h.crystal_instance_id = c.id
      AND h.event_type = 'admin'
  );

-- Add auto-update date column for badge_instances for filtering
ALTER TABLE badge_instances
ADD COLUMN last_modified DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

-- Add date column to track when instance transfers occur
ALTER TABLE badge_instances
ADD COLUMN last_transferred DATETIME DEFAULT CURRENT_TIMESTAMP;

UPDATE badge_instances
SET last_transferred = acquired_at
WHERE last_transferred IS NOT NULL;

-- Add trigger to modify last_transferred when owner changes
CREATE TRIGGER trg_update_last_transferred_on_owner_change
BEFORE UPDATE ON badge_instances
FOR EACH ROW
  SET NEW.last_transferred = IF(
    NEW.owner_discord_id != OLD.owner_discord_id,
    CURRENT_TIMESTAMP,
    OLD.last_transferred
  );
