-- Server Settings Table
CREATE TABLE IF NOT EXISTS server_settings (
  id INT PRIMARY KEY CHECK (id = 1),
  bonus_xp_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  bonus_xp_amount TINYINT NULL DEFAULT 2
);

-- Ensure a row exists
INSERT INTO server_settings (id, bonus_xp_enabled, bonus_xp_amount)
VALUES (1, FALSE, 2)
ON DUPLICATE KEY UPDATE id = id;