-- ------------------------------------------------------------
-- BEGIN SECTION A: NEW BADGE METADATA
-- ------------------------------------------------------------

-- Create a new badge_info table, now with blackjack and hookers
-- More specifically, removing id, making badge_filename the PK and moving badge_filename to the top of the table.
CREATE TABLE `badge_info_new` LIKE `badge_info`;
INSERT INTO `badge_info_new` SELECT * FROM badge_info;
ALTER TABLE badge_info_new DROP COLUMN `id`;
ALTER TABLE badge_info_new ADD PRIMARY KEY (`badge_filename`);
ALTER TABLE badge_info_new CHANGE COLUMN badge_name badge_name VARCHAR(128) NOT NULL AFTER badge_filename;

-- Create new badge_affiliation and populate from old one
CREATE TABLE `badge_affiliation_new`
(
    `id`               int          NOT NULL AUTO_INCREMENT,
    `badge_filename`   varchar(128) NOT NULL,
    `affiliation_name` varchar(128) NOT NULL,
    PRIMARY KEY (`id`),
    KEY `badge_filename` (`badge_filename`),
    CONSTRAINT `badge_affiliation_fk_badge_filename` FOREIGN KEY (`badge_filename`) REFERENCES `badge_info_new` (`badge_filename`)
);

INSERT INTO badge_affiliation_new (badge_filename, affiliation_name)
SELECT
    badge_info.badge_filename,
    badge_affiliation.affiliation_name
    FROM badge_info
    INNER JOIN badge_affiliation ON badge_info.id = badge_affiliation.badge_id;

-- Create new badge_type and populate from old one
CREATE TABLE `badge_type_new`
(
    `id`             int          NOT NULL AUTO_INCREMENT,
    `badge_filename` varchar(128) NOT NULL,
    `type_name`      varchar(128) NOT NULL,
    PRIMARY KEY (`id`),
    KEY `badge_filename` (`badge_filename`),
    CONSTRAINT `badge_type_fk_badge_filename` FOREIGN KEY (`badge_filename`) REFERENCES `badge_info_new` (`badge_filename`)
);

INSERT INTO badge_type_new (badge_filename, type_name)
SELECT
    badge_info.badge_filename,
    badge_type.type_name
    FROM badge_info
    INNER JOIN badge_type ON badge_info.id = badge_type.badge_id;

-- Create new badge universe and populate from old one
CREATE TABLE `badge_universe_new`
(
    `id`             int          NOT NULL AUTO_INCREMENT,
    `badge_filename` varchar(128) NOT NULL,
    `universe_name`  varchar(128) NOT NULL,
    PRIMARY KEY (`id`),
    KEY `badge_filename` (`badge_filename`),
    CONSTRAINT `badge_universe_fk_badge_filename` FOREIGN KEY (`badge_filename`) REFERENCES `badge_info_new` (`badge_filename`)
);

INSERT INTO badge_universe_new (badge_filename, universe_name)
SELECT
    badge_info.badge_filename,
    badge_universe.universe_name
FROM badge_info
INNER JOIN badge_universe ON badge_info.id = badge_universe.badge_id;


-- ------------------------------------------------------------
-- END SECTION A: NEW BADGE METADATA
-- ------------------------------------------------------------

-- ------------------------------------------------------------
-- BEGIN SECTION B: UPDATE BADGE REFERENCES
-- ------------------------------------------------------------

-- trade_offered
CREATE TABLE IF NOT EXISTS trade_offered_new
(
    id             int(11)      NOT NULL AUTO_INCREMENT,
    badge_filename VARCHAR(128) NOT NULL,
    trade_id       int(11)      NOT NULL,
    time_created   timestamp    NOT NULL DEFAULT current_timestamp(),
    PRIMARY KEY (id),
    FOREIGN KEY (badge_filename)
        REFERENCES badge_info_new (badge_filename),
    FOREIGN KEY (trade_id)
        REFERENCES trades (id)
);
INSERT INTO trade_offered_new (id, badge_filename, trade_id, time_created)
SELECT
    trade_offered.id,
    badge_info.badge_filename,
    trade_offered.trade_id,
    trade_offered.time_created
    FROM trade_offered
    INNER JOIN badge_info ON trade_offered.badge_id = badge_info.id;

-- trade_requested
CREATE TABLE IF NOT EXISTS trade_requested_new
(
    id             int(11)      NOT NULL AUTO_INCREMENT,
    badge_filename VARCHAR(128) NOT NULL,
    trade_id       int(11)      NOT NULL,
    time_created   timestamp    NOT NULL DEFAULT current_timestamp(),
    PRIMARY KEY (id),
    FOREIGN KEY (badge_filename)
        REFERENCES badge_info_new (badge_filename),
    FOREIGN KEY (trade_id)
        REFERENCES trades (id)
);
INSERT INTO trade_requested_new (id, badge_filename, trade_id, time_created)
SELECT
    trade_requested.id,
    badge_info.badge_filename,
    trade_requested.trade_id,
    trade_requested.time_created
    FROM trade_requested
    INNER JOIN badge_info ON trade_requested.badge_id = badge_info.id;

-- badges
CREATE TABLE `badges_new`
(
    `id`              int          NOT NULL AUTO_INCREMENT,
    `user_discord_id` varchar(64)  NOT NULL,
    `badge_filename`  varchar(128) NOT NULL,
    `time_created`    timestamp    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
);
INSERT INTO badges_new (id, user_discord_id, badge_filename, time_created) SELECT id, user_discord_id, badge_name as badge_filename, time_created FROM badges;

-- profile_badges;
CREATE TABLE `profile_badges_new`
(
    `id`              int         NOT NULL AUTO_INCREMENT,
    `user_discord_id` varchar(64) NOT NULL,
    `badge_filename`  varchar(128)         DEFAULT NULL,
    `last_modified`   timestamp   NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `user_discord_id` (`user_discord_id`)
);
INSERT INTO profile_badges_new (id, user_discord_id, badge_filename, last_modified) SELECT id, user_discord_id, badge_name, last_modified FROM profile_badges;

-- @TODO profile_badges should use badge_filename, not badge_name


-- @TODO swap table names

-- ------------------------------------------------------------
-- END SECTION B: UPDATE BADGE REFERENCES
-- ------------------------------------------------------------

-- ------------------------------------------------------------
-- START SECTION C: CLEANUP
-- ------------------------------------------------------------

-- Swap tables so previous ones are now "_old"
RENAME TABLE badge_info to badge_info_old, badge_info_new to badge_info;
RENAME TABLE badge_affiliation to badge_affiliation_old, badge_affiliation_new to badge_affiliation;
RENAME TABLE badge_type to badge_type_old, badge_type_new to badge_type;
RENAME TABLE badge_universe to badge_universe_old, badge_universe_new to badge_universe;

RENAME TABLE badges to badges_old, badges_new to badges;
RENAME TABLE profile_badges to profile_badges_old, profile_badges_new to profile_badges;
RENAME TABLE trade_offered to trade_offered_old, trade_offered_new to trade_offered;
RENAME TABLE trade_requested to trade_requested_old, trade_requested_new to trade_requested;


-- When you're happy, then uncomment and execute the following lines to remove the old tables.
DROP TABLE profile_badges_old;
DROP TABLE trade_offered_old;
DROP TABLE trade_requested_old;
DROP TABLE badges_old;
DROP TABLE badge_affiliation_old;
DROP TABLE badge_type_old;
DROP TABLE badge_universe_old;
DROP TABLE badge_info_old;

-- ------------------------------------------------------------
-- END SECTION C: CLEANUP
-- ------------------------------------------------------------
