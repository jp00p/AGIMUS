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
MODIFY COLUMN owner_discord_id VARCHAR(64) NULL,
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