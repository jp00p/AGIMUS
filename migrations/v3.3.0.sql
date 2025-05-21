-- Convert drop_chance back to FLOAT
ALTER TABLE crystal_ranks
MODIFY COLUMN drop_chance FLOAT NOT NULL;

-- Fix typo in rarity name
UPDATE crystal_ranks
SET name = 'Unobtainium'
WHERE LOWER(name) = 'unobtanium';

-- Reset drop chances...
UPDATE crystal_ranks SET drop_chance = 50 WHERE name = 'Common';
UPDATE crystal_ranks SET drop_chance = 33 WHERE name = 'Uncommon';
UPDATE crystal_ranks SET drop_chance = 10 WHERE name = 'Rare';
UPDATE crystal_ranks SET drop_chance = 5  WHERE name = 'Legendary';
UPDATE crystal_ranks SET drop_chance = 1.75 WHERE name = 'Mythic';
UPDATE crystal_ranks SET drop_chance = 0.25 WHERE name = 'Unobtainium';