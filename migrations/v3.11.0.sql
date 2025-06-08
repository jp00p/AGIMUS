START TRANSACTION;

-- Step 1: Drop foreign keys temporarily
ALTER TABLE badge_affiliation DROP FOREIGN KEY badge_affiliation_fk_badge_filename;
ALTER TABLE badge_type DROP FOREIGN KEY badge_type_fk_badge_filename;
ALTER TABLE badge_universe DROP FOREIGN KEY badge_universe_fk_badge_filename;

-- Step 2: Update parent table first (so children can reference the new filename)
UPDATE badge_info SET badge_name = 'AGIMUS Banner E', badge_filename = 'AGIMUS-Banner-E.png' WHERE badge_filename = 'AMIGUS-Banner-E.png';
UPDATE badge_info SET badge_name = 'AGIMUS Banner D', badge_filename = 'AGIMUS-Banner-D.png' WHERE badge_filename = 'AMIGUS-Banner-D.png';

-- Step 3: Update all child tables
UPDATE badge_affiliation SET badge_filename = 'AGIMUS-Banner-E.png' WHERE badge_filename = 'AMIGUS-Banner-E.png';
UPDATE badge_affiliation SET badge_filename = 'AGIMUS-Banner-D.png' WHERE badge_filename = 'AMIGUS-Banner-D.png';

UPDATE badge_type SET badge_filename = 'AGIMUS-Banner-E.png' WHERE badge_filename = 'AMIGUS-Banner-E.png';
UPDATE badge_type SET badge_filename = 'AGIMUS-Banner-D.png' WHERE badge_filename = 'AMIGUS-Banner-D.png';

UPDATE badge_universe SET badge_filename = 'AGIMUS-Banner-E.png' WHERE badge_filename = 'AMIGUS-Banner-E.png';
UPDATE badge_universe SET badge_filename = 'AGIMUS-Banner-D.png' WHERE badge_filename = 'AMIGUS-Banner-D.png';

-- Step 4: Re-add foreign keys
ALTER TABLE badge_affiliation
  ADD CONSTRAINT badge_affiliation_fk_badge_filename
  FOREIGN KEY (badge_filename) REFERENCES badge_info(badge_filename);

ALTER TABLE badge_type
  ADD CONSTRAINT badge_type_fk_badge_filename
  FOREIGN KEY (badge_filename) REFERENCES badge_info(badge_filename);

ALTER TABLE badge_universe
  ADD CONSTRAINT badge_universe_fk_badge_filename
  FOREIGN KEY (badge_filename) REFERENCES badge_info(badge_filename);

UPDATE badge_info SET time_period = '2000s' WHERE badge_name = 'FOD Pride 2025';
INSERT INTO badge_info (badge_name, badge_filename, badge_url, quadrant, time_period, franchise, reference, special) VALUES ("Lady Lurkana Coffee", "Lady_Lurkana_Coffee.png", "https://pennyante-art.carrd.co/", "Alpha", "2000s", "The USS Hood", "Lurqara' joH qa'vin, it's a Good Day to Rise. (Artwork by Penny Ante!)", 1);

COMMIT;