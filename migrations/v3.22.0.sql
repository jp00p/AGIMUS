START TRANSACTION;
UPDATE badge_info SET badge_filename = "FoDTober.png" WHERE badge_filename = "FoD'Tober.png";
UPDATE badge_type SET badge_filename = "FoDTober.png" WHERE badge_filename = "FoD'Tober.png";
UPDATE badge_universe SET badge_filename = "FoDTober.png" WHERE badge_filename = "FoD'Tober.png";
COMMIT;
