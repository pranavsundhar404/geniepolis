-- ==========================================================================
-- GENIEPOLIS · Example questions + the SQL Genie should generate
--
-- Two uses:
--   1. Paste the QUESTION lines into the Genie space -> "Example questions".
--   2. Paste each QUESTION + QUERY pair into the Genie space ->
--      Instructions -> "SQL queries" / "Example SQL queries"  (name = question,
--      body = the SELECT). This makes Genie far more accurate.
--
-- Schema recap (all in  geniepolis.campus):
--   buildings(id,name,type,capacity,rooms,x,y,w,h)
--   rooms(room_id,building_id,capacity,kind)               kind: lecture/lab/office/seminar
--   classes(class_id,building_id,room_id,start_time,end_time,student_count,faculty_id)
--   faculty(faculty_id,building_id,department,office_room,classes,status)
--                                                          status: in_class/in_office/off_campus/meeting
--   workers(worker_id,building_id,work_type,shift,workload)
--   occupancy(hour,building_id,students,faculty,workers,visitors,occupancy,capacity,occupancy_rate)
--   traffic(hour,road_id,vehicles,average_speed,congestion) road_id: spine/ring_w/ring_e/gate_link
--   parking(hour,parking_id,capacity,occupied,available,occupancy_rate) parking_id: parking_a/parking_b
--   washrooms(washroom_id,building_id,usage_rate,crowd_level,maintenance_status)
--   canteens(canteen_id,building_id,counters,queue_len,avg_wait_min,seats)
--   sports(sports_id,building_id,activity,slots_total,slots_booked,participants)
--   transport(route_id,stop,peak_window,buses_per_hour,riders)
--   events(event_id,name,building_id,hour,expected)
--   issues(issue_id,type,building_id,severity,hour)         severity: low/medium/high
--   wish_history(wish_id,domain,wish_text,hour,affected_group)
--   impact_relationships(source,target,relationship,weight,explanation)
--
--   The demo "now" is  hour = 16 (4 PM).
--   *_rate / congestion columns are fractions 0..1.
-- ==========================================================================


-- ---- CAMPUS STATE --------------------------------------------------------

-- Q: Which buildings have the highest occupancy right now?
SELECT b.name, o.occupancy_rate, o.occupancy, o.capacity
FROM geniepolis.campus.occupancy o
JOIN geniepolis.campus.buildings b ON b.id = o.building_id
WHERE o.hour = 16
ORDER BY o.occupancy_rate DESC
LIMIT 5;

-- Q: How does the Main Academic Block fill up over the day?
SELECT hour, occupancy_rate, students, faculty
FROM geniepolis.campus.occupancy
WHERE building_id = 'academic_block'
ORDER BY hour;

-- Q: How many students, faculty, workers and visitors are on campus at 4 PM?
SELECT SUM(students) AS students, SUM(faculty) AS faculty,
       SUM(workers) AS workers, SUM(visitors) AS visitors
FROM geniepolis.campus.occupancy
WHERE hour = 16;


-- ---- ACADEMICS ---------------------------------------------------------

-- Q: Which building runs the most classes?
SELECT b.name, COUNT(*) AS classes_scheduled, SUM(c.student_count) AS students
FROM geniepolis.campus.classes c
JOIN geniepolis.campus.buildings b ON b.id = c.building_id
GROUP BY b.name
ORDER BY classes_scheduled DESC;

-- Q: How many classes start at each time slot?
SELECT start_time, COUNT(*) AS num_classes, SUM(student_count) AS students
FROM geniepolis.campus.classes
GROUP BY start_time
ORDER BY start_time;

-- Q: How many rooms does each building have, and how many are labs?
SELECT b.name,
       COUNT(*) AS total_rooms,
       SUM(CASE WHEN r.kind = 'lab' THEN 1 ELSE 0 END) AS labs
FROM geniepolis.campus.rooms r
JOIN geniepolis.campus.buildings b ON b.id = r.building_id
GROUP BY b.name
ORDER BY total_rooms DESC;

-- Q: How many faculty members are in the academic block, and what are they doing?
SELECT status, COUNT(*) AS faculty
FROM geniepolis.campus.faculty
WHERE building_id = 'academic_block'
GROUP BY status
ORDER BY faculty DESC;


-- ---- MOBILITY (traffic / parking / buses) -----------------------------

-- Q: What time is campus traffic highest?
SELECT hour, ROUND(AVG(congestion), 3) AS avg_congestion
FROM geniepolis.campus.traffic
GROUP BY hour
ORDER BY avg_congestion DESC
LIMIT 3;

-- Q: Which road is most congested in the evening?
SELECT road_id, congestion, vehicles, average_speed
FROM geniepolis.campus.traffic
WHERE hour = 17
ORDER BY congestion DESC;

-- Q: Which parking zone is busiest at 4 PM?
SELECT b.name, p.occupied, p.available, p.capacity, p.occupancy_rate
FROM geniepolis.campus.parking p
JOIN geniepolis.campus.buildings b ON b.id = p.parking_id
WHERE p.hour = 16
ORDER BY p.occupancy_rate DESC;

-- Q: When is parking most full during the day?
SELECT hour, ROUND(AVG(occupancy_rate), 3) AS avg_occupancy
FROM geniepolis.campus.parking
GROUP BY hour
ORDER BY avg_occupancy DESC
LIMIT 5;

-- Q: What are the bus peak windows and how many riders?
SELECT route_id, stop, peak_window, buses_per_hour, riders
FROM geniepolis.campus.transport
ORDER BY riders DESC;


-- ---- FACILITIES (washrooms / cafeteria / sports) --------------------

-- Q: Which washrooms need attention?
SELECT b.name, w.washroom_id, w.usage_rate, w.crowd_level, w.maintenance_status
FROM geniepolis.campus.washrooms w
JOIN geniepolis.campus.buildings b ON b.id = w.building_id
WHERE w.maintenance_status <> 'ok' OR w.crowd_level IN ('HIGH', 'CRITICAL')
ORDER BY w.usage_rate DESC;

-- Q: How long is the cafeteria queue and wait?
SELECT canteen_id, counters, queue_len, avg_wait_min, seats
FROM geniepolis.campus.canteens;

-- Q: How full are the sports facilities?
SELECT b.name, s.activity, s.slots_booked, s.slots_total, s.participants
FROM geniepolis.campus.sports s
JOIN geniepolis.campus.buildings b ON b.id = s.building_id
ORDER BY s.participants DESC;

-- Q: What events are scheduled and how many people are expected?
SELECT name, building_id, hour, expected
FROM geniepolis.campus.events
ORDER BY hour;


-- ---- CAMPUS PULSE (wishes + issues) --------------------------------

-- Q: What are the most requested campus improvements?
SELECT wish_text, COUNT(*) AS requests
FROM geniepolis.campus.wish_history
GROUP BY wish_text
ORDER BY requests DESC
LIMIT 5;

-- Q: How many students requested better parking?
SELECT COUNT(*) AS requests
FROM geniepolis.campus.wish_history
WHERE domain = 'parking';

-- Q: Which wishes have crossed the 50-request campus-signal threshold?
SELECT wish_text, COUNT(*) AS requests
FROM geniepolis.campus.wish_history
GROUP BY wish_text
HAVING COUNT(*) >= 50
ORDER BY requests DESC;

-- Q: Which campus issue is reported most frequently?
SELECT type, COUNT(*) AS reports
FROM geniepolis.campus.issues
GROUP BY type
ORDER BY reports DESC
LIMIT 5;

-- Q: Which buildings have the most reported issues?
SELECT b.name, COUNT(*) AS issues
FROM geniepolis.campus.issues i
JOIN geniepolis.campus.buildings b ON b.id = i.building_id
GROUP BY b.name
ORDER BY issues DESC
LIMIT 5;


-- ---- RELATIONSHIPS (explain, don't simulate) ----------------------

-- Q: What does a change in class start time affect?
SELECT target, relationship, weight, explanation
FROM geniepolis.campus.impact_relationships
WHERE source = 'class_start_time'
ORDER BY weight DESC;

-- Q: What happens to parking demand and traffic when evening activity increases?
SELECT source, target, relationship, weight, explanation
FROM geniepolis.campus.impact_relationships
WHERE target IN ('parking_demand', 'road_traffic')
ORDER BY weight DESC;

-- Q: What are all the knock-on effects if we move the campus gate?
SELECT target, relationship, weight, explanation
FROM geniepolis.campus.impact_relationships
WHERE source = 'gate_location'
ORDER BY weight DESC;
