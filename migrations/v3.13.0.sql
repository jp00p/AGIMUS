UPDATE badge_info
SET badge_url = REPLACE(badge_url, 'united-federation-of-planets-ufp', 'united-federation-of-planets-(ufp)')
WHERE badge_url LIKE '%united-federation-of-planets-ufp%';

UPDATE badge_info
SET badge_url = REPLACE(badge_url, 'federation-news-network-fnn', 'federation-news-network-(fnn)')
WHERE badge_url LIKE '%federation-news-network-fnn%';