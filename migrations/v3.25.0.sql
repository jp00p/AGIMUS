ALTER TABLE users
  ADD COLUMN wishlist_dm_enabled BOOLEAN NOT NULL DEFAULT 1 AFTER ping_on_badge;
