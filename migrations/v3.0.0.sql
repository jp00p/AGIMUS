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

-- v3.0.0

-- ==Echelon (New Level System)==
CREATE TABLE echelon_progress (
  user_discord_id VARCHAR(64) PRIMARY KEY,
  current_xp BIGINT NOT NULL DEFAULT 0,
  current_level INT NOT NULL DEFAULT 1,
  current_prestige_tier INT NOT NULL DEFAULT 0,
  buffer_failure_streak INT NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_discord_id) REFERENCES users(discord_id)
);

CREATE TABLE IF NOT EXISTS echelon_progress_history (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_discord_id VARCHAR(64) NOT NULL,
  xp_gained INT NOT NULL,
  user_level_at_gain INT NOT NULL,
  channel_id BIGINT NULL,
  reason VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_discord_id) REFERENCES users(discord_id)
);

CREATE TABLE IF NOT EXISTS legacy_xp_records (
  user_discord_id VARCHAR(64) PRIMARY KEY,
  legacy_level INT NOT NULL DEFAULT 1,
  legacy_xp BIGINT NOT NULL DEFAULT 0,
  recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_discord_id) REFERENCES users(discord_id)
);

-- ==CRYSTALS tables!==

-- Crystal Ranks
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

-- Crystal Types
CREATE TABLE IF NOT EXISTS crystal_types (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(64) NOT NULL UNIQUE,
  rarity_rank INT NOT NULL,
  icon VARCHAR(128),
  effect TEXT,
  description TEXT
);

INSERT INTO crystal_types (name, rarity_rank, icon, effect, description) VALUES

  -- Common Crystals (Tints/Gradients)
  ("Dilithium", 1, "dilithium.png", "pink_tint", "Good old Dilithium. Standard Starfleet issue!"),
  ("Deuterium", 1, "deuterium.png", "blue_tint", "Refined for warp cores. It glows a bit blue."),
  ("Tritanium", 1, "tritanium.png", "steel_tint", "Strong and dependable. Hull-grade enhancement."),
  ("Baryon", 1, "baryon.png", "orange_tint", "Sterile and slightly warm. Still glowing a bit."),
  ("Cormaline", 1, "cormaline.png", "purple_tint", 'Ferenginar gemstone. Often "gifted" during dubious business deals.'),
  ("Tellurium", 1, "tellurium.png", "greenmint_tint", "Essential for biosensor arrays. Slightly toxic when aerosolized, don't breathe this!"),
  ("Rubindium", 1, "rubindium.png", "crimson_gradient", "Sensor-reflective alloy with multiple applications. Chief among them, frikkin laser beams."),
  ("Polytrinic", 1, "polytrinic.png", "lime_gradient", "Toxic and corrosive. Glows green, that means bad!"),
  ("Benamite", 1, "benamite.png", "navy_gradient", "Essential for quantum slipstream drives. Sadly unstable, you lose yet again Voyager!"),
  ("Auridium", 1, "auridium.png", "gold_gradient", "Trade-standard alloy with a golden gleam. All that glitters is not gold."),
  ("Duranium", 1, "duranium.png", "silver_gradient", "A silvery alloy used in Starship hull plating. Makes a nice 'BWONG!' sound when you smack it."),
  ("Solanogen", 1, "solanogen.png", "cyan_gradient", "Exotic compound from subspace realms. Don't get SCHISMD!"),
  ("Pergium", 1, "pergium.png", "amber_gradient", "Highly prized radiothermal ore. Still glows warm from its mining days."),

  ("Latinum", 1, "latinum.png", "latinum", "Get that, get that, Gold Pressed Latinum!"),
  ('Transparent Aluminum', 1, 'transparent_aluminum.png', 'transparent_aluminum', 'Revolutionary compound. Transparent, resilient, and rumored to have been invented by a time traveler...'),

  -- Uncommon Crystals (Border Effects)
  ("Optical", 2, "optical.png", "optical", "Optical data strands. Utilized by LCARS display terminals."),
  ("Cryonetrium", 2, "cryonetrium.png", "cryonetrium", "Still gaseous at -200°C, that's some cold coolant!"),
  ('Verterium Cortenide', 2, 'verterium_cortenide.png', 'verterium_cortenide', 'Essential alloy used in Starship Warp Nacelles. Emits faint subspace displacement harmonics.'),
  ('Boridium', 2, 'boridium.png', 'boridium', 'Energetic material with many uses. Boridium is the powerhouse of the power cell.'),

  -- Rare Crystals (Backgrounds)
  ("Trilithium", 3, "trilithium.png", "trilithium_banger", "Volatile compound banned in most systems. Handle with care."),
  ("Tholian Silk", 3, "tholian_silk.png", "tholian_web", "A crystallized thread of energy - elegant, fractical, and deadly."),
  ("Holomatrix Fragment", 3, "holomatrix_fragment.png", "holo_grid", "Hologrammatical. Renders with an uncanny simulated depth."),
  ("Silicon Shard", 3, "silicon_shard.png", "crystalline_entity", "Sharp and pointy, a beautiful Entity. Crystalline with a lot of lore behind it."),
  ("Colombian Coffee Crystal", 3, "coffee_crystal.png", "coffee_nebula", "Delicious, tastes like rich-bodied regular coffee! A nebulous and tasty flavor."),
  ("Positron", 3, "positron.png", "positronic_net", "Fully functional. Networks of these can operate at 60 trillion calculations a second."),
  ("Isolinear", 3, "isolinear.png", "isolinear_circuit", "Shimoda's favorite circuitry plaything. Fully stackable!"),
  ("Farpoint Sphere", 3, "farpoint_sphere.png", "q_grid", "Has a warm feeling, like being wrapped in a big Pendleton blanket. How Q-rious..."),

  -- Legendary Crystals (Animations)
  ("Warp Plasma Cell", 4, "warp_plasma.png", "warp_pulse", "EJECTED FROM A CORE! Hums with that familiar pulse."),
  ("Tetryon", 4, "tetryon.png", "subspace_ripple", "A particle intrinsic to subspace. Distortions abound when these are around!"),
  ("Triaxilation Node", 4, "triaxilation_node.png", "static_cascade", "Essential to subspace communications. Emits a pulsing cascade that resonates across signal channels."),

  -- Mythic Crystals (Prestige Animations)
  ("Bajoran Orb", 5, "bajoran_orb.png", "celestial_temple", "A Tear of the Prophets. My Child!"),
  ("Chroniton", 5, "chroniton.png", "phase_flicker", "Time travel! Glitches in and out of this temporal frame."),
  ("Omega Molecule", 5, "omega.png", "shimmer_flux", "The perfect form of matter. Dangerous, beautiful, and rarely stable.");

-- Crystal Pattern Buffers (Credits to redeem for Crystals)
CREATE TABLE IF NOT EXISTS crystal_pattern_buffers (
  user_discord_id VARCHAR(64) PRIMARY KEY,
  buffer_count INT NOT NULL DEFAULT 0 CHECK (buffer_count >= 0),
  FOREIGN KEY (user_discord_id) REFERENCES users(discord_id)
);

-- Crystal Instances (Initially tradeable but once 'attuned' cannot be reattached to another)
CREATE TABLE IF NOT EXISTS crystal_instances (
  id INT AUTO_INCREMENT PRIMARY KEY,
  crystal_type_id INT NOT NULL,
  owner_discord_id VARCHAR(64) DEFAULT NULL,
  attached_to_instance_id INT DEFAULT NULL, -- leave this FK for later
  status ENUM('available', 'attuned', 'harmonized') NOT NULL DEFAULT 'available',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (crystal_type_id) REFERENCES crystal_types(id),
  FOREIGN KEY (owner_discord_id) REFERENCES users(discord_id)
);

-- Crystal Instances History
CREATE TABLE IF NOT EXISTS crystal_instance_history (
  id INT AUTO_INCREMENT PRIMARY KEY,
  crystal_instance_id INT NOT NULL,
  event_type ENUM('replicated', 'trade', 'attuned') NOT NULL,
  from_user_id varchar(64) DEFAULT NULL,
  to_user_id varchar(64) DEFAULT NULL,
  occurred_at DATETIME DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (crystal_instance_id) REFERENCES crystal_instances(id),
  FOREIGN KEY (from_user_id) REFERENCES users(discord_id),
  FOREIGN KEY (to_user_id) REFERENCES users(discord_id)
);

-- ==Badges Tables==

-- Badge Instances
CREATE TABLE IF NOT EXISTS badge_instances (
  id INT AUTO_INCREMENT PRIMARY KEY,
  badge_info_id INT UNSIGNED NOT NULL,
  owner_discord_id varchar(64) NULL,
  prestige_level INT DEFAULT 0,
  locked BOOLEAN DEFAULT FALSE,
  active BOOLEAN GENERATED ALWAYS AS (status = 'active') STORED,
  origin_user_id varchar(64) NOT NULL,
  acquired_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  active_crystal_id INT DEFAULT NULL,
  status ENUM('active', 'scrapped', 'liquidated', 'archived') NOT NULL DEFAULT 'active',

  UNIQUE KEY uq_user_badge_active (owner_discord_id, badge_info_id, prestige_level, active),
  FOREIGN KEY (badge_info_id) REFERENCES badge_info(id),
  FOREIGN KEY (active_crystal_id) REFERENCES crystal_instances(id) ON DELETE SET NULL
);

-- Badge Crystals (Many to One)
CREATE TABLE IF NOT EXISTS badge_crystals (
  id INT AUTO_INCREMENT PRIMARY KEY,
  badge_instance_id INT NOT NULL,
  crystal_instance_id INT NOT NULL,
  attached_at DATETIME DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (badge_instance_id) REFERENCES badge_instances(id) ON DELETE CASCADE,
  FOREIGN KEY (crystal_instance_id) REFERENCES crystal_instances(id),
  UNIQUE (badge_instance_id, crystal_instance_id)
);


-- Alter crystal_instances now that badge_instances has been created so that we can fk constraint it
ALTER TABLE crystal_instances
  ADD CONSTRAINT fk_crystal_attached_to_badge
  FOREIGN KEY (attached_to_instance_id) REFERENCES badge_instances(id);

-- Badge Instance History, Track Lifecycle
CREATE TABLE IF NOT EXISTS badge_instance_history (
  id INT AUTO_INCREMENT PRIMARY KEY,
  badge_instance_id INT NOT NULL,
  from_user_id varchar(64) DEFAULT NULL,
  to_user_id varchar(64) NULL,
  occurred_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  event_type ENUM(
    'epoch',
    'level_up',
    'trade',
    'tongo_risk',
    'tongo_reward',
    'liquidation',
    'liquidation_endowment',
    'prestige_echo',
    'admin',
    'unknown'
  ) NOT NULL DEFAULT 'unknown',
  FOREIGN KEY (badge_instance_id) REFERENCES badge_instances(id),
  INDEX idx_history_instance_id (badge_instance_id)
);

CREATE TABLE IF NOT EXISTS profile_badge_instances (
  user_discord_id VARCHAR(64) PRIMARY KEY,
  badge_instance_id INT,
  FOREIGN KEY (badge_instance_id) REFERENCES badge_instances(id)
);

--
-- TONGO v2
--

CREATE TABLE IF NOT EXISTS tongo_games (
  id INT AUTO_INCREMENT PRIMARY KEY,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  chair_user_id varchar(64) NOT NULL,
  status ENUM('open', 'in_progress', 'resolved', 'cancelled') DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS tongo_game_players (
  game_id INT,
  user_discord_id varchar(64),
  joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (game_id, user_discord_id),
  FOREIGN KEY (game_id) REFERENCES tongo_games(id)
);

CREATE TABLE IF NOT EXISTS tongo_continuum (
  badge_info_id INT UNSIGNED PRIMARY KEY,
  source_instance_id INT,
  thrown_by_user_id varchar(64),
  added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (badge_info_id) REFERENCES badge_info(id),
  FOREIGN KEY (source_instance_id) REFERENCES badge_instances(id)
);

CREATE TABLE IF NOT EXISTS tongo_game_rewards (
  game_id INT,
  user_discord_id varchar(64),
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

CREATE TABLE IF NOT EXISTS badge_instances_wishlists (
  user_discord_id VARCHAR(64)   NOT NULL,
  badge_info_id   INT UNSIGNED  NOT NULL,
  time_added      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_discord_id, badge_info_id),
  FOREIGN KEY (user_discord_id) REFERENCES users(discord_id) ON DELETE CASCADE,
  FOREIGN KEY (badge_info_id)   REFERENCES badge_info(id)   ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS badge_instances_wishlists_dismissals (
  user_discord_id   VARCHAR(64)         NOT NULL,
  match_discord_id  VARCHAR(64)         NOT NULL,
  badge_info_id     INT UNSIGNED        NOT NULL,
  prestige_level    INT                 NOT NULL,
  role              ENUM('has','wants') NOT NULL,
  time_created      TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_discord_id, match_discord_id, badge_info_id, prestige_level, role),
  FOREIGN KEY (user_discord_id) REFERENCES users(discord_id) ON DELETE CASCADE,
  FOREIGN KEY (match_discord_id) REFERENCES users(discord_id) ON DELETE CASCADE,
  FOREIGN KEY (badge_info_id) REFERENCES badge_info(id) ON DELETE CASCADE
);

--
-- Badge Tags
--

CREATE TABLE IF NOT EXISTS badge_info_tags_associations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_discord_id VARCHAR(64) NOT NULL,
  badge_info_id INT UNSIGNED NOT NULL,
  badge_tags_id INT NOT NULL,
  time_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_discord_id) REFERENCES users(discord_id) ON DELETE CASCADE,
  FOREIGN KEY (badge_info_id) REFERENCES badge_info(id) ON DELETE CASCADE,
  FOREIGN KEY (badge_tags_id) REFERENCES badge_tags(id) ON DELETE CASCADE,
  UNIQUE KEY uq_user_info_tag (user_discord_id, badge_info_id, badge_tags_id)
);

CREATE TABLE IF NOT EXISTS badge_info_tags_carousel_state (
  user_discord_id VARCHAR(64) PRIMARY KEY,
  last_viewed_badge_info_id INT UNSIGNED,
  last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_discord_id) REFERENCES users(discord_id) ON DELETE CASCADE,
  FOREIGN KEY (last_viewed_badge_info_id) REFERENCES badge_info(id) ON DELETE CASCADE
);

--
-- Trades
--

-- Badge Trades
CREATE TABLE IF NOT EXISTS badge_instance_trades (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  requestor_id    varchar(64) NOT NULL,
  requestee_id    varchar(64) NOT NULL,
  prestige_level  INT NOT NULL DEFAULT 0,
  status          ENUM('pending', 'active', 'complete', 'declined', 'canceled') NOT NULL DEFAULT 'pending',
  time_created    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trade_offered_badge_instances (
  id                INT AUTO_INCREMENT PRIMARY KEY,
  trade_id          INT NOT NULL,
  badge_instance_id INT NOT NULL,
  FOREIGN KEY (trade_id) REFERENCES badge_instance_trades(id) ON DELETE CASCADE,
  FOREIGN KEY (badge_instance_id) REFERENCES badge_instances(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS trade_requested_badge_instances (
  id                INT AUTO_INCREMENT PRIMARY KEY,
  trade_id          INT NOT NULL,
  badge_instance_id INT NOT NULL,
  FOREIGN KEY (trade_id) REFERENCES badge_instance_trades(id) ON DELETE CASCADE,
  FOREIGN KEY (badge_instance_id) REFERENCES badge_instances(id) ON DELETE CASCADE
);


-- Crystal Trades -- NOTE: To be implemented later
CREATE TABLE IF NOT EXISTS crystal_instance_trades (
  id INT AUTO_INCREMENT PRIMARY KEY,
  requestor_id varchar(64) NOT NULL,
  requestee_id varchar(64) NOT NULL,
  status ENUM('pending', 'active', 'complete', 'declined', 'canceled') NOT NULL DEFAULT 'pending',
  time_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trade_offered_crystal_instances (
  id INT AUTO_INCREMENT PRIMARY KEY,
  trade_id INT NOT NULL,
  crystal_instance_id INT NOT NULL,
  FOREIGN KEY (trade_id) REFERENCES crystal_instance_trades(id) ON DELETE CASCADE,
  FOREIGN KEY (crystal_instance_id) REFERENCES crystal_instances(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS trade_requested_crystal_instances (
  id INT AUTO_INCREMENT PRIMARY KEY,
  trade_id INT NOT NULL,
  crystal_instance_id INT NOT NULL,
  FOREIGN KEY (trade_id) REFERENCES crystal_instance_trades(id) ON DELETE CASCADE,
  FOREIGN KEY (crystal_instance_id) REFERENCES crystal_instances(id) ON DELETE CASCADE
);