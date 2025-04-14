-- v3.0.0.sql - Badge Instances Refactor

-- We're gonna start using an id column on badge_info for the new tables going forward
-- But eventually we'll go back and update all the tables and queries to use this id
-- badge_info's primary key, but this refactor is massive enough as-is and
-- I just don't want to deal with all of that shit right now... whee

-- Add ID column for badge_info without breaking foreign key constraints
ALTER TABLE badge_info
  ADD COLUMN id INT AUTO_INCREMENT UNIQUE FIRST;

-- v3.0.0.sql - Crystallization Schema

-- CRYSTALS!

-- 1. Crystal Ranks
CREATE TABLE crystal_ranks (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(64) NOT NULL UNIQUE,
  emoji VARCHAR(16),
  rarity_rank INT NOT NULL,
  drop_chance FLOAT NOT NULL,
  sort_order INT DEFAULT 0
);

INSERT INTO crystal_ranks (name, emoji, rarity_rank, drop_chance, sort_order) VALUES
  ("Common",    "⚪", 1, 0.64, 0),
  ("Uncommon",  "🟢", 2, 0.20, 1),
  ("Rare",      "🟣", 3, 0.10, 2),
  ("Legendary", "🔥", 4, 0.075, 3),
  ("Mythic",    "💎", 5, 0.05, 4);

-- 2. Crystal Types
CREATE TABLE crystal_types (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(64) NOT NULL UNIQUE,
  rarity_rank INT NOT NULL,
  icon VARCHAR(128),
  effect TEXT,
  description TEXT
);

INSERT INTO crystal_types (name, rarity_rank, icon, effect, description) VALUES

  -- Common Crystals
  ("Dilithium", 1, "dilithium.png", "pink_tint", "Good old Dilithium. Standard Starfleet issue!"),
  ("Deuterium", 1, "deuterium.png", "blue_tint", "Refined for warp cores. Imparts a subtle blue glow."),
  ("Tritanium", 1, "tritanium.png", "steel_tint", "Strong and dependable. Hull-grade enhancement."),
  ("Baryon", 1, "baryon.png", "orange_tint", "Sterile and slightly warm. Still glowing a bit."),
  ("Cormaline", 1, "cormaline.png", "purple_tint", "Ferenginar gemstone. Often gifted during dubious business deals."),
  ("Tellurium", 1, "tellurium.png", "greenmint_tint", "Essential for biosensor arrays. Slightly toxic when aerosolized, don't breathe this!"),

  -- Uncommon Crystals
  ("Isolinear", 2, "isolinear.png", "isolinear", "Shimoda's favorite plaything. Fully stackable!"),
  ("Optical", 2, "optical.png", "optical", "Optical data strands. Utilized by LCARS display terminals."),
  ("Positron", 2, "positron.png", "positronic", "Fully functional. Operates at 60 trillion calculations a second."),
  ("Latinum", 2, "latinum.png", "latinum", "Get that, get that, Gold Pressed Latinum!"),
  ("Cryonetrium", 2, "cryonetrium.png", "cryonetrium", "Still gaseous at -200°C, that's some cold coolant!"),

  -- Rare Crystals
  ("Trilithium", 3, "trilithium.png", "trilithium_banger", "Volatile compound banned in three quadrants. Handle with care."),
  ("Tholian Silk", 3, "tholian_silk.png", "tholian_web", "A crystallized thread of energy - elegant, fractical, and deadly."),
  ("Holomatrix Fragment", 3, "holomatrix_fragment.png", "holo_grid", "Hologrammatical. Rendered with an uncanny simulated depth."),
  ("Silicon Shard", 3, "silicon_shard.png", "crystalline_entity", "Sharp and pointy, a beautiful Entity. Crystalline as FUCK!"),

  -- Legendary Crystals
  ("Warp Plasma Cell", 4, "warp_plasma.png", "warp_pulse", "EJECTED FROM A CORE! Hums with that familiar pulse."),
  ("Tetryon", 4, "tetryon.png", "subspace_ripple", "A particle intrinsic to subspace. Distortions abound when these are around!"),
  ("Bajoran Orb", 4, "bajoran_orb.png", "prophet_glow", "An Tear of the Prophets. My Child!"),

  -- Mythic Crystals
  ("Chroniton", 5, "chroniton.png", "phase_flicker", "Time travel! Glitches in and out of this temporal frame."),
  ("Omega Molecule", 5, "omega.png", "shimmer_flux", "The perfect form of matter. Dangerous, beautiful, and rarely stable.");

-- 3. Badge Crystals (must come before badge_instances)
CREATE TABLE badge_crystals (
  id INT AUTO_INCREMENT PRIMARY KEY,
  badge_instance_id INT NOT NULL,
  crystal_type_id INT NOT NULL,
  granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (crystal_type_id) REFERENCES crystal_types(id)
);

-- 4. Badge Instances (safe now!)
CREATE TABLE badge_instances (
  id INT AUTO_INCREMENT PRIMARY KEY,
  badge_info_id INT NOT NULL,
  owner_discord_id BIGINT NULL,
  locked BOOLEAN DEFAULT FALSE,
  origin_user_id BIGINT NOT NULL,
  acquired_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  active_crystal_id INT DEFAULT NULL,
  status ENUM('active', 'scrapped', 'liquidated', 'archived') NOT NULL DEFAULT 'active',
  UNIQUE KEY (owner_discord_id, badge_info_id),
  FOREIGN KEY (badge_info_id) REFERENCES badge_info(id),
  FOREIGN KEY (active_crystal_id) REFERENCES badge_crystals(id) ON DELETE SET NULL
);

-- 5. Instance Provenance
CREATE TABLE badge_instance_history (
  id INT AUTO_INCREMENT PRIMARY KEY,
  badge_instance_id INT NOT NULL,
  from_user_id BIGINT DEFAULT NULL,
  to_user_id BIGINT NULL,
  occurred_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  event_type ENUM(
    'epoch',
    'level_up',
    'trade',
    'tongo_risk',
    'tongo_reward',
    'liquidation',
    'liquidation_endowment',
    'admin',
    'unknown'
  ) NOT NULL DEFAULT 'unknown',
  FOREIGN KEY (badge_instance_id) REFERENCES badge_instances(id),
  INDEX idx_history_instance_id (badge_instance_id)
);

-- 6. Crystal Trades
CREATE TABLE crystal_trades (
  id INT AUTO_INCREMENT PRIMARY KEY,
  crystal_id INT NOT NULL,
  from_badge_instance_id INT NOT NULL,
  to_badge_instance_id INT NOT NULL,
  from_user_id BIGINT NOT NULL,
  to_user_id BIGINT NOT NULL,
  transferred_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (crystal_id) REFERENCES badge_crystals(id),
  FOREIGN KEY (from_badge_instance_id) REFERENCES badge_instances(id),
  FOREIGN KEY (to_badge_instance_id) REFERENCES badge_instances(id)
);

-- 7. Add FK to badge_crystals after both tables exist
ALTER TABLE badge_crystals
  ADD CONSTRAINT fk_badge_crystals_instance
  FOREIGN KEY (badge_instance_id) REFERENCES badge_instances(id) ON DELETE CASCADE;


-- New autoslot setting
ALTER TABLE users ADD COLUMN crystallize_autoslot ENUM('manual', 'auto_rarest', 'auto_newest') DEFAULT 'manual';

--
-- TONGO v2
--

CREATE TABLE tongo_games (
  id INT AUTO_INCREMENT PRIMARY KEY,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  chair_user_id BIGINT NOT NULL,
  status ENUM('open', 'in_progress', 'resolved', 'cancelled') DEFAULT 'open'
);

CREATE TABLE tongo_game_players (
  game_id INT,
  user_discord_id BIGINT,
  liability_mode ENUM('unlocked', 'all_in') NOT NULL,
  joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (game_id, user_discord_id),
  FOREIGN KEY (game_id) REFERENCES tongo_games(id)
);

CREATE TABLE tongo_continuum (
  badge_info_id INT PRIMARY KEY,
  source_instance_id INT,
  thrown_by_user_id BIGINT,
  added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (badge_info_id) REFERENCES badge_info(id),
  FOREIGN KEY (source_instance_id) REFERENCES badge_instances(id)
);

CREATE TABLE tongo_game_rewards (
  game_id INT,
  user_discord_id BIGINT,
  badge_instance_id INT,
  crystal_id INT DEFAULT NULL,
  rewarded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (game_id, user_discord_id, badge_instance_id),
  FOREIGN KEY (game_id) REFERENCES tongo_games(id),
  FOREIGN KEY (badge_instance_id) REFERENCES badge_instances(id),
  FOREIGN KEY (crystal_id) REFERENCES crystal_types(id)
);

--
-- Wishlists
--

-- Note that we don't reference specific badge_instances here,
-- users are essentially wishlisting "badge_info"s, but we're naming it
-- `badge_instance_wishlists` because we're migrating from the old
-- `badge_wishlists` table and want to make this clear this is the new table
-- also the results of these wishlists will be badge instances so ¯\_(ツ)_/¯
CREATE TABLE badge_instance_wishlists (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  user_discord_id VARCHAR(64) NOT NULL,
  badge_info_id INT NOT NULL,
  time_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY unique_user_badge (user_discord_id, badge_info_id),
  FOREIGN KEY (user_discord_id) REFERENCES users(discord_id) ON DELETE CASCADE,
  FOREIGN KEY (badge_info_id) REFERENCES badge_info(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS badge_instance_wishlist_dismissals (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  user_discord_id VARCHAR(64) NOT NULL,
  match_discord_id VARCHAR(64) NOT NULL,
  has JSON NOT NULL,
  wants JSON NOT NULL,
  time_created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY unique_dismissal (user_discord_id, match_discord_id),
  FOREIGN KEY (user_discord_id) REFERENCES users(discord_id) ON DELETE CASCADE,
  FOREIGN KEY (match_discord_id) REFERENCES users(discord_id) ON DELETE CASCADE
);

--
-- Badge Tags Migration
--

-- === STEP 1: BACKUP EXISTING ASSOCIATIONS TO TEMP TABLE ===
CREATE TABLE badge_tags_associations_backup AS
SELECT
  t_a.badge_tags_id,
  b.user_discord_id,
  b.badge_filename
FROM badge_tags_associations t_a
JOIN badges b ON t_a.badges_id = b.id;

-- === STEP 2: DROP OLD FOREIGN KEY AND COLUMN ===
ALTER TABLE badge_tags_associations
  DROP FOREIGN KEY badge_tags_associations_ibfk_1;

ALTER TABLE badge_tags_associations
  DROP COLUMN badges_id;

-- === STEP 3: ADD NEW INSTANCE-BASED COLUMN ===
ALTER TABLE badge_tags_associations
  ADD COLUMN badge_instance_id INT NOT NULL;

-- === STEP 4: REPOPULATE badge_instance_id USING BACKUP DATA ===
UPDATE badge_tags_associations t_a
JOIN badge_tags_associations_backup bkp
  ON t_a.badge_tags_id = bkp.badge_tags_id
JOIN badge_info info
  ON info.badge_filename = bkp.badge_filename
JOIN badge_instances inst
  ON inst.badge_info_id = info.id AND inst.owner_discord_id = bkp.user_discord_id
SET t_a.badge_instance_id = inst.id;

-- === STEP 5: RE-ESTABLISH FOREIGN KEY ===
ALTER TABLE badge_tags_associations
  ADD CONSTRAINT fk_tags_instance
    FOREIGN KEY (badge_instance_id) REFERENCES badge_instances(id)
    ON DELETE CASCADE;

-- === STEP 6: CLEANUP TEMP TABLE ===
DROP TABLE badge_tags_associations_backup;

-- Now for the carousel positions...

-- === STEP 1: Back up the current table ===
CREATE TABLE tags_carousel_position_backup AS
SELECT id, user_discord_id, badge_filename, last_modified
FROM tags_carousel_position;

-- === STEP 2: Drop the old table ===
DROP TABLE tags_carousel_position;

-- === STEP 3: Recreate with new structure based on badge_instance_id ===
CREATE TABLE tags_carousel_position (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_discord_id VARCHAR(64) NOT NULL,
  badge_instance_id INT NOT NULL,
  last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_user (user_discord_id),
  UNIQUE KEY uq_user_instance (user_discord_id, badge_instance_id),
  KEY idx_instance (badge_instance_id),
  CONSTRAINT fk_carousel_instance
    FOREIGN KEY (badge_instance_id)
    REFERENCES badge_instances(id)
    ON DELETE CASCADE
);

-- === STEP 4: Restore data using badge_filename → badge_info.id → badge_instances.id ===
INSERT INTO tags_carousel_position (user_discord_id, badge_instance_id, last_modified)
SELECT
  bkp.user_discord_id,
  inst.id AS badge_instance_id,
  bkp.last_modified
FROM tags_carousel_position_backup bkp
JOIN badge_info info ON info.badge_filename = bkp.badge_filename
JOIN badge_instances inst ON inst.badge_info_id = info.id
WHERE inst.owner_discord_id = bkp.user_discord_id
  AND inst.status = 'active';

-- === STEP 5: Drop the backup table ===
DROP TABLE tags_carousel_position_backup;
