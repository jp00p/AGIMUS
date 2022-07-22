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
CREATE TABLE IF NOT EXISTS users (
  id int(11) NOT NULL AUTO_INCREMENT,
  discord_id varchar(64) NOT NULL,
  name varchar(128) DEFAULT NULL,
  mention varchar(128) DEFAULT NULL,
  score int(11) NOT NULL DEFAULT 0,
  spins int(11) NOT NULL DEFAULT 0,
  jackpots int(11) NOT NULL DEFAULT 0,
  wager int(11) NOT NULL DEFAULT 1,
  profile_card longtext DEFAULT NULL,
  profile_badge varchar(255) DEFAULT NULL,
  high_roller tinyint(1) DEFAULT 0,
  chips varchar(255) DEFAULT '10',
  xp int(11) DEFAULT 0,
  log_messages int(11) NOT NULL DEFAULT 0,
  xp_enabled BOOLEAN NOT NULL DEFAULT 1,
  tagline VARCHAR(255) DEFAULT NULL,
  level int(11) DEFAULT 1,  
  PRIMARY KEY (id),
  UNIQUE KEY (discord_id)
);
CREATE TABLE IF NOT EXISTS badges (
  id int(11) NOT NULL AUTO_INCREMENT,
  user_discord_id varchar(64) NOT NULL,
  badge_name varchar(128) NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS trades (
  id int(11) NOT NULL AUTO_INCREMENT,
  requestor_id varchar(128) NOT NULL,
  requestee_id varchar(128) NOT NULL,
  active BOOLEAN NOT NULL DEFAULT 0,
  pending BOOLEAN NOT NULL DEFAULT 1,
  completed BOOLEAN NOT NULL DEFAULT 0,
  rejected BOOLEAN NOT NULL DEFAULT 0,
  canceled BOOLEAN NOT NULL DEFAULT 0,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id),
  FOREIGN KEY (requestor_id)
    REFERENCES users(discord_id),
  FOREIGN KEY (requestee_id)
    REFERENCES users(discord_id)
);
CREATE TABLE IF NOT EXISTS badge_info (
  id int(11) NOT NULL AUTO_INCREMENT,
  badge_name varchar(128) NOT NULL,
  affiliation varchar(128) DEFAULT NULL,
  quadrant varchar(128) DEFAULT NULL,
  time_period varchar(128) DEFAULT NULL,
  universe varchar(128) DEFAULT NULL,
  franchise varchar(128) DEFAULT NULL,
  PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS trade_offered (
  id int(11) NOT NULL AUTO_INCREMENT,
  badge_id int(11) NOT NULL,
  trade_id int(11) NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id),
  FOREIGN KEY (badge_id)
    REFERENCES badge_info(id),
  FOREIGN KEY (trade_id)
    REFERENCES trades(id)
);
CREATE TABLE IF NOT EXISTS trade_requested (
  id int(11) NOT NULL AUTO_INCREMENT,
  badge_id int(11) NOT NULL,
  trade_id int(11) NOT NULL,
  time_created timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (id),
  FOREIGN KEY (badge_id)
    REFERENCES badge_info(id),
  FOREIGN KEY (trade_id)
    REFERENCES trades(id)
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