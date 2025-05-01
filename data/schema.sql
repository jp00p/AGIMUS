CREATE DATABASE IF NOT EXISTS FoD;
use FoD;
CREATE TABLE IF NOT EXISTS jackpots (
  id int(11) NOT NULL AUTO_INCREMENT,
  jackpot_value bigint(20) NOT NULL DEFAULT 250,
  winner varchar(128) DEFAULT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  time_won timestamp NULL DEFAULT NULL,
  PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS reaction_role_messages (
  id INT(11) NOT NULL AUTO_INCREMENT,
  message_id VARCHAR(64) NOT NULL,
  message_name VARCHAR(64) NOT NULL,
  reaction_type VARCHAR(64) DEFAULT NULL,
  time_created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  PRIMARY KEY (id),
  UNIQUE KEY (message_id)
);
CREATE TABLE IF NOT EXISTS users (
  id int(11) NOT NULL AUTO_INCREMENT,
  discord_id varchar(64) NOT NULL,
  name varchar(128) DEFAULT NULL,
  mention varchar(128) DEFAULT NULL,
  score int(11) NOT NULL DEFAULT 0,
  spins int(11) NOT NULL DEFAULT 0,
  jackpots int(11) NOT NULL DEFAULT 0,
  wager int(11) NOT NULL DEFAULT 1,
  high_roller tinyint(1) DEFAULT 0,
  xp int(11) DEFAULT 0,
  log_messages int(11) NOT NULL DEFAULT 0,
  xp_enabled BOOLEAN NOT NULL DEFAULT 1,
  receive_notifications BOOLEAN NOT NULL DEFAULT 1,
  loudbot_enabled BOOLEAN NOT NULL DEFAULT 0,
  tagging_enabled BOOLEAN NOT NULL DEFAULT 0,
  crystallize_autoslot ENUM('manual', 'auto_rarest', 'auto_newest') DEFAULT 'manual',
  level int(11) DEFAULT 1,
  PRIMARY KEY (id),
  UNIQUE KEY (discord_id)
);
CREATE TABLE IF NOT EXISTS user_preferences (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id VARCHAR(64) NOT NULL,
  badge_showcase_color VARCHAR(32) NOT NULL DEFAULT 'orange',
  badge_sets_color VARCHAR(32) NOT NULL DEFAULT 'teal',
  PRIMARY KEY (id),
  FOREIGN KEY (user_discord_id)
    REFERENCES users(discord_id)
);
CREATE TABLE IF NOT EXISTS profile_photos (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id VARCHAR(64) NOT NULL,
  photo VARCHAR(255) DEFAULT NULL,
  last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP() ON UPDATE CURRENT_TIMESTAMP(),
  PRIMARY KEY (id),
  UNIQUE KEY (user_discord_id)
);
CREATE TABLE IF NOT EXISTS profile_stickers (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id VARCHAR(64) NOT NULL,
  sticker VARCHAR(255) DEFAULT NULL,
  position VARCHAR(24) DEFAULT NULL,
  last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP() ON UPDATE CURRENT_TIMESTAMP(),
  PRIMARY KEY (id),
  UNIQUE KEY (user_discord_id)
);
CREATE TABLE IF NOT EXISTS profile_taglines (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id VARCHAR(64) NOT NULL,
  tagline VARCHAR(255) DEFAULT NULL,
  last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP() ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY (user_discord_id)
);
CREATE TABLE IF NOT EXISTS profile_badges (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id VARCHAR(64) NOT NULL,
  badge_filename VARCHAR(128) DEFAULT NULL,
  last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP() ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY (user_discord_id)
);
CREATE TABLE IF NOT EXISTS profile_style (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id VARCHAR(64) NOT NULL,
  style VARCHAR(128) DEFAULT 'Default',
  last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP() ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY (user_discord_id)
);
CREATE TABLE IF NOT EXISTS profile_inventory (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id VARCHAR(64) NOT NULL,
  item_category VARCHAR(64) NOT NULL,
  item_name VARCHAR(128) NOT NULL,
  last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP() ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS profile_photo_filters (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id VARCHAR(64) NOT NULL,
  filter VARCHAR(64) NOT NULL,
  last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP() ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY (user_discord_id)
);
CREATE TABLE IF NOT EXISTS user_birthdays (
  user_discord_id VARCHAR(64) PRIMARY KEY
    REFERENCES users (discord_id) ON DELETE CASCADE,
  month TINYINT(2) NOT NULL,
  day TINYINT(2) NOT NULL
);
CREATE TABLE IF NOT EXISTS trades (
  id int(11) NOT NULL AUTO_INCREMENT,
  requestor_id varchar(128) NOT NULL,
  requestee_id varchar(128) NOT NULL,
  status varchar(64) NOT NULL DEFAULT 'pending',
  type varchar(64) NOT NULL DEFAULT 'standard',
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id),
  FOREIGN KEY (requestor_id)
    REFERENCES users(discord_id),
  FOREIGN KEY (requestee_id)
    REFERENCES users(discord_id)
);
CREATE TABLE IF NOT EXISTS badges (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id varchar(64) NOT NULL,
  badge_filename varchar(128) NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  locked BOOLEAN NOT NULL DEFAULT 0,
  PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS badge_info (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  badge_filename VARCHAR(128) NOT NULL UNIQUE,
  badge_name VARCHAR(128) NOT NULL,
  badge_url VARCHAR(256) NOT NULL,
  quadrant VARCHAR(128) DEFAULT NULL,
  time_period VARCHAR(128) DEFAULT NULL,
  franchise VARCHAR(128) DEFAULT NULL,
  reference VARCHAR(128) DEFAULT NULL,
  special BOOLEAN NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS badge_affiliation (
  id int NOT NULL AUTO_INCREMENT,
  badge_filename varchar(128) NOT NULL,
  affiliation_name varchar(128) NOT NULL,
  PRIMARY KEY (id),
  KEY badge_filename (badge_filename),
  CONSTRAINT badge_affiliation_fk_badge_filename FOREIGN KEY (badge_filename) REFERENCES badge_info (badge_filename)
);
CREATE TABLE IF NOT EXISTS badge_type (
  id int NOT NULL AUTO_INCREMENT,
  badge_filename varchar(128) NOT NULL,
  type_name varchar(128) NOT NULL,
  PRIMARY KEY (id),
  KEY badge_filename (badge_filename),
  CONSTRAINT badge_type_fk_badge_filename FOREIGN KEY (badge_filename) REFERENCES badge_info (badge_filename)
);
CREATE TABLE IF NOT EXISTS badge_universe (
  id int NOT NULL AUTO_INCREMENT,
  badge_filename varchar(128) NOT NULL,
  universe_name varchar(128) NOT NULL,
  PRIMARY KEY (id),
  KEY badge_filename (badge_filename),
  CONSTRAINT badge_universe_fk_badge_filename FOREIGN KEY (badge_filename) REFERENCES badge_info (badge_filename)
);
CREATE TABLE IF NOT EXISTS trade_offered (
  id int(11) NOT NULL AUTO_INCREMENT,
  badge_filename VARCHAR(128) NOT NULL,
  trade_id int(11) NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id),
  FOREIGN KEY (badge_filename)
    REFERENCES badge_info(badge_filename),
  FOREIGN KEY (trade_id)
    REFERENCES trades(id)
);
CREATE TABLE IF NOT EXISTS trade_requested (
  id int(11) NOT NULL AUTO_INCREMENT,
  badge_filename VARCHAR(128) NOT NULL,
  trade_id int(11) NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id),
  FOREIGN KEY (badge_filename)
    REFERENCES badge_info(badge_filename),
  FOREIGN KEY (trade_id)
    REFERENCES trades(id)
);
CREATE TABLE IF NOT EXISTS badge_scraps (
  id int NOT NULL AUTO_INCREMENT,
  badge_filename varchar(128) NOT NULL,
  user_discord_id varchar(128) NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id),
  KEY badge_filename (badge_filename),
  CONSTRAINT badge_scraps_fk_badge_filename FOREIGN KEY (badge_filename) REFERENCES badge_info (badge_filename)
);
CREATE TABLE IF NOT EXISTS badge_scrapped (
  id int NOT NULL AUTO_INCREMENT,
  scrap_id int(11) NOT NULL,
  badge_filename varchar(128) NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id),
  KEY badge_filename (badge_filename),
  FOREIGN KEY (scrap_id) REFERENCES badge_scraps (id),
  FOREIGN KEY (badge_filename) REFERENCES badge_info (badge_filename)
);
CREATE TABLE IF NOT EXISTS reactions (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_id varchar(64) NOT NULL,
  user_name varchar(64) NOT NULL,
  reaction varchar(128) NOT NULL,
  reaction_message_id varchar(64) NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id),
  CONSTRAINT USERID_REACTION_MESSAGEID UNIQUE (user_id, reaction, reaction_message_id)
);
CREATE TABLE IF NOT EXISTS starboard_posts (
  id int(11) NOT NULL AUTO_INCREMENT,
  message_id varchar(64) NOT NULL,
  user_id varchar(64) NOT NULL,
  board_channel varchar(128) NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS xp_history (
  id int(11) NOT NULL AUTO_INCREMENT,
  channel_id varchar(64) NOT NULL,
  user_discord_id varchar(64) NOT NULL,
  amount int(11) NOT NULL,
  reason varchar(32) NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS message_history (
  id int(11) NOT NULL AUTO_INCREMENT,
  channel_id varchar(64) NOT NULL,
  user_discord_id varchar(64) NOT NULL,
  message_text text NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS shouts (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id varchar(64) NOT NULL,
  channel_id varchar(64) NOT NULL,
  shout varchar(128) NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id),
  UNIQUE KEY (shout)
);
CREATE TABLE IF NOT EXISTS badge_wishlists (
  id int NOT NULL AUTO_INCREMENT,
  badge_filename varchar(128) NOT NULL,
  user_discord_id varchar(128) NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id),
  KEY badge_filename (badge_filename),
  CONSTRAINT badge_wishlists_fk_badge_filename FOREIGN KEY (badge_filename) REFERENCES badge_info (badge_filename)
);
CREATE TABLE IF NOT EXISTS badge_tags (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id varchar(128) NOT NULL,
  tag_name varchar(24) NOT NULL,
  PRIMARY KEY (id)
);
CREATE TABLE badge_tags_associations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  badge_tags_id INT NOT NULL,
  badge_instance_id INT NOT NULL,
  CONSTRAINT fk_tags_to_tags
    FOREIGN KEY (badge_tags_id)
    REFERENCES badge_tags(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_tags_to_instances
    FOREIGN KEY (badge_instance_id)
    REFERENCES badge_instances(id)
    ON DELETE CASCADE,
  UNIQUE KEY unique_tag_per_instance (badge_tags_id, badge_instance_id)
);
CREATE TABLE IF NOT EXISTS tags_carousel_position (
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
CREATE TABLE IF NOT EXISTS wishlist_dismissals (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id varchar(64) NOT NULL,
  match_discord_id varchar(64) NOT NULL,
  has JSON NOT NULL,
  wants JSON NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS randomep_selections (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id varchar(64) NOT NULL,
  shows JSON NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id),
  UNIQUE (user_discord_id)
);
CREATE TABLE IF NOT EXISTS user_aliases (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id varchar(64) NOT NULL,
  old_alias varchar(64) NOT NULL,
  new_alias varchar(64) NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS xp_cap_progress (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id varchar(64) NOT NULL,
  progress int(4) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE (user_discord_id)
);
CREATE TABLE IF NOT EXISTS down_to_dabo (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id varchar(64) NOT NULL,
  weight int(4) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE (user_discord_id)
);
CREATE TABLE IF NOT EXISTS tongo (
  id int(11) NOT NULL AUTO_INCREMENT,
  chair_discord_id varchar(64) NOT NULL,
  status varchar(64) NOT NULL DEFAULT 'active',
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS tongo_players (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id varchar(64) NOT NULL,
  tongo_id int(11) DEFAULT 0 NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id),
  KEY tongo_id (tongo_id),
  CONSTRAINT badge_tongo_players_fk_tongo_id FOREIGN KEY (tongo_id) REFERENCES tongo (id),
  CONSTRAINT unique_user_tongo UNIQUE (user_discord_id, tongo_id)
);
CREATE TABLE IF NOT EXISTS tongo_pot (
  id int(11) NOT NULL AUTO_INCREMENT,
  origin_user_discord_id varchar(64) NOT NULL,
  badge_filename VARCHAR(128) DEFAULT '' NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id),
  KEY badge_filename (badge_filename),
  CONSTRAINT badge_tongo_pot_fk_badge_filename FOREIGN KEY (badge_filename) REFERENCES badge_info (badge_filename)
);
CREATE TABLE IF NOT EXISTS user_tags (
  id int(11) NOT NULL AUTO_INCREMENT,
  tagged_user_id varchar(128) NOT NULL,
  tagger_user_id varchar(128) NOT NULL,
  tag varchar(128) NOT NULL,
  last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP() ON UPDATE CURRENT_TIMESTAMP(),
  PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS april_fools (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id VARCHAR(64) NOT NULL,
  cornmander_status VARCHAR(32) NOT NULL DEFAULT 'unpipped',
  last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP() ON UPDATE CURRENT_TIMESTAMP(),
  PRIMARY KEY (id),
  FOREIGN KEY (user_discord_id)
    REFERENCES users(discord_id)
);
CREATE TABLE IF NOT EXISTS food_war (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id VARCHAR(64) NOT NULL,
  reason VARCHAR(64) NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id),
  FOREIGN KEY (user_discord_id)
    REFERENCES users(discord_id)
);
CREATE TABLE IF NOT EXISTS sub_rosa (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id VARCHAR(64) NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id),
  FOREIGN KEY (user_discord_id)
    REFERENCES users(discord_id)
);
CREATE TABLE IF NOT EXISTS wrapped_queue (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_discord_id VARCHAR(64) NOT NULL,
  status ENUM('pending', 'processing', 'complete', 'error') DEFAULT 'pending',
  wrapped_year INT NOT NULL,
  time_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  time_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  video_path VARCHAR(255),
  error TEXT
);

-- v3.0.0

-- ==Echelon (New Level System)==
CREATE TABLE echelon_progress (
  user_discord_id VARCHAR(64) PRIMARY KEY,
  current_xp BIGINT NOT NULL DEFAULT 0,
  current_level INT NOT NULL DEFAULT 1,
  current_prestige_level INT NOT NULL DEFAULT 0,
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

  -- Uncommon Crystals (Border Effects)
  ("Isolinear", 2, "isolinear.png", "isolinear", "Shimoda's favorite plaything material. Fully stackable!"),
  ("Optical", 2, "optical.png", "optical", "Optical data strands. Utilized by LCARS display terminals."),
  ("Positron", 2, "positron.png", "positronic", "Fully functional. Networks of these can operate at 60 trillion calculations a second."),
  ("Cryonetrium", 2, "cryonetrium.png", "cryonetrium", "Still gaseous at -200°C, that's some cold coolant!"),

  ('Verterium Cortenide', 2, 'verterium_cortenide.png', 'verterium_cortenide', 'Essential alloy used in Starship Warp Nacelles. Emits faint subspace displacement harmonics.'), -- New, Needs effect
  ('Transparent Aluminum', 2, 'transparent_aluminum.png', 'transparent_aluminum', 'Revolutionary compound. Transparent, resilient, and rumored to have been invented by a time traveler...'), -- New, Needs effect
  ('Boridium', 2, 'boridium.png', 'boridium', 'Energetic material with many uses. Boridium is the powerhouse of the power cell.'), -- New, Needs effect

  -- Rare Crystals (Backgrounds)
  ("Trilithium", 3, "trilithium.png", "trilithium_banger", "Volatile compound banned in most systems. Handle with care."),
  ("Tholian Silk", 3, "tholian_silk.png", "tholian_web", "A crystallized thread of energy - elegant, fractical, and deadly."),
  ("Holomatrix Fragment", 3, "holomatrix_fragment.png", "holo_grid", "Hologrammatical. Renders with an uncanny simulated depth."),
  ("Silicon Shard", 3, "silicon_shard.png", "crystalline_entity", "Sharp and pointy, a beautiful Entity. Crystalline with a lot of lore behind it."),

  -- Legendary Crystals (Animations)
  ("Warp Plasma Cell", 4, "warp_plasma.png", "warp_pulse", "EJECTED FROM A CORE! Hums with that familiar pulse."),
  ("Tetryon", 4, "tetryon.png", "subspace_ripple", "A particle intrinsic to subspace. Distortions abound when these are around!"),

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
    'admin',
    'unknown'
  ) NOT NULL DEFAULT 'unknown',
  FOREIGN KEY (badge_instance_id) REFERENCES badge_instances(id),
  INDEX idx_history_instance_id (badge_instance_id)
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
  liability_mode ENUM('unlocked', 'all_in') NOT NULL,
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

-- Badge Trades
CREATE TABLE IF NOT EXISTS badge_instance_trades (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  requestor_id    varchar(64) NOT NULL,
  requestee_id    varchar(64) NOT NULL,
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


-- Crystal Trades
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