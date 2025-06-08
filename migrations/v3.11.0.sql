-- Use transaction so we can atomically alter the child tables before the main table is updated and it occurs at the end
START TRANSACTION;

UPDATE badge_affiliation SET badge_filename = 'AGIMUS-Banner-E.png' WHERE badge_filename = 'AMIGUS-Banner-E.png';
UPDATE badge_affiliation SET badge_filename = 'AGIMUS-Banner-D.png' WHERE badge_filename = 'AMIGUS-Banner-D.png';

UPDATE badge_type SET badge_filename = 'AGIMUS-Banner-E.png' WHERE badge_filename = 'AMIGUS-Banner-E.png';
UPDATE badge_type SET badge_filename = 'AGIMUS-Banner-D.png' WHERE badge_filename = 'AMIGUS-Banner-D.png';

UPDATE badge_universe SET badge_filename = 'AGIMUS-Banner-E.png' WHERE badge_filename = 'AMIGUS-Banner-E.png';
UPDATE badge_universe SET badge_filename = 'AGIMUS-Banner-D.png' WHERE badge_filename = 'AMIGUS-Banner-D.png';

UPDATE badge_info SET badge_name = 'AGIMUS Banner E', badge_filename = 'AGIMUS-Banner-E.png' WHERE badge_filename = 'AMIGUS-Banner-E.png';
UPDATE badge_info SET badge_name = 'AGIMUS Banner D', badge_filename = 'AGIMUS-Banner-D.png' WHERE badge_filename = 'AMIGUS-Banner-D.png';

UPDATE badge_info SET time_period = '2000s' WHERE badge_name = 'FOD Pride 2025';
INSERT INTO badge_info (badge_name, badge_filename, badge_url, quadrant, time_period, franchise, reference, special) VALUES ("Lady Lurkana Coffee", "Lady_Lurkana_Coffee.png", "https://pennyante-art.carrd.co/", "Alpha", "2000s", "The USS Hood", "Lurqara' joH qa'vin, it's a Good Day to Rise. (Artwork by Penny Ante!)", 1);

COMMIT;