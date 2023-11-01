UPDATE badge_info SET badge_url = replace(badge_url, "/symbols/", "/");

INSERT INTO badge_info (badge_name, badge_filename, badge_url, quadrant, time_period, franchise, reference, special) VALUES ("Level Veteran", "Level_Veteran.png", "https://drunkshimoda.com/", "Alpha", "2100s", "The USS Hood", "Commemorating Hard Earned Levels Before The Progress Cap!", 1) ON DUPLICATE KEY UPDATE badge_name = badge_name;
INSERT INTO badges (user_discord_id, badge_filename) SELECT discord_id, 'Level_Veteran.png' FROM users WHERE level >= 176;