CREATE TABLE IF NOT EXISTS dakota_events (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  event_date DATE NOT NULL,
  event_time VARCHAR(64) NOT NULL DEFAULT '',
  performer_name VARCHAR(255) NOT NULL,
  genre VARCHAR(255) NULL,
  description_short TEXT NULL,
  source_url VARCHAR(500) NOT NULL,
  scraped_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uq_event_occurrence (event_date, event_time, performer_name)
);
