UPDATE badge_info SET badge_url = 'https://www.startrekdesignproject.com/symbols/risian-beach-resort' WHERE badge_url = 'https://www.startrekdesignproject.com/symbols/risan-beach-resort';

-- Add 'error' to the status enum in tongo_games
ALTER TABLE tongo_games
MODIFY COLUMN status ENUM(
  'open',
  'in_progress',
  'resolved',
  'cancelled',
  'error'
) NOT NULL;