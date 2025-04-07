-- v3.0.0.sql — Crystallization Schema

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
--
-- Rarity Tier Design Philosophy:
-- Common    – Simple color tints
-- Uncommon  – Visual overlays (e.g. patterns)
-- Rare      – Background effects (may include subtle top overlays)
-- Legendary – Animated overlays or backdrops
-- Mythic    – Animated + prestige visual effects
CREATE TABLE crystal_types (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(64) NOT NULL UNIQUE,
  crystal_rank_id INT NOT NULL,
  icon VARCHAR(128),
  effect TEXT,
  description TEXT,
  FOREIGN KEY (crystal_rank_id) REFERENCES crystal_ranks(id)
);

INSERT INTO crystal_types (name, crystal_rank_id, icon, effect, description) VALUES

  -- Common Crystals
  ("Dilithium", 1, "dilithium.png", NULL, "Good old Dilithium. Standard Starfleet issue!"),
  ("Deuterium", 1, "deuterium.png", "blue_tint", "Refined for warp cores. Imparts a subtle blue glow."),
  ("Tritanium", 1, "tritanium.png", "steel_tint", "Strong and dependable. Hull-grade enhancement."),
  ("Baryon", 1, "baryon.png", "orange_tint", "Sterile and slightly warm. Still glowing a bit."),

  -- Uncommon Crystals
  ("Isolinear", 2, "isolinear.png", "circuitry", "Shimoda's favorite plaything. Fully stackable!"),
  ("Optical Mesh", 2, "optical_mesh.png", "optical_filaments", "Data strands utilized by LCARS display terminals."),
  ("Positron", 2, "positron.png", "positronic_pattern", "Fully functional. Operates at 60 trillion calculations a second."),

  -- Rare Crystals
  ("Trilithium", 3, "trilithium.png", "fiery_glow", "A volatile compound banned in three quadrants. Handle with care."),
  ("Tholian Silk", 3, "tholian_silk.png", "web_pattern", "A crystallized thread of energy - elegant, fractical, and deadly."),
  ("Photonic Shard", 3, "photonic_shard.png", "holo_grid", "Rendered with simulated depth."),

  -- Legendary Crystals
  ("Raw Warp Plasma", 4, "warp_plasma.png", "pulsing_surge", "Collected from the EPS grid. Hums with that familiar pulse."),
  ("Subspace Ripple", 4, "subspace.png", "ripple_warp", "Always vibrating... but not quite here."),

-- Mythic Crystals
  ("Chroniton", 5, "chroniton.png", "phase_flicker", "Phased slightly out of time. Glitches in and out of this temporal frame."),
  ("Omega Molecule", 5, "omega.png", "shimmer_flux", "The perfect form of matter. Dangerous, beautiful, and rarely stable.");

-- 3. Badge Crystals (must come before badge_instances)
CREATE TABLE badge_crystals (
  id INT AUTO_INCREMENT PRIMARY KEY,
  badge_instance_id INT NOT NULL,
  crystal_type_id INT NOT NULL,
  granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (crystal_type_id) REFERENCES crystal_types(id)
);

-- 4. Badge Instances
CREATE TABLE badge_instances (
  id INT AUTO_INCREMENT PRIMARY KEY,
  badge_info_id INT NOT NULL,
  owner_discord_id BIGINT NOT NULL,
  locked BOOLEAN DEFAULT FALSE,
  origin_user_id BIGINT,
  acquired_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  preferred_crystal_id INT DEFAULT NULL,
  status ENUM('active', 'scrapped', 'archived') NOT NULL DEFAULT 'active',
  UNIQUE KEY (owner_discord_id, badge_info_id),
  FOREIGN KEY (badge_info_id) REFERENCES badge_info(id),
  FOREIGN KEY (preferred_crystal_id) REFERENCES badge_crystals(id) ON DELETE SET NULL
);

-- 5. Badge Trade History
CREATE TABLE badge_trade_history (
  id INT AUTO_INCREMENT PRIMARY KEY,
  badge_instance_id INT NOT NULL,
  from_user_id BIGINT NOT NULL,
  to_user_id BIGINT NOT NULL,
  transferred_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  trade_reason TEXT,
  FOREIGN KEY (badge_instance_id) REFERENCES badge_instances(id)
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

-- Add FK to badge_instances after it exists
ALTER TABLE badge_crystals
  ADD CONSTRAINT fk_badge_crystals_instance
  FOREIGN KEY (badge_instance_id) REFERENCES badge_instances(id) ON DELETE CASCADE;
