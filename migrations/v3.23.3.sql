ALTER TABLE crystal_rematerializations
  ADD KEY idx_remat_user_discord_id (user_discord_id);

ALTER TABLE crystal_rematerializations
  DROP INDEX uq_user_active_rematerialization;

ALTER TABLE crystal_rematerializations
  ADD COLUMN active_user_discord_id VARCHAR(64)
    GENERATED ALWAYS AS (
      CASE
        WHEN status = 'active' THEN user_discord_id
        ELSE NULL
      END
    ) STORED,
  ADD UNIQUE KEY uq_user_active_rematerialization (active_user_discord_id);
