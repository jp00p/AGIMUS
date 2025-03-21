/*
  Any existing users that have "Vulcan-IDIC-2370s.png" but not "Vulcan_IDIC_2370s.png"
  should instead simply have "Vulcan_IDIC_2370s.png"
*/
UPDATE badges
SET badge_filename = 'Vulcan_IDIC_2370s.png'
WHERE badge_filename = 'Vulcan-IDIC-2370s.png'
  AND user_discord_id NOT IN (
    SELECT user_discord_id
    FROM (SELECT user_discord_id FROM badges WHERE badge_filename = 'Vulcan_IDIC_2370s.png') AS subquery
  );
/*
  Now delete all the badge information about "Vulcan-IDIC-2370s.png"
*/
DELETE FROM badge_affiliation WHERE badge_filename = "Vulcan-IDIC-2370s.png";
DELETE FROM badge_type WHERE badge_filename = "Vulcan-IDIC-2370s.png";
DELETE FROM badge_universe WHERE badge_filename = "Vulcan-IDIC-2370s.png";
DELETE FROM badge_info WHERE badge_filename = "Vulcan-IDIC-2370s.png";
/*
  Delete misc entries
*/
DELETE FROM badge_wishlists WHERE badge_filename = "Vulcan-IDIC-2370s.png";
DELETE FROM profile_badges WHERE badge_filename = "Vulcan-IDIC-2370s.png";
DELETE FROM tongo_pot WHERE badge_filename = "Vulcan-IDIC-2370s.png";
DELETE FROM tags_carousel_position WHERE badge_filename = "Vulcan-IDIC-2370s.png";
/*
  Then delete all instances of "Vulcan-IDIC-2370s.png"
  to remove the dupes from users' inventories
*/
DELETE FROM badges WHERE badge_filename = "Vulcan-IDIC-2370s.png";
