-- Migration 0001: detection review workflow + calibrated frequency columns.
--
-- Adds to DETECTIONS:
--   freq_min      FLOAT NULL
--   freq_max      FLOAT NULL
--   review_status ENUM('pending','confirmed','rejected') NOT NULL DEFAULT 'pending'
--   reviewed_by   INT NULL
--   reviewed_at   TIMESTAMP NULL
-- plus a supporting index on review_status (used by the explorer/dashboard filters).
--
-- Written for MySQL 8.0 (see docker-compose.yml). Safe to run multiple times and
-- safe to run against the already-populated `DATA` database (19 files, 5211
-- detections at the time of writing): every change is additive (no DROP, no
-- rewrite of existing rows) and guarded by an INFORMATION_SCHEMA check so it can
-- be re-applied without error if some columns already exist.
--
-- How this is applied:
--   - Fresh install (empty db/osadecdb datadir): docker-compose.yml mounts this
--     file under /docker-entrypoint-initdb.d/, so it runs automatically, right
--     after init_db.sql and load_data.sql.
--   - Existing datadir (already initialized, as it is today): MySQL's
--     docker-entrypoint-initdb.d scripts only run once, against an empty
--     datadir, so this file will NOT be re-run automatically. Apply it by hand
--     once — see docs/db_migrations.md.

USE `DATA`;

SET @schema := DATABASE();

-- freq_min
SET @sql := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @schema AND TABLE_NAME = 'DETECTIONS' AND COLUMN_NAME = 'freq_min') = 0,
  'ALTER TABLE `DETECTIONS` ADD COLUMN `freq_min` FLOAT NULL AFTER `confidence`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- freq_max
SET @sql := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @schema AND TABLE_NAME = 'DETECTIONS' AND COLUMN_NAME = 'freq_max') = 0,
  'ALTER TABLE `DETECTIONS` ADD COLUMN `freq_max` FLOAT NULL AFTER `freq_min`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- review_status
SET @sql := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @schema AND TABLE_NAME = 'DETECTIONS' AND COLUMN_NAME = 'review_status') = 0,
  "ALTER TABLE `DETECTIONS` ADD COLUMN `review_status` ENUM('pending','confirmed','rejected') NOT NULL DEFAULT 'pending' AFTER `freq_max`",
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- reviewed_by
SET @sql := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @schema AND TABLE_NAME = 'DETECTIONS' AND COLUMN_NAME = 'reviewed_by') = 0,
  'ALTER TABLE `DETECTIONS` ADD COLUMN `reviewed_by` INT NULL AFTER `review_status`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- reviewed_at
SET @sql := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @schema AND TABLE_NAME = 'DETECTIONS' AND COLUMN_NAME = 'reviewed_at') = 0,
  'ALTER TABLE `DETECTIONS` ADD COLUMN `reviewed_at` TIMESTAMP NULL AFTER `reviewed_by`',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Supporting index for filtering by review status (dashboard/explorer, Phase 2).
SET @sql := IF(
  (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = @schema AND TABLE_NAME = 'DETECTIONS' AND INDEX_NAME = 'idx_detections_review_status') = 0,
  'CREATE INDEX `idx_detections_review_status` ON `DETECTIONS` (`review_status`)',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
