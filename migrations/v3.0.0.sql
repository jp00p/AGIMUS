-- v3.0.0.sql - Badge Instances Refactor

--
-- Badge Info, transition to using id as primary everywhere
--

-- Drop foreign keys that depend on badge_filename
ALTER TABLE badge_affiliation DROP FOREIGN KEY badge_affiliation_fk_badge_filename;
ALTER TABLE badge_type DROP FOREIGN KEY badge_type_fk_badge_filename;
ALTER TABLE badge_universe DROP FOREIGN KEY badge_universe_fk_badge_filename;
ALTER TABLE badge_scraps DROP FOREIGN KEY badge_scraps_fk_badge_filename;
ALTER TABLE trade_offered DROP FOREIGN KEY trade_offered_ibfk_1;
ALTER TABLE trade_requested DROP FOREIGN KEY trade_requested_ibfk_1;
ALTER TABLE badge_scrapped DROP FOREIGN KEY badge_scrapped_ibfk_2;
ALTER TABLE badge_wishlists DROP FOREIGN KEY badge_wishlists_fk_badge_filename;
ALTER TABLE tongo_pot DROP FOREIGN KEY badge_tongo_pot_fk_badge_filename;
ALTER TABLE tags_carousel_position DROP FOREIGN KEY badge_tags_carousel_position_fk_badge_filename;

-- Drop primary key on badge_filename
ALTER TABLE badge_info DROP PRIMARY KEY;

-- Add id column and promote it to primary key
ALTER TABLE badge_info
  ADD COLUMN id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY FIRST;

-- Make badge_filename a UNIQUE column instead
ALTER TABLE badge_info
  ADD UNIQUE KEY uq_badge_filename (badge_filename);

-- Re-add foreign keys (still using badge_filename)
ALTER TABLE badge_affiliation
  ADD CONSTRAINT badge_affiliation_fk_badge_filename
  FOREIGN KEY (badge_filename) REFERENCES badge_info (badge_filename);

ALTER TABLE badge_type
  ADD CONSTRAINT badge_type_fk_badge_filename
  FOREIGN KEY (badge_filename) REFERENCES badge_info (badge_filename);

ALTER TABLE badge_universe
  ADD CONSTRAINT badge_universe_fk_badge_filename
  FOREIGN KEY (badge_filename) REFERENCES badge_info (badge_filename);

ALTER TABLE badge_scraps
  ADD CONSTRAINT badge_scraps_fk_badge_filename
  FOREIGN KEY (badge_filename) REFERENCES badge_info (badge_filename);

ALTER TABLE trade_offered
  ADD CONSTRAINT trade_offered_ibfk_1
  FOREIGN KEY (badge_filename) REFERENCES badge_info (badge_filename);

ALTER TABLE trade_requested
  ADD CONSTRAINT trade_requested_ibfk_1
  FOREIGN KEY (badge_filename) REFERENCES badge_info (badge_filename);

ALTER TABLE badge_scrapped
  ADD CONSTRAINT badge_scrapped_ibfk_2
  FOREIGN KEY (badge_filename) REFERENCES badge_info (badge_filename);

ALTER TABLE badge_wishlists
  ADD CONSTRAINT badge_wishlists_fk_badge_filename
  FOREIGN KEY (badge_filename) REFERENCES badge_info (badge_filename);

ALTER TABLE tongo_pot
  ADD CONSTRAINT badge_tongo_pot_fk_badge_filename
  FOREIGN KEY (badge_filename) REFERENCES badge_info (badge_filename);

ALTER TABLE tags_carousel_position
  ADD CONSTRAINT badge_tags_carousel_position_fk_badge_filename
  FOREIGN KEY (badge_filename) REFERENCES badge_info (badge_filename);

-- v3.0.0.sql - Crystallization Schema

-- CRYSTALS!

-- 1. Crystal Ranks
CREATE TABLE IF NOT EXISTS crystal_ranks (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(64) NOT NULL UNIQUE,
  emoji VARCHAR(16),
  rarity_rank INT NOT NULL,
  drop_chance FLOAT NOT NULL,
  sort_order INT DEFAULT 0
);

INSERT INTO crystal_ranks (name, emoji, rarity_rank, drop_chance, sort_order) VALUES
  ("Common",    "⚪", 1, 0.50, 0),
  ("Uncommon",  "🟢", 2, 0.30, 1),
  ("Rare",      "🟣", 3, 0.125, 2),
  ("Legendary", "🔥", 4, 0.075, 3),
  ("Mythic",    "💎", 5, 0.05, 4);

-- 2. Crystal Types
CREATE TABLE IF NOT EXISTS crystal_types (
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

  ("Rubindium", 1, "rubindium.png", "crimson_gradient", "Sensor-reflective alloy with multiple applications. Chief among them, frikkin laser beams."),
  ("Polytrinic", 1, "polytrinic.png", "lime_gradient", "Toxic and corrosive. Glows green, that means bad!"),
  ("Benamite", 1, "benamite.png", "navy_gradient", "Essential for quantum slipstream drives. Sadly unstable, you lose yet again Voyager!"),
  ("Auridium", 1, "auridium.png", "gold_gradient", "Trade-standard alloy with a golden gleam. Shiny!"),
  ("Duranium", 1, "duranium.png", "silver_gradient", "Forged in Federation shipyards. A silvery alloy used in starship hull plating."),
  ("Solanogen", 1, "solanogen.png", "cyan_gradient", "Exotic compound from subspace realms. Don't get SCHISMD!"),
  ("Pergium", 1, "pergium.png", "amber_gradient", "Highly prized radiothermal ore. Still glows warm from its mining days."),

  ("Latinum", 1, "latinum.png", "latinum", "Get that, get that, Gold Pressed Latinum!"),

  -- Uncommon Crystals
  ("Isolinear", 2, "isolinear.png", "isolinear", "Shimoda's favorite plaything. Fully stackable!"),
  ("Optical", 2, "optical.png", "optical", "Optical data strands. Utilized by LCARS display terminals."),
  ("Positron", 2, "positron.png", "positronic", "Fully functional. Operates at 60 trillion calculations a second."),
  ("Cryonetrium", 2, "cryonetrium.png", "cryonetrium", "Still gaseous at -200°C, that's some cold coolant!"),

  -- Rare Crystals
  ("Trilithium", 3, "trilithium.png", "trilithium_banger", "Volatile compound banned in three quadrants. Handle with care."),
  ("Tholian Silk", 3, "tholian_silk.png", "tholian_web", "A crystallized thread of energy - elegant, fractical, and deadly."),
  ("Holomatrix Fragment", 3, "holomatrix_fragment.png", "holo_grid", "Hologrammatical. Rendered with an uncanny simulated depth."),
  ("Silicon Shard", 3, "silicon_shard.png", "crystalline_entity", "Sharp and pointy, a beautiful Entity. Crystalline as FUCK!"),

  -- Legendary Crystals
  ("Warp Plasma Cell", 4, "warp_plasma.png", "warp_pulse", "EJECTED FROM A CORE! Hums with that familiar pulse."),
  ("Tetryon", 4, "tetryon.png", "subspace_ripple", "A particle intrinsic to subspace. Distortions abound when these are around!"),

  -- Mythic Crystals
  ("Bajoran Orb", 5, "bajoran_orb.png", "wormhole_opening", "Tear of the Prophets. My Child!"),
  ("Chroniton", 5, "chroniton.png", "phase_flicker", "Time travel! Glitches in and out of this temporal frame."),
  ("Omega Molecule", 5, "omega.png", "shimmer_flux", "The perfect form of matter. Dangerous, beautiful, and rarely stable.");

-- 3. Badge Crystals (must come before badge_instances)
CREATE TABLE IF NOT EXISTS badge_crystals (
  id INT AUTO_INCREMENT PRIMARY KEY,
  badge_instance_id INT NOT NULL,
  crystal_type_id INT NOT NULL,
  granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (crystal_type_id) REFERENCES crystal_types(id)
);

-- 4. Badge Instances (safe now!)
CREATE TABLE IF NOT EXISTS badge_instances (
  id INT AUTO_INCREMENT PRIMARY KEY,
  badge_info_id INT UNSIGNED NOT NULL,
  owner_discord_id BIGINT NULL,
  locked BOOLEAN DEFAULT FALSE,
  active BOOLEAN GENERATED ALWAYS AS (status = 'active') STORED,
  origin_user_id BIGINT NOT NULL,
  acquired_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  active_crystal_id INT DEFAULT NULL,
  status ENUM('active', 'scrapped', 'liquidated', 'archived') NOT NULL DEFAULT 'active',

  UNIQUE KEY uq_user_badge_active (owner_discord_id, badge_info_id, active),
  FOREIGN KEY (badge_info_id) REFERENCES badge_info(id),
  FOREIGN KEY (active_crystal_id) REFERENCES badge_crystals(id) ON DELETE SET NULL
);


-- 5. Instance Provenance
CREATE TABLE IF NOT EXISTS badge_instance_history (
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
CREATE TABLE IF NOT EXISTS crystal_trades (
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

CREATE TABLE IF NOT EXISTS tongo_games (
  id INT AUTO_INCREMENT PRIMARY KEY,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  chair_user_id BIGINT NOT NULL,
  status ENUM('open', 'in_progress', 'resolved', 'cancelled') DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS tongo_game_players (
  game_id INT,
  user_discord_id BIGINT,
  liability_mode ENUM('unlocked', 'all_in') NOT NULL,
  joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (game_id, user_discord_id),
  FOREIGN KEY (game_id) REFERENCES tongo_games(id)
);

CREATE TABLE IF NOT EXISTS tongo_continuum (
  badge_info_id INT UNSIGNED PRIMARY KEY,
  source_instance_id INT,
  thrown_by_user_id BIGINT,
  added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (badge_info_id) REFERENCES badge_info(id),
  FOREIGN KEY (source_instance_id) REFERENCES badge_instances(id)
);

CREATE TABLE IF NOT EXISTS tongo_game_rewards (
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

CREATE TABLE IF NOT EXISTS badge_instance_wishlists (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  user_discord_id VARCHAR(64) NOT NULL,
  badge_info_id INT UNSIGNED NOT NULL,
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

CREATE TABLE IF NOT EXISTS badge_instances_tags_associations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  badge_instance_id INT NOT NULL,
  badge_tags_id INT NOT NULL,
  time_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (badge_instance_id) REFERENCES badge_instances(id) ON DELETE CASCADE,
  FOREIGN KEY (badge_tags_id) REFERENCES badge_tags(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS badge_instances_tags_carousel_position (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_discord_id VARCHAR(64) NOT NULL,
  badge_instance_id INT NOT NULL,
  last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_user (user_discord_id),
  UNIQUE KEY uq_user_instance (user_discord_id, badge_instance_id),
  FOREIGN KEY (badge_instance_id) REFERENCES badge_instances(id) ON DELETE CASCADE,
  FOREIGN KEY (user_discord_id) REFERENCES users(discord_id) ON DELETE CASCADE
);

--
-- Trades
--

CREATE TABLE IF NOT EXISTS instance_trades (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  requestor_id    BIGINT NOT NULL,
  requestee_id    BIGINT NOT NULL,
  status          ENUM('pending', 'active', 'complete', 'declined', 'canceled') NOT NULL DEFAULT 'pending',
  time_created    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trade_offered_instances (
  id                INT AUTO_INCREMENT PRIMARY KEY,
  trade_id          INT NOT NULL,
  badge_instance_id INT NOT NULL,
  FOREIGN KEY (trade_id) REFERENCES instance_trades(id) ON DELETE CASCADE,
  FOREIGN KEY (badge_instance_id) REFERENCES badge_instances(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS trade_requested_instances (
  id                INT AUTO_INCREMENT PRIMARY KEY,
  trade_id          INT NOT NULL,
  badge_instance_id INT NOT NULL,
  FOREIGN KEY (trade_id) REFERENCES instance_trades(id) ON DELETE CASCADE,
  FOREIGN KEY (badge_instance_id) REFERENCES badge_instances(id) ON DELETE CASCADE
);
