"""
Synthetic campus data generator for GENIEPOLIS.

Everything here is generated deterministically (np.random.seed(42)) so the demo
is reproducible. NONE of it is real institutional data.

Returns a dict of pandas DataFrames + a "snapshot" dict of current conditions
per building (what the clickable info panels show).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from data.campus_data import BUILDINGS, BUILDING_BY_ID

SEED = 42
CURRENT_HOUR = 16  # the campus "now" for the demo is 4 PM (evening pressure)

DEPARTMENTS = ["CSE", "ISE", "ECE", "EEE", "MECH", "CIVIL", "AIML", "BT"]
WORK_TYPES = ["housekeeping", "security", "maintenance", "catering", "gardening", "lab_support"]
ISSUE_TYPES = [
    "Parking full after 4 PM", "Long cafeteria queue at lunch", "Washroom needs cleaning",
    "Bus arrives late in the morning", "Classroom projector not working", "Slow campus wifi",
    "Not enough study space in library", "Sports ground double-booked", "Water cooler empty",
    "Crowded corridor between classes",
]

# Wishes students "have already made" -> drives Campus Pulse
WISH_CATALOG = [
    ("parking", "Better peak-hour parking after 4 PM"),
    ("transport", "More buses between 9:00 and 9:45 AM"),
    ("cafeteria", "Shorter cafeteria queue at lunch"),
    ("schedule", "Start classes at 10 AM"),
    ("washroom", "Cleaner and better maintained washrooms"),
    ("sports", "More open sports slots on weekdays"),
    ("library", "Library open later at night"),
    ("infrastructure", "Move the bus stop closer to the academic block"),
    ("traffic", "Make the central road pedestrian-only"),
    ("wifi", "Faster wifi in the academic block"),
]


def _daycurve(hour, peak, width, base, amp):
    """Smooth bell-ish daily pattern."""
    return base + amp * np.exp(-((hour - peak) ** 2) / (2 * width ** 2))


def _occupancy_pattern(hour, btype):
    """Return an occupancy_rate 0..1 for a building type at a given hour."""
    h = hour
    if btype == "academic":
        r = max(_daycurve(h, 11, 2.4, 0.12, 0.78), _daycurve(h, 15, 2.2, 0.0, 0.62))
    elif btype == "faculty":
        r = _daycurve(h, 12, 3.0, 0.15, 0.6)
    elif btype == "library":
        r = _daycurve(h, 17, 3.5, 0.2, 0.7)
    elif btype == "cafeteria":
        r = max(_daycurve(h, 9, 0.9, 0.05, 0.55), _daycurve(h, 13, 1.1, 0.05, 0.95),
                _daycurve(h, 17, 1.3, 0.0, 0.5))
    elif btype == "auditorium":
        r = _daycurve(h, 15, 1.2, 0.03, 0.7)
    elif btype in ("sports",):
        r = max(_daycurve(h, 7, 1.2, 0.05, 0.5), _daycurve(h, 17.5, 1.6, 0.05, 0.95))
    elif btype == "hostel":
        r = 1.0 - _daycurve(h, 13, 3.5, 0.15, 0.6)
    elif btype == "admin":
        r = _daycurve(h, 12, 3.0, 0.1, 0.7)
    elif btype == "transport":
        r = max(_daycurve(h, 8.7, 0.7, 0.05, 0.95), _daycurve(h, 17, 1.0, 0.05, 0.9))
    elif btype == "parking":
        r = _daycurve(h, 13, 4.5, 0.25, 0.7)
    elif btype == "washroom":
        r = max(_daycurve(h, 11, 1.6, 0.15, 0.7), _daycurve(h, 13.5, 1.4, 0.0, 0.6))
    else:  # gate
        r = max(_daycurve(h, 8.7, 0.8, 0.05, 0.9), _daycurve(h, 17, 1.1, 0.05, 0.85))
    return float(np.clip(r, 0.02, 0.99))


def level(rate):
    if rate >= 0.9:
        return "CRITICAL"
    if rate >= 0.72:
        return "HIGH"
    if rate >= 0.45:
        return "MEDIUM"
    return "LOW"


def generate_all(seed: int = SEED) -> dict:
    rng = np.random.default_rng(seed)
    np.random.seed(seed)

    hours = list(range(6, 23))

    # ---------------- buildings ----------------
    buildings = pd.DataFrame(BUILDINGS)

    # ---------------- rooms ----------------
    rooms = []
    for b in BUILDINGS:
        for r in range(b["rooms"]):
            rooms.append(dict(
                room_id=f"{b['id']}-R{r+1:03d}", building_id=b["id"],
                capacity=int(rng.integers(24, 72)),
                kind=rng.choice(["lecture", "lab", "office", "seminar"], p=[0.5, 0.25, 0.15, 0.1]),
            ))
    rooms = pd.DataFrame(rooms)

    # ---------------- faculty ----------------
    faculty = []
    for i in range(160):
        home = rng.choice(["faculty_block", "academic_block", "innovation_center", "admin_block"],
                          p=[0.55, 0.3, 0.1, 0.05])
        status = rng.choice(["in_class", "in_office", "off_campus", "meeting"], p=[0.42, 0.33, 0.15, 0.10])
        faculty.append(dict(
            faculty_id=f"FAC{i+1:03d}", building_id=home,
            department=rng.choice(DEPARTMENTS), office_room=f"{home}-R{rng.integers(1, 40):03d}",
            classes=int(rng.integers(1, 5)), status=status,
        ))
    faculty = pd.DataFrame(faculty)

    # ---------------- workers ----------------
    workers = []
    for i in range(120):
        wt = rng.choice(WORK_TYPES)
        home = rng.choice([b["id"] for b in BUILDINGS])
        workers.append(dict(
            worker_id=f"WRK{i+1:03d}", building_id=home, work_type=wt,
            shift=rng.choice(["morning", "general", "evening"], p=[0.4, 0.4, 0.2]),
            workload=round(float(rng.uniform(0.35, 0.95)), 2),
        ))
    workers = pd.DataFrame(workers)

    # ---------------- classes ----------------
    classes = []
    start_slots = [8, 9, 10, 11, 12, 14, 15, 16]
    acad_rooms = rooms[rooms.building_id.isin(["academic_block", "innovation_center"])].room_id.tolist()
    for i in range(220):
        s = int(rng.choice(start_slots, p=[0.2, 0.2, 0.16, 0.13, 0.08, 0.09, 0.08, 0.06]))
        rid = rng.choice(acad_rooms)
        classes.append(dict(
            class_id=f"CLS{i+1:03d}", building_id=BUILDING_BY_ID_safe(rid),
            room_id=rid, start_time=f"{s:02d}:00", end_time=f"{s+1:02d}:00",
            student_count=int(rng.integers(28, 68)),
            faculty_id=f"FAC{rng.integers(1, 160):03d}",
        ))
    classes = pd.DataFrame(classes)

    # ---------------- hourly occupancy ----------------
    occ_rows = []
    for b in BUILDINGS:
        cap = max(b["capacity"], 1)
        for h in hours:
            rate = _occupancy_pattern(h, b["type"]) * float(rng.uniform(0.92, 1.08))
            rate = float(np.clip(rate, 0.02, 0.99))
            total = int(round(rate * cap))
            students = int(total * rng.uniform(0.62, 0.85)) if b["type"] not in ("faculty", "admin") else int(total * 0.15)
            fac = int(total * rng.uniform(0.05, 0.16))
            wrk = int(total * rng.uniform(0.03, 0.10))
            vis = max(total - students - fac - wrk, 0)
            occ_rows.append(dict(
                hour=h, building_id=b["id"], students=students, faculty=fac,
                workers=wrk, visitors=vis, occupancy=total, capacity=cap,
                occupancy_rate=round(rate, 3),
            ))
    occupancy = pd.DataFrame(occ_rows)

    # ---------------- traffic ----------------
    traffic_rows = []
    for road in ["spine", "ring_w", "ring_e", "gate_link"]:
        for h in hours:
            cong = max(_daycurve(h, 8.8, 0.9, 0.15, 0.8), _daycurve(h, 17, 1.1, 0.1, 0.9))
            cong = float(np.clip(cong * rng.uniform(0.9, 1.1), 0.05, 0.99))
            traffic_rows.append(dict(
                hour=h, road_id=road, vehicles=int(cong * rng.integers(120, 260)),
                average_speed=round(float(28 - 20 * cong + rng.uniform(-2, 2)), 1),
                congestion=round(cong, 3),
            ))
    traffic = pd.DataFrame(traffic_rows)

    # ---------------- parking ----------------
    park_rows = []
    for pid in ["parking_a", "parking_b"]:
        cap = BUILDING_BY_ID[pid]["capacity"]
        for h in hours:
            rate = float(np.clip(_occupancy_pattern(h, "parking") * rng.uniform(0.95, 1.12), 0.05, 0.99))
            occ = int(rate * cap)
            park_rows.append(dict(
                hour=h, parking_id=pid, capacity=cap, occupied=occ,
                available=cap - occ, occupancy_rate=round(rate, 3),
            ))
    parking = pd.DataFrame(park_rows)

    # ---------------- washrooms ----------------
    wash = []
    for b in BUILDINGS:
        if b["type"] in ("parking", "gate", "transport"):
            continue
        for n in range(2):
            usage = round(float(np.clip(_occupancy_pattern(CURRENT_HOUR, "washroom") * rng.uniform(0.7, 1.2), 0.1, 0.99)), 2)
            wash.append(dict(
                washroom_id=f"{b['id']}-WC{n+1}", building_id=b["id"], usage_rate=usage,
                crowd_level=level(usage),
                maintenance_status=rng.choice(["ok", "ok", "ok", "needs_cleaning", "under_repair"]),
            ))
    washrooms = pd.DataFrame(wash)

    # ---------------- canteens ----------------
    canteens = pd.DataFrame([dict(
        canteen_id="cafeteria-main", building_id="cafeteria", counters=6,
        queue_len=int(_occupancy_pattern(CURRENT_HOUR, "cafeteria") * 90),
        avg_wait_min=round(float(_occupancy_pattern(CURRENT_HOUR, "cafeteria") * 14), 1),
        seats=520,
    )])

    # ---------------- sports ----------------
    sports = pd.DataFrame([
        dict(sports_id="ground-main", building_id="ground", activity="Football / Athletics",
             slots_total=12, slots_booked=9, participants=int(_occupancy_pattern(CURRENT_HOUR, "sports") * 900)),
        dict(sports_id="complex-indoor", building_id="sports_complex", activity="Indoor courts / Gym",
             slots_total=16, slots_booked=11, participants=int(_occupancy_pattern(CURRENT_HOUR, "sports") * 420)),
    ])

    # ---------------- transport ----------------
    transport = pd.DataFrame([
        dict(route_id="R1", stop="bus_stop", peak_window="08:30-09:15", buses_per_hour=14, riders=520),
        dict(route_id="R2", stop="bus_stop", peak_window="16:45-17:45", buses_per_hour=12, riders=470),
        dict(route_id="R3", stop="bus_stop", peak_window="12:30-13:15", buses_per_hour=6, riders=180),
    ])

    # ---------------- events ----------------
    events = pd.DataFrame([
        dict(event_id="EV1", name="Inter-dept Football League", building_id="ground", hour=17, expected=1200),
        dict(event_id="EV2", name="Tech Talk: Data + Genies", building_id="auditorium", hour=15, expected=650),
        dict(event_id="EV3", name="Placement Drive", building_id="admin_block", hour=10, expected=300),
    ])

    # ---------------- issues ----------------
    issue_rows = []
    for i in range(240):
        it = rng.choice(ISSUE_TYPES, p=_norm([9, 8, 7, 6, 4, 4, 4, 3, 2, 3]))
        issue_rows.append(dict(
            issue_id=f"ISS{i+1:04d}", type=it,
            building_id=rng.choice([b["id"] for b in BUILDINGS]),
            severity=rng.choice(["low", "medium", "high"], p=[0.5, 0.35, 0.15]),
            hour=int(rng.choice(hours)),
        ))
    issues = pd.DataFrame(issue_rows)

    # ---------------- wish history (Campus Pulse) ----------------
    counts = _norm([63, 51, 47, 44, 38, 32, 27, 22, 19, 14])
    wish_rows = []
    wid = 1
    for (domain, text), c in zip(WISH_CATALOG, [63, 51, 47, 44, 38, 32, 27, 22, 19, 14]):
        for _ in range(c):
            wish_rows.append(dict(
                wish_id=f"WSH{wid:04d}", domain=domain, wish_text=text,
                hour=int(rng.choice(hours)),
                affected_group=rng.choice(["students", "faculty", "staff", "visitors"], p=[0.75, 0.12, 0.08, 0.05]),
            ))
            wid += 1
    wish_history = pd.DataFrame(wish_rows)

    # ---------------- impact relationships ----------------
    from simulation.relationships import IMPACT_EDGES
    impact_relationships = pd.DataFrame(IMPACT_EDGES)

    data = dict(
        buildings=buildings, rooms=rooms, classes=classes, faculty=faculty,
        workers=workers, occupancy=occupancy, traffic=traffic, parking=parking,
        washrooms=washrooms, canteens=canteens, sports=sports, transport=transport,
        events=events, issues=issues, wish_history=wish_history,
        impact_relationships=impact_relationships,
    )
    data["snapshot"] = build_snapshot(data, CURRENT_HOUR)
    return data


def _norm(xs):
    a = np.array(xs, dtype=float)
    return a / a.sum()


def BUILDING_BY_ID_safe(room_id: str) -> str:
    return room_id.split("-R")[0]


def build_snapshot(data: dict, hour: int) -> dict:
    """Per-building 'current conditions' shown in the click panel."""
    occ = data["occupancy"]
    snap = {}
    for b in BUILDINGS:
        row = occ[(occ.building_id == b["id"]) & (occ.hour == hour)]
        if row.empty:
            continue
        row = row.iloc[0]
        rooms_b = data["rooms"][data["rooms"].building_id == b["id"]]
        cls_b = data["classes"][data["classes"].building_id == b["id"]]
        fac_b = data["faculty"][data["faculty"].building_id == b["id"]]
        wrk_b = data["workers"][data["workers"].building_id == b["id"]]
        classes_running = int((cls_b.start_time.str[:2].astype(int) <= hour).sum() and
                              (cls_b.start_time.str[:2].astype(int).apply(lambda s: s <= hour < s + 1)).sum()) \
            if not cls_b.empty else 0
        # simpler: classes whose slot contains the hour
        if not cls_b.empty:
            starts = cls_b.start_time.str[:2].astype(int)
            classes_running = int(((starts <= hour) & (hour < starts + 1)).sum())
        rate = float(row.occupancy_rate)
        snap[b["id"]] = dict(
            name=b["name"], type=b["type"], rooms=b["rooms"],
            available_rooms=max(b["rooms"] - classes_running - int(len(fac_b) * 0.3), 0),
            classes_running=classes_running,
            faculty_present=int(len(fac_b)),
            faculty_in_class=int((fac_b.status == "in_class").sum()),
            faculty_in_office=int((fac_b.status == "in_office").sum()),
            staff=int(len(wrk_b)),
            students=int(row.students), faculty=int(row.faculty),
            workers=int(row.workers), visitors=int(row.visitors),
            occupancy=int(row.occupancy), capacity=int(row.capacity),
            occupancy_rate=rate, crowd=level(rate),
            traffic=_building_traffic_level(data, b["id"], hour),
        )
    return snap


def _building_traffic_level(data, bid, hour):
    tmap = {"main_gate": "gate_link", "bus_stop": "gate_link", "parking_a": "ring_w",
            "parking_b": "ring_e", "academic_block": "spine", "cafeteria": "spine"}
    road = tmap.get(bid, "spine")
    row = data["traffic"][(data["traffic"].road_id == road) & (data["traffic"].hour == hour)]
    if row.empty:
        return "LOW"
    return level(float(row.iloc[0].congestion))
