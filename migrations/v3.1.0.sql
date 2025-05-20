-- Update to allow decimal weights
ALTER TABLE crystal_ranks
MODIFY COLUMN drop_chance DECIMAL(5,2) NOT NULL;

-- Adjust values accordingly
UPDATE crystal_ranks SET drop_chance = 32 WHERE name = 'Uncommon';
UPDATE crystal_ranks SET drop_chance = 2.5 WHERE name = 'Mythic';

-- Insert Unobtanium
INSERT INTO crystal_ranks (name, emoji, rarity_rank, drop_chance, sort_order)
VALUES ('Unobtanium', '💥', 6, 0.5, 5);

-- Insert Bone Fragment Crystal (MOOPSY!)
INSERT INTO crystal_types (name, rarity_rank, icon, effect, description) VALUES
  ("Bone Fragment", 6, "bone_fragment.png", "moopsy_swarm", "That's bone. Looks oddly drinkable.");


-- Allow unowned badge instances to be created (for zek consortium investments...)
ALTER TABLE badge_instances
MODIFY COLUMN origin_user_id VARCHAR(64) NULL;

-- New 'tongo_consortium_investment' history event_type
ALTER TABLE badge_instance_history
MODIFY COLUMN event_type ENUM(
  'epoch',
  'level_up',
  'trade',
  'tongo_risk',
  'tongo_reward',
  'tongo_consortium_investment',
  'liquidation',
  'liquidation_endowment',
  'dividend_reward',
  'prestige_echo',
  'admin',
  'unknown'
) NOT NULL DEFAULT 'unknown';


-- Rework the Tongo Continuum Schema --

-- 1. Backup existing data
RENAME TABLE tongo_continuum TO tongo_continuum_old;

-- 2. Create the new table structure
CREATE TABLE tongo_continuum (
  source_instance_id INT PRIMARY KEY,
  thrown_by_user_id VARCHAR(64),
  added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (source_instance_id) REFERENCES badge_instances(id)
);

-- 3. Migrate data (assuming instance IDs are unique and valid)
INSERT INTO tongo_continuum (source_instance_id, thrown_by_user_id, added_at)
SELECT source_instance_id, thrown_by_user_id, added_at
FROM tongo_continuum_old;

-- 4. Drop the old table (optional, once verified)
DROP TABLE tongo_continuum_old;