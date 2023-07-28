CREATE TABLE IF NOT EXISTS user_birthdays (
  user_discord_id VARCHAR(64) PRIMARY KEY
    REFERENCES users (discord_id) ON DELETE CASCADE,
  month TINYINT(2) NOT NULL,
  day TINYINT(2) NOT NULL
);