-- ==========================================================================
-- GENIEPOLIS · Databricks Unity Catalog setup
-- Run in a Databricks SQL editor / notebook (Free Edition works).
-- All data loaded here is SYNTHETIC DEMONSTRATION DATA for a fictional
-- rendering of BMS College of Engineering. Do not present as real data.
-- ==========================================================================

CREATE CATALOG IF NOT EXISTS geniepolis;
CREATE SCHEMA  IF NOT EXISTS geniepolis.campus;
USE CATALOG geniepolis;
USE SCHEMA campus;

-- --------------------------------------------------------------------------
-- Core tables.  The easiest load path on Free Edition:
--   1. run  `python databricks/export_csvs.py`  locally  -> databricks/exports/*.csv
--   2. in Databricks: Data > Create table > Upload files, target = geniepolis.campus
--   3. keep the table names below (Genie instructions reference them)
-- --------------------------------------------------------------------------

-- If you prefer DDL + COPY INTO from a volume, the schemas are:

CREATE TABLE IF NOT EXISTS buildings (
  id STRING, name STRING, type STRING, capacity INT, rooms INT,
  x INT, y INT, w INT, h INT
) COMMENT 'Campus buildings/entities with 2.5D map coordinates. Synthetic.';

CREATE TABLE IF NOT EXISTS rooms (
  room_id STRING, building_id STRING, capacity INT, kind STRING
) COMMENT 'Rooms per building. Synthetic.';

CREATE TABLE IF NOT EXISTS classes (
  class_id STRING, building_id STRING, room_id STRING,
  start_time STRING, end_time STRING, student_count INT, faculty_id STRING
) COMMENT 'Scheduled classes. Synthetic.';

CREATE TABLE IF NOT EXISTS faculty (
  faculty_id STRING, building_id STRING, department STRING,
  office_room STRING, classes INT, status STRING
) COMMENT 'Faculty, home building and current status (in_class/in_office/...). Synthetic.';

CREATE TABLE IF NOT EXISTS workers (
  worker_id STRING, building_id STRING, work_type STRING,
  shift STRING, workload DOUBLE
) COMMENT 'Support staff (housekeeping/security/catering/...). Synthetic.';

CREATE TABLE IF NOT EXISTS occupancy (
  hour INT, building_id STRING, students INT, faculty INT, workers INT,
  visitors INT, occupancy INT, capacity INT, occupancy_rate DOUBLE
) COMMENT 'Hourly occupancy per building, 06:00-22:00. Synthetic.';

CREATE TABLE IF NOT EXISTS traffic (
  hour INT, road_id STRING, vehicles INT, average_speed DOUBLE, congestion DOUBLE
) COMMENT 'Hourly road congestion (0..1). Synthetic.';

CREATE TABLE IF NOT EXISTS parking (
  hour INT, parking_id STRING, capacity INT, occupied INT,
  available INT, occupancy_rate DOUBLE
) COMMENT 'Hourly parking occupancy. Synthetic.';

CREATE TABLE IF NOT EXISTS washrooms (
  washroom_id STRING, building_id STRING, usage_rate DOUBLE,
  crowd_level STRING, maintenance_status STRING
) COMMENT 'Washroom usage and maintenance state. Synthetic.';

CREATE TABLE IF NOT EXISTS canteens (
  canteen_id STRING, building_id STRING, counters INT,
  queue_len INT, avg_wait_min DOUBLE, seats INT
) COMMENT 'Cafeteria queue and capacity. Synthetic.';

CREATE TABLE IF NOT EXISTS sports (
  sports_id STRING, building_id STRING, activity STRING,
  slots_total INT, slots_booked INT, participants INT
) COMMENT 'Sports facilities usage. Synthetic.';

CREATE TABLE IF NOT EXISTS transport (
  route_id STRING, stop STRING, peak_window STRING,
  buses_per_hour INT, riders INT
) COMMENT 'Bus routes and peak windows. Synthetic.';

CREATE TABLE IF NOT EXISTS events (
  event_id STRING, name STRING, building_id STRING, hour INT, expected INT
) COMMENT 'Scheduled campus events. Synthetic.';

CREATE TABLE IF NOT EXISTS issues (
  issue_id STRING, type STRING, building_id STRING, severity STRING, hour INT
) COMMENT 'Reported campus issues. Synthetic.';

CREATE TABLE IF NOT EXISTS wish_history (
  wish_id STRING, domain STRING, wish_text STRING,
  hour INT, affected_group STRING
) COMMENT 'Historical student wishes -> drives Campus Pulse. Synthetic.';

CREATE TABLE IF NOT EXISTS impact_relationships (
  source STRING, target STRING, relationship STRING,
  weight DOUBLE, explanation STRING
) COMMENT 'Campus butterfly-effect graph. Genie may EXPLAIN edges; it must not simulate outcomes.';

-- Quick sanity checks -------------------------------------------------------
-- SELECT building_id, occupancy_rate FROM occupancy WHERE hour = 16 ORDER BY occupancy_rate DESC;
-- SELECT wish_text, COUNT(*) c FROM wish_history GROUP BY wish_text ORDER BY c DESC;
-- SELECT * FROM impact_relationships WHERE source = 'class_start_time';
