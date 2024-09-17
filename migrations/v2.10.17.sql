/*
  Any existing users that have "Vulcan-IDIC-2370s.png" but not "Vulcan_IDIC_2370s.png"
  should instead simply have "Vulcan_IDIC_2370s.png"
*/
UPDATE badges SET badge_filename = "Vulcan_IDIC_2370s.png"
  WHERE badge_filename = "Vulcan-IDIC-2370s.png"
    AND discord_user_id NOT IN (
      SELECT discord_user_id
      FROM badges
      WHERE badge_filename = "Vulcan_IDIC_2370s.png"
    );
/*
  Now delete all the badge information about "Vulcan-IDIC-2370s.png"
*/
DELETE FROM badge_affiliation WHERE badge_filename = "Vulcan-IDIC-2370s.png";
DELETE FROM badge_type WHERE badge_filename = "Vulcan-IDIC-2370s.png";
DELETE FROM badge_universe WHERE badge_filename = "Vulcan-IDIC-2370s.png";
DELETE FROM badge_info WHERE badge_filename = "Vulcan-IDIC-2370s.png";
/*
  Then delete all instances of "Vulcan-IDIC-2370s.png"
  to remove the dupes from users' inventories
*/
DELETE FROM badges WHERE badge_filename = "Vulcan-IDIC-2370s.png";