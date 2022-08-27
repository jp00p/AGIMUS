CREATE DATABASE IF NOT EXISTS FoD;
use FoD;
CREATE TABLE IF NOT EXISTS jackpots (
  id int(11) NOT NULL AUTO_INCREMENT,
  jackpot_value bigint(20) NOT NULL,
  winner varchar(128) DEFAULT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  time_won timestamp NULL DEFAULT NULL,
  PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS reaction_role_messages (
  id INT(11) NOT NULL AUTO_INCREMENT,
  message_id VARCHAR(64) NOT NULL,
  message_name VARCHAR(64) NOT NULL,
  reaction_type VARCHAR(64) DEFAULT NULL,
  time_created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  PRIMARY KEY (id),
  UNIQUE KEY (message_id)
);
CREATE TABLE IF NOT EXISTS users (
  id int(11) NOT NULL AUTO_INCREMENT,
  discord_id varchar(64) NOT NULL,
  name varchar(128) DEFAULT NULL,
  mention varchar(128) DEFAULT NULL,
  score int(11) NOT NULL DEFAULT 0,
  spins int(11) NOT NULL DEFAULT 0,
  jackpots int(11) NOT NULL DEFAULT 0,
  wager int(11) NOT NULL DEFAULT 1,
  high_roller tinyint(1) DEFAULT 0,
  xp int(11) DEFAULT 0,
  log_messages int(11) NOT NULL DEFAULT 0,
  xp_enabled BOOLEAN NOT NULL DEFAULT 1,
  receive_notifications BOOLEAN NOT NULL DEFAULT 1,
  loudbot_enabled BOOLEAN NOT NULL DEFAULT 0,
  level int(11) DEFAULT 1,
  PRIMARY KEY (id),
  UNIQUE KEY (discord_id)
);
CREATE TABLE IF NOT EXISTS user_preferences (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id VARCHAR(64) NOT NULL,
  badge_showcase_color VARCHAR(32) NOT NULL DEFAULT 'orange',
  badge_sets_color VARCHAR(32) NOT NULL DEFAULT 'teal',
  PRIMARY KEY (id),
  FOREIGN KEY (user_discord_id)
    REFERENCES users(discord_id)
);
CREATE TABLE IF NOT EXISTS profile_photos (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id VARCHAR(64) NOT NULL,
  photo VARCHAR(255) DEFAULT NULL,
  last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP() ON UPDATE CURRENT_TIMESTAMP(),
  PRIMARY KEY (id),
  UNIQUE KEY (user_discord_id)
);
CREATE TABLE IF NOT EXISTS profile_stickers (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id VARCHAR(64) NOT NULL,
  sticker VARCHAR(255) DEFAULT NULL,
  position VARCHAR(24) DEFAULT NULL,
  last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP() ON UPDATE CURRENT_TIMESTAMP(),
  PRIMARY KEY (id),
  UNIQUE KEY (user_discord_id)
);
CREATE TABLE IF NOT EXISTS profile_taglines (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id VARCHAR(64) NOT NULL,
  tagline VARCHAR(255) DEFAULT NULL,
  last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP() ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY (user_discord_id)
);
CREATE TABLE IF NOT EXISTS profile_badges (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id VARCHAR(64) NOT NULL,
  badge_filename VARCHAR(128) DEFAULT NULL,
  last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP() ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY (user_discord_id)
);
CREATE TABLE IF NOT EXISTS trades (
  id int(11) NOT NULL AUTO_INCREMENT,
  requestor_id varchar(128) NOT NULL,
  requestee_id varchar(128) NOT NULL,
  status varchar(64) NOT NULL DEFAULT 'pending',
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id),
  FOREIGN KEY (requestor_id)
    REFERENCES users(discord_id),
  FOREIGN KEY (requestee_id)
    REFERENCES users(discord_id)
);
CREATE TABLE IF NOT EXISTS badges (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id varchar(64) NOT NULL,
  badge_filename varchar(128) NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  locked BOOLEAN NOT NULL DEFAULT 0,
  PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS `badge_info` (
  `badge_filename` varchar(128) NOT NULL,
  `badge_name` varchar(128) NOT NULL,
  `badge_url` varchar(256) NOT NULL,
  `quadrant` varchar(128) DEFAULT NULL,
  `time_period` varchar(128) DEFAULT NULL,
  `franchise` varchar(128) DEFAULT NULL,
  `reference` varchar(128) DEFAULT NULL,
  PRIMARY KEY (`badge_filename`)
);
CREATE TABLE IF NOT EXISTS badge_affiliation (
  `id` int NOT NULL AUTO_INCREMENT,
  `badge_filename` varchar(128) NOT NULL,
  `affiliation_name` varchar(128) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `badge_filename` (`badge_filename`),
  CONSTRAINT `badge_affiliation_fk_badge_filename` FOREIGN KEY (`badge_filename`) REFERENCES `badge_info` (`badge_filename`)
);
CREATE TABLE IF NOT EXISTS badge_type (
  `id` int NOT NULL AUTO_INCREMENT,
  `badge_filename` varchar(128) NOT NULL,
  `type_name` varchar(128) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `badge_filename` (`badge_filename`),
  CONSTRAINT `badge_type_fk_badge_filename` FOREIGN KEY (`badge_filename`) REFERENCES `badge_info` (`badge_filename`)
);
CREATE TABLE IF NOT EXISTS badge_universe (
  `id` int NOT NULL AUTO_INCREMENT,
  `badge_filename` varchar(128) NOT NULL,
  `universe_name` varchar(128) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `badge_filename` (`badge_filename`),
  CONSTRAINT `badge_universe_fk_badge_filename` FOREIGN KEY (`badge_filename`) REFERENCES `badge_info` (`badge_filename`)
);
CREATE TABLE IF NOT EXISTS trade_offered (
  id int(11) NOT NULL AUTO_INCREMENT,
  badge_filename VARCHAR(128) NOT NULL,
  trade_id int(11) NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id),
  FOREIGN KEY (badge_filename)
    REFERENCES badge_info(badge_filename),
  FOREIGN KEY (trade_id)
    REFERENCES trades(id)
);
CREATE TABLE IF NOT EXISTS trade_requested (
  id int(11) NOT NULL AUTO_INCREMENT,
  badge_filename VARCHAR(128) NOT NULL,
  trade_id int(11) NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id),
  FOREIGN KEY (badge_filename)
    REFERENCES badge_info(badge_filename),
  FOREIGN KEY (trade_id)
    REFERENCES trades(id)
);
CREATE TABLE IF NOT EXISTS `badge_scraps` (
  `id` int NOT NULL AUTO_INCREMENT,
  `badge_filename` varchar(128) NOT NULL,
  `user_discord_id` varchar(128) NOT NULL,
  `time_created` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `badge_filename` (`badge_filename`),
  CONSTRAINT `badge_scraps_fk_badge_filename` FOREIGN KEY (`badge_filename`) REFERENCES `badge_info` (`badge_filename`)
);
CREATE TABLE IF NOT EXISTS `badge_scrapped` (
    `id` int NOT NULL AUTO_INCREMENT,
    `scrap_id` int(11) NOT NULL,
    `badge_filename` varchar(128) NOT NULL,
    `time_created` timestamp NOT NULL DEFAULT current_timestamp(),
    PRIMARY KEY (`id`),
    KEY `badge_filename` (`badge_filename`),
    FOREIGN KEY (`scrap_id`) REFERENCES `badge_scraps` (`id`),
    FOREIGN KEY (`badge_filename`) REFERENCES `badge_info` (`badge_filename`)
);
CREATE TABLE IF NOT EXISTS reactions (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_id varchar(64) NOT NULL,
  user_name varchar(64) NOT NULL,
  reaction varchar(128) NOT NULL,
  reaction_message_id varchar(64) NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id),
  CONSTRAINT USERID_REACTION_MESSAGEID UNIQUE (user_id, reaction, reaction_message_id)
);
CREATE TABLE IF NOT EXISTS starboard_posts (
  id int(11) NOT NULL AUTO_INCREMENT,
  message_id varchar(64) NOT NULL,
  user_id varchar(64) NOT NULL,
  board_channel varchar(128) NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS xp_history (
  id int(11) NOT NULL AUTO_INCREMENT,
  channel_id varchar(64) NOT NULL,
  user_discord_id varchar(64) NOT NULL,
  amount int(11) NOT NULL,
  reason varchar(32) NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS message_history (
  id int(11) NOT NULL AUTO_INCREMENT,
  channel_id varchar(64) NOT NULL,
  user_discord_id varchar(64) NOT NULL,
  message_text text NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS shouts (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id varchar(64) NOT NULL,
  channel_id varchar(64) NOT NULL,
  shout varchar(128) NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id),
  UNIQUE KEY (shout)
);
CREATE TABLE IF NOT EXISTS badge_wishlists (
  `id` int NOT NULL AUTO_INCREMENT,
  `badge_filename` varchar(128) NOT NULL,
  `user_discord_id` varchar(128) NOT NULL,
  `time_created` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `badge_filename` (`badge_filename`),
  CONSTRAINT `badge_wishlists_fk_badge_filename` FOREIGN KEY (`badge_filename`) REFERENCES `badge_info` (`badge_filename`)
);
CREATE TABLE IF NOT EXISTS poshimo_players (
  'id' INT NOT NULL AUTO_INCREMENT,
  'user_id' INT NOT NULL,
  'wins' INT DEFAULT 0,
  'losses' INT DEFAULT 0,
  'status' VARCHAR(64) DEFAULT NULL,
  'location' VARCHAR(128) DEFAULT NULL,
  'shimodapedia' TEXT DEFAULT NULL,
  'poshimodae' TEXT DEFAULT NULL,
  'inventory' TEXT DEFAULT NULL,
  'buckles' TEXT DEFAULT NULL,
  'money' INT DEFAULT 0 NOT NULL,
  'time_created' TIMESTAMP NOT NULL DEFAULT current_timestamp(),
   PRIMARY KEY (id),
   FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS poshimodae (
  'id' INT NOT NULL AUTO_INCREMENT,
  'owner_id' INT NOT NULL,
  'name' VARCHAR(128) NOT NULL,
  'display_name' VARCHAR(128) DEFAULT NULL,
  'level' INT NOT NULL DEFAULT 1,
  'xp' INT NOT NULL DEFAULT 0,
  'time_created' TIMESTAMP NOT NULL DEFAULT current_timestamp(),
  PRIMARY_KEY(id),
  FOREIGN_KEY(owner_id) REFERENCES poshimo_players(id)
);
CREATE TABLE IF NOT EXISTS poshimo_battles (
  'id' INT NOT NULL AUTO_INCREMENT,
  'combatant1' INT NOT NULL,
  'combatant2' INT NOT NULL,
  'turn' INT NOT NULL,
  'status' VARCHAR(128) NOT NULL,
  'outcome' VARCHAR(128) NOT NULL,
  'time_started' TIMESTAMP DEFAULT current_timestamp(),
  'time_ended' TIMESTAMP DEFAULT NULL,
  PRIMARY_KEY(id),
  FOREIGN KEY (combatant1) REFERENCES poshimo_players(id),
  FOREIGN KEY (combatant2) REFERENCES poshimo_players(id)
);
CREATE TABLE IF NOT EXISTS poshimo_battle_logs (
  'id' INT NOT NULL AUTO_INCREMENT,
  'battle_id' INT NOT NULL,
  'combatant1' INT NOT NULL,
  'combatant2' INT NOT NULL,
  'turn' INT NOT NULL,
  'event' TEXT NOT NULL,
  PRIMARY KEY (id),
  FOREIGN KEY (battle_id) REFERENCES poshimo_battles(id),
  FOREIGN KEY (combatant1) REFERENCES poshimo_players(id),
  FOREIGN KEY (combatant2) REFERENCES poshimo_players(id),
)