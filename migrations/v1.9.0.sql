ALTER TABLE badge_info ADD COLUMN special BOOLEAN NOT NULL DEFAULT 0;
UPDATE badge_info SET special = 1 WHERE badge_filename = "Friends_Of_DeSoto.png";
UPDATE badge_info SET special = 1 WHERE badge_filename = "Captain_Picard_Day.png";