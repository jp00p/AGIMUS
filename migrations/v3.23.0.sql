ALTER TABLE crystal_instances
  MODIFY COLUMN status ENUM('available', 'attuned', 'harmonized', 'rematerialized')
  NOT NULL
  DEFAULT 'available';

ALTER TABLE crystal_instance_history
  MODIFY COLUMN event_type ENUM(
    'replicated',
    'trade',
    'attuned',
    'admin',
    'dematerialized',
    'rematerialization'
  )
  NOT NULL;

CREATE TABLE IF NOT EXISTS crystal_rematerializations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_discord_id VARCHAR(64) NOT NULL,
  source_rank_id INT NOT NULL,
  target_rank_id INT NOT NULL,
  status ENUM('active', 'completed', 'cancelled') DEFAULT 'active',
  active BOOLEAN GENERATED ALWAYS AS (status = 'active') STORED,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  completed_at TIMESTAMP NULL DEFAULT NULL,

  FOREIGN KEY (user_discord_id) REFERENCES users(discord_id),
  FOREIGN KEY (source_rank_id) REFERENCES crystal_ranks(id),
  FOREIGN KEY (target_rank_id) REFERENCES crystal_ranks(id),
  UNIQUE KEY uq_user_active_rematerialization (user_discord_id, active)
);

CREATE TABLE IF NOT EXISTS crystal_rematerialization_items (
  id INT AUTO_INCREMENT PRIMARY KEY,
  rematerialization_id INT NOT NULL,
  crystal_instance_id INT NOT NULL,
  added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (rematerialization_id) REFERENCES crystal_rematerializations(id) ON DELETE CASCADE,
  FOREIGN KEY (crystal_instance_id) REFERENCES crystal_instances(id)
);

ALTER TABLE users ADD COLUMN ping_on_badge BOOLEAN NOT NULL DEFAULT 1;