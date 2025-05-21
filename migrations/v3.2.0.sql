UPDATE crystal_ranks SET name = 'unobtanium' WHERE LOWER(name) = 'unobtanium';

UPDATE badge_instances SET locked = TRUE WHERE badge_info_id IN (SELECT id FROM badge_info WHERE special = TRUE);

DELETE FROM badge_instances_wishlists WHERE badge_info_id IN ( SELECT id FROM badge_info WHERE special = TRUE);