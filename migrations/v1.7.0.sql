ALTER TABLE users ADD COLUMN loudbot_enabled BOOLEAN NOT NULL DEFAULT 0 AFTER receive_notifications;