"""
GENIEPOLIS deterministic simulation engine.

INPUT : structured wish (dict) + synthetic campus data (dict of DataFrames)
OUTPUT: a Scenario result dict the UI renders (ripple, direct/indirect impacts,
        before/after metrics, benefits, risks, tradeoffs, alternatives, why).

Rules of the house:
  * The LLM / Genie NEVER computes these numbers. This file does.
  * Formulas are intentionally simple and readable:  new = base * (1 + factor)
  * Reproducible: inputs -> outputs are pure.
"""
from __future__ import annotations

from simulation.relationships import ADJ, label as node_label, NODE_TO_BUILDING
from simulation.scenarios import scenario_key, NAUGHTY_CLOSERS

PARKING_HOUR = 16


# ---------------------------------------------------------------------------
# base metrics pulled from synthetic data
# ---------------------------------------------------------------------------
def base_metrics(data: dict) -> dict:
    tr = data["traffic"]
    pk = data["parking"]
    peak_cong = float(tr[tr.hour.isin([8, 9, 17])].congestion.mean())
    park_rate = float(pk[pk.hour == PARKING_HOUR].occupancy_rate.mean())
    caf_wait = float(data["canteens"].iloc[0].avg_wait_min)
    wash_rate = float(data["washrooms"].usage_rate.mean())
    fac_delay = round(4 + 14 * peak_cong, 1)          # min, derived from congestion
    walk = 420                                         # m, gate -> academic core
    energy = 100                                       # index
    bus_peak_load = int(data["transport"].iloc[0].riders)
    return dict(
        traffic=round(peak_cong * 100, 1),
        parking=round(park_rate * 100, 1),
        cafeteria_wait=round(caf_wait, 1),
        washroom=round(wash_rate * 100, 1),
        faculty_delay=fac_delay,
        walking_distance=walk,
        campus_energy=energy,
        bus_peak_load=bus_peak_load,
    )


def _m(before, after, unit="%"):
    before = round(before, 1)
    after = round(after, 1)
    return dict(before=before, after=after, unit=unit,
                delta=round(after - before, 1),
                delta_pct=round((after - before) / before * 100, 1) if before else 0.0)


def _pct(before, after):
    return round((after - before) / before * 100, 1) if before else 0.0


def _ripple(chain):
    """chain = [(node, kind, delta_pct_or_None), ...] -> UI-ready ripple list."""
    out = []
    for i, (node, kind, delta) in enumerate(chain):
        out.append(dict(
            step=i, node=node, label=node_label(node),
            building_id=NODE_TO_BUILDING.get(node),
            kind=kind, delta_pct=delta,
        ))
    return out


def _verdict(risks, benefits):
    if len(risks) >= len(benefits) + 2:
        return "risky"
    if len(risks) >= len(benefits):
        return "mixed"
    return "good"


def _closer(verdict, creative=False):
    key = "creative" if creative else verdict
    import random
    random.seed(hash(key) & 0xFFFF)
    return random.choice(NAUGHTY_CLOSERS[key])


# ---------------------------------------------------------------------------
# main dispatch
# ---------------------------------------------------------------------------
def simulate(sw: dict, data: dict) -> dict:
    b = base_metrics(data)
    key = scenario_key(sw)
    handler = HANDLERS.get(key, _generic)
    res = handler(sw, data, b)
    res.setdefault("scenario_key", key)
    res.setdefault("wish_domain", sw["domain"])
    res.setdefault("raw_text", sw.get("raw_text", ""))
    res["verdict"] = _verdict(res.get("risks", []), res.get("benefits", []))
    res["genie_closer"] = _closer(res["verdict"], creative=(key == "creative_retheme"))
    # attach a compact before/after table view
    res["metrics_table"] = [
        dict(metric=k.replace("_", " ").title(), **v)
        for k, v in res.get("metrics", {}).items()
    ]
    return res


# ---------------------------------------------------------------------------
# Scenario handlers
# ---------------------------------------------------------------------------
def _class_start_time(sw, data, b):
    target = sw.get("time", "10:00")
    hour = int(target.split(":")[0])
    shift = hour - 8                      # hours later than the 8AM baseline
    late = hour >= 18

    # deterministic factors
    traffic_factor = 0.06 * shift if not late else 0.28      # sharper, compressed peak
    bus_factor = 0.08 * shift if not late else 0.35
    parking_factor = 0.045 * shift if not late else -0.15
    faculty_factor = 0.05 * shift if not late else 0.22
    breakfast_factor = 0.12 * shift if not late else -0.4
    energy_factor = 0.01 * shift if not late else 0.18       # evening lighting/HVAC

    metrics = {
        "traffic": _m(b["traffic"], b["traffic"] * (1 + traffic_factor)),
        "bus_peak_load": _m(b["bus_peak_load"], b["bus_peak_load"] * (1 + bus_factor), unit="riders"),
        "parking": _m(b["parking"], min(b["parking"] * (1 + parking_factor), 99)),
        "faculty_delay": _m(b["faculty_delay"], b["faculty_delay"] * (1 + faculty_factor), unit="min"),
        "cafeteria_wait": _m(b["cafeteria_wait"], b["cafeteria_wait"] * (1 + breakfast_factor), unit="min"),
        "campus_energy": _m(b["campus_energy"], b["campus_energy"] * (1 + energy_factor), unit="idx"),
    }

    direct = [
        dict(label="Class schedule", building_id="academic_block", status="shifted",
             note=f"All in-scope classes start at {target}"),
        dict(label="Student arrival", building_id="main_gate", status="shifted",
             note=f"Arrival peak moves ~{max(shift,1)*15} min later"),
    ]
    indirect = [
        dict(label="Road traffic", building_id="main_gate", delta_pct=metrics["traffic"]["delta_pct"],
             note="Same cars, narrower window = sharper peak" if not late else "Most traffic now after dark"),
        dict(label="Bus demand", building_id="bus_stop", delta_pct=metrics["bus_peak_load"]["delta_pct"],
             note="Riders concentrate into the pre-class window"),
        dict(label="Faculty schedule", building_id="faculty_block", delta_pct=metrics["faculty_delay"]["delta_pct"],
             note="Teaching hours and arrival delay shift"),
        dict(label="Parking", building_id="parking_a", delta_pct=metrics["parking"]["delta_pct"],
             note="Later, shorter parking rush"),
        dict(label="Breakfast demand", building_id="cafeteria", delta_pct=metrics["cafeteria_wait"]["delta_pct"],
             note="More on-campus breakfast" if not late else "Breakfast service largely idle"),
        dict(label="Worker schedule", building_id="admin_block", delta_pct=round(faculty_factor * 60, 1),
             note="Housekeeping / catering / security shifts move with classes"),
    ]

    ripple = _ripple([
        ("class_start_time", "direct", None),
        ("student_arrival", "direct", None),
        ("bus_demand", "indirect", metrics["bus_peak_load"]["delta_pct"]),
        ("road_traffic", "indirect", metrics["traffic"]["delta_pct"]),
        ("parking_fill_time", "indirect", metrics["parking"]["delta_pct"]),
        ("canteen_breakfast", "indirect", metrics["cafeteria_wait"]["delta_pct"]),
        ("faculty_schedule", "indirect", metrics["faculty_delay"]["delta_pct"]),
        ("worker_schedule", "indirect", round(faculty_factor * 60, 1)),
        ("campus_energy", "indirect", metrics["campus_energy"]["delta_pct"]),
    ])

    if late:
        benefits = ["Mornings freed for internships, projects and labs",
                    "Near-empty early campus: almost no early traffic or crowd",
                    "Cooler evening classes, lower daytime AC load"]
        risks = ["Bus network barely runs after 8 PM — students stranded",
                 "Security & housekeeping need a full night shift (cost + staffing)",
                 "Library / cafeteria hours must extend to match",
                 "Safety and lighting concerns for a late-night commute",
                 "Faculty availability drops sharply in the evening"]
        tradeoffs = ["You trade a quiet morning campus for an expensive, thinly-staffed night campus."]
    else:
        benefits = [f"~{shift} hour(s) more sleep / prep time for {sw.get('affected_group','students')}",
                    "Lower *early* morning crowd and 7-8 AM traffic",
                    "Fewer first-hour absentees and late entries"]
        risks = [f"Peak traffic shifts ~{shift*15} min later and gets sharper (+{metrics['traffic']['delta_pct']}%)",
                 f"Bus demand concentrates into one window (+{metrics['bus_peak_load']['delta_pct']}%)",
                 "Faculty and worker schedules must be re-planned",
                 "Evening activities (sports, clubs) get compressed",
                 "Afternoon classroom & cafeteria load rises"]
        tradeoffs = ["You don't remove the morning rush — you move it closer to lunch and make it denser."]

    why = (f"Shifting start to {target} doesn't reduce the number of commuters, it compresses them. "
           f"Baseline peak congestion is {b['traffic']}%; with the same vehicles arriving in a tighter "
           f"pre-{target} window, the model raises it to {metrics['traffic']['after']}%. Buses see the "
           f"largest swing (+{metrics['bus_peak_load']['delta_pct']}%) because most riders have no "
           f"flexibility on arrival time.")

    alternatives = [
        dict(label="Staggered start (8:00 / 8:45 / 9:30 by year)", why="Keeps the sleep benefit for most while flattening the traffic peak instead of moving it."),
        dict(label="Add 4 buses in the new peak window", why="Directly absorbs the +bus demand instead of letting it spill onto roads."),
        dict(label="Keep 8 AM, make first hour attendance-optional", why="Cheapest option; captures ~60% of the sleep benefit with zero ripple."),
    ]

    return dict(
        scenario=dict(title=f"Classes start at {target}", type="A · Operational",
                      description=f"In-scope: {sw.get('scope','all')} classes. Motivation: {sw.get('motivation','decongest')}."),
        direct_impacts=direct, indirect_impacts=indirect, metrics=metrics,
        benefits=benefits, risks=risks, tradeoffs=tradeoffs,
        recommendations=alternatives, ripple=ripple, why=why,
    )


def _move_gate(sw, data, b):
    action = sw.get("preferred_solution", "move_parking")
    to_parking = action == "move_parking"
    walk_after = 260 if to_parking else 180
    metrics = {
        "walking_distance": _m(b["walking_distance"], walk_after, unit="m"),
        "traffic": _m(b["traffic"], b["traffic"] * (1.18 if to_parking else 1.10)),
        "parking": _m(b["parking"], min(b["parking"] * 1.08, 99)),
        "faculty_delay": _m(b["faculty_delay"], b["faculty_delay"] * (1.12 if to_parking else 0.95), unit="min"),
    }
    direct = [
        dict(label="Main Gate", building_id="main_gate", status="relocated",
             note="Gate moves beside Parking Zone A" if to_parking else "Gate moves toward the academic block"),
        dict(label="Parking access", building_id="parking_a", status="improved",
             note="Drivers enter directly next to parking"),
        dict(label="Security checkpoint", building_id="main_gate", status="rebuilt",
             note="New patrol route and staffing pattern"),
    ]
    indirect = [
        dict(label="Traffic concentration", building_id="main_gate", delta_pct=metrics["traffic"]["delta_pct"],
             note="All inbound vehicles funnel through one new pinch point"),
        dict(label="Pedestrian flow", building_id="academic_block", delta_pct=-_pct(b["walking_distance"], walk_after),
             note="Shorter walk from gate to classes"),
        dict(label="Bus routing", building_id="bus_stop", delta_pct=8.0, note="Buses re-route to follow the gate"),
        dict(label="Faculty arrival delay", building_id="faculty_block", delta_pct=metrics["faculty_delay"]["delta_pct"],
             note="Depends on whether faculty park or are dropped"),
        dict(label="Cafeteria access", building_id="cafeteria", delta_pct=-6.0, note="Slightly longer walk for some routes"),
    ]
    ripple = _ripple([
        ("gate_location", "direct", None),
        ("walking_distance", "direct", -_pct(b["walking_distance"], walk_after)),
        ("traffic_concentration", "indirect", metrics["traffic"]["delta_pct"]),
        ("security_workload", "indirect", 15.0),
        ("bus_routing", "indirect", 8.0),
        ("parking_demand", "indirect", metrics["parking"]["delta_pct"]),
    ])
    benefits = [f"Walking distance gate→class drops {b['walking_distance']}m → {walk_after}m",
                "Drivers stop hunting for the lot entrance — smoother parking",
                "Clear single security checkpoint"]
    risks = ["All entry traffic now concentrates at one corner of campus",
             "Pedestrians and vehicles mix more at the new gate",
             "Bus stop and routes must be rebuilt to match",
             "Emergency vehicle access from the old gate side is reduced"]
    tradeoffs = ["You trade a longer walk for a worse single traffic pinch-point near parking."]
    why = (f"Relocating the gate is a pure infrastructure move: the direct wins are geometric "
           f"(walk {b['walking_distance']}→{walk_after} m). The cost is that inbound flow that used "
           f"to spread across two approaches now converges, so modelled congestion rises to "
           f"{metrics['traffic']['after']}%.")
    alternatives = [
        dict(label="Add a second pedestrian-only gate near parking", why="Gets the short walk without moving vehicle traffic."),
        dict(label="Keep the gate, add a covered walkway", why="Solves the 'walk feels long' complaint at a fraction of the disruption."),
        dict(label="Move only the drop-off bay, not the whole gate", why="Captures most of the convenience with minimal re-routing."),
    ]
    return dict(
        scenario=dict(title="Relocate the Main Gate", type="B · Infrastructure",
                      description=f"Action: {action}. Driver: {sw.get('driver','walk')}."),
        direct_impacts=direct, indirect_impacts=indirect, metrics=metrics,
        benefits=benefits, risks=risks, tradeoffs=tradeoffs,
        recommendations=alternatives, ripple=ripple, why=why,
    )


def _pedestrian_zone(sw, data, b):
    scope = sw.get("preferred_solution", "core_pedestrian")
    hard = scope in ("core_carfree",)
    metrics = {
        "traffic": _m(b["traffic"], b["traffic"] * (0.55 if hard else 0.7)),
        "walking_distance": _m(b["walking_distance"], b["walking_distance"] * (1.35 if hard else 1.18), unit="m"),
        "parking": _m(b["parking"], min(b["parking"] * 1.0, 99)),
        "campus_energy": _m(b["campus_energy"], b["campus_energy"] * 0.98, unit="idx"),
    }
    direct = [
        dict(label="Central Spine Road", building_id="academic_block", status="closed to cars",
             note=f"In force: {sw.get('time','peak')}"),
        dict(label="Through-traffic", building_id="main_gate", status="removed",
             note="Vehicles routed to ring roads only"),
    ]
    indirect = [
        dict(label="Road traffic (core)", building_id="academic_block", delta_pct=metrics["traffic"]["delta_pct"],
             note="Through-traffic gone from the centre"),
        dict(label="Perimeter parking demand", building_id="parking_b", delta_pct=22.0,
             note="Cars park at the edge and walk in"),
        dict(label="Walking distance", building_id="academic_block", delta_pct=metrics["walking_distance"]["delta_pct"],
             note="Longer walk from edge lots"),
        dict(label="Bus movement", building_id="bus_stop", delta_pct=-10.0, note="Buses confined to ring roads"),
        dict(label="Emergency access", building_id="admin_block", delta_pct=-18.0,
             note="Fewer vehicle routes into the core"),
    ]
    ripple = _ripple([
        ("pedestrian_zone", "direct", None),
        ("road_traffic", "indirect", metrics["traffic"]["delta_pct"]),
        ("parking_demand", "indirect", 22.0),
        ("walking_distance", "indirect", metrics["walking_distance"]["delta_pct"]),
        ("bus_routing", "indirect", -10.0),
        ("emergency_access", "indirect", -18.0),
    ])
    benefits = ["Quieter, safer, cleaner academic core",
                f"Core congestion {b['traffic']}% → {metrics['traffic']['after']}%",
                "More usable open space between classes", "Lower noise and local emissions"]
    risks = ["Walking distance from edge lots rises by "
             f"{metrics['walking_distance']['delta_pct']}%",
             "Perimeter parking (Zone B) demand jumps ~22%",
             "Ambulance / fire access to the core is slower",
             "Rain-day experience worsens without covered paths",
             "Deliveries and accessibility drop-offs need special permits"]
    tradeoffs = ["You trade vehicle convenience and emergency speed for a calmer, walkable centre."]
    why = (f"Removing through-traffic is the one lever that actually *reduces* congestion rather than "
           f"moving it: modelled core traffic falls to {metrics['traffic']['after']}%. The catch is "
           f"conservation of cars — they reappear at the perimeter, pushing Zone B demand up ~22% and "
           f"average walk-in distance up {metrics['walking_distance']['delta_pct']}%.")
    alternatives = [
        dict(label="Pedestrian-only during class hours only", why="Keeps deliveries/emergencies easy off-peak."),
        dict(label="Electric shuttle loop on the closed spine", why="Preserves access for mobility-impaired users."),
        dict(label="One-way calming loop instead of full closure", why="Half the traffic benefit, none of the emergency-access risk."),
    ]
    return dict(
        scenario=dict(title="Car-free central campus", type="B · Infrastructure",
                      description=f"Scope: {scope}. Parking plan: {sw.get('parking_plan','perimeter')}."),
        direct_impacts=direct, indirect_impacts=indirect, metrics=metrics,
        benefits=benefits, risks=risks, tradeoffs=tradeoffs,
        recommendations=alternatives, ripple=ripple, why=why,
    )


def _sports_participation(sw, data, b):
    goal = sw.get("goal", "participation")
    part_before = int(data["sports"].participants.sum())
    part_after = int(part_before * 1.6)
    metrics = {
        "sports_participation": _m(part_before, part_after, unit="people"),
        "parking": _m(b["parking"], min(b["parking"] * 1.12, 99)),
        "washroom": _m(b["washroom"], min(b["washroom"] * 1.25, 99)),
        "cafeteria_wait": _m(b["cafeteria_wait"], b["cafeteria_wait"] * 1.15, unit="min"),
    }
    direct = [
        dict(label="Sports Ground usage", building_id="ground", status="up",
             note=f"Participation {part_before} → {part_after}"),
        dict(label="Sports Complex bookings", building_id="sports_complex", status="up",
             note="Indoor slots fill; more evening sessions"),
    ]
    indirect = [
        dict(label="Parking Zone B", building_id="parking_b", delta_pct=metrics["parking"]["delta_pct"],
             note="Players & spectators drive to the ground side"),
        dict(label="Washroom / changing rooms", building_id="washroom_block", delta_pct=metrics["washroom"]["delta_pct"],
             note="Big spike right after sessions"),
        dict(label="Cafeteria load", building_id="cafeteria", delta_pct=metrics["cafeteria_wait"]["delta_pct"],
             note="Post-game cluster at juice / snack counters"),
        dict(label="Grounds & cleaning staff", building_id="admin_block", delta_pct=30.0,
             note="More line-marking, watering, waste rounds"),
        dict(label="Pedestrian traffic (east)", building_id="ground", delta_pct=18.0,
             note="Flow between academic block and ground increases"),
    ]
    ripple = _ripple([
        ("sports_participation", "direct", None),
        ("parking_demand", "indirect", metrics["parking"]["delta_pct"]),
        ("washroom_usage", "indirect", metrics["washroom"]["delta_pct"]),
        ("cafeteria_demand", "indirect", metrics["cafeteria_wait"]["delta_pct"]),
        ("worker_schedule", "indirect", 30.0),
    ])
    benefits = ["More students active — health, focus, community",
                f"Ground utilisation up to {part_after} participants",
                "Better use of an expensive existing asset"]
    risks = ["Washroom / changing-room load near the ground spikes ~25%",
             "Parking Zone B contention on match days",
             "Grounds & cleaning staff workload up ~30%",
             "If it eats class time, attendance elsewhere dips",
             "Evening lighting & water costs rise"]
    tradeoffs = [f"Trading '{sw.get('tradeoff','none')}' for participation. If that's class time, expect academic pushback."]
    why = (f"Sports participation is a demand multiplier on nearby services. A 60% rise ({part_before}→{part_after}) "
           f"feeds washrooms (+{metrics['washroom']['delta_pct']}%) and Zone B parking "
           f"(+{metrics['parking']['delta_pct']}%) hardest, because those are closest and capacity-limited.")
    alternatives = [
        dict(label="Friday 3-5 PM sports block, no class overlap", why="Gets participation without trading academic time."),
        dict(label="Add 2 portable washroom units near the ground", why="Directly caps the biggest ripple risk."),
        dict(label="Intramural leagues by department", why="Drives steady participation without single-day parking spikes."),
    ]
    return dict(
        scenario=dict(title="Boost sports participation", type="A · Operational",
                      description=f"Goal: {goal}. Timing: {sw.get('when','evening')}."),
        direct_impacts=direct, indirect_impacts=indirect, metrics=metrics,
        benefits=benefits, risks=risks, tradeoffs=tradeoffs,
        recommendations=alternatives, ripple=ripple, why=why,
    )


def _cafeteria_center(sw, data, b):
    metrics = {
        "walking_distance": _m(360, 210, unit="m"),
        "cafeteria_wait": _m(b["cafeteria_wait"], b["cafeteria_wait"] * 1.1, unit="min"),
        "washroom": _m(b["washroom"], min(b["washroom"] * 1.12, 99)),
        "traffic": _m(b["traffic"], b["traffic"] * 1.05),
    }
    direct = [
        dict(label="Cafeteria location", building_id="cafeteria", status="relocated to centre",
             note="Now beside the central lawn"),
        dict(label="Average walk to food", building_id="academic_block", status="shorter",
             note="360 m → 210 m"),
    ]
    indirect = [
        dict(label="Crowd concentration", building_id="cafeteria", delta_pct=15.0,
             note="Whole campus converges on one central point at 1 PM"),
        dict(label="Central washroom usage", building_id="washroom_block", delta_pct=metrics["washroom"]["delta_pct"],
             note="Nearest washrooms take the overflow"),
        dict(label="Waste / cleaning load (centre)", building_id="cafeteria", delta_pct=20.0,
             note="Single hub concentrates waste collection"),
        dict(label="Foot traffic on the spine", building_id="academic_block", delta_pct=12.0,
             note="More criss-cross pedestrian flow at lunch"),
    ]
    ripple = _ripple([
        ("cafeteria_location", "direct", None),
        ("walking_distance", "direct", -_pct(360, 210)),
        ("crowd_concentration", "indirect", 15.0),
        ("washroom_usage", "indirect", metrics["washroom"]["delta_pct"]),
        ("waste_workload", "indirect", 20.0),
    ])
    benefits = ["Everyone is closer to food — walk 360→210 m",
                "Better for a short lunch break", "Central social hub for campus life"]
    risks = ["Lunch crowd concentrates dangerously in one node (+15%)",
             "Central washrooms and waste load rise",
             "Noise and smell near the academic core / library",
             "Queue still long unless counters are added"]
    tradeoffs = ["You trade a distributed, calmer campus for a convenient but congested centre."]
    why = ("Centralising food trades distance for density. The walk genuinely drops (360→210 m), but the "
           "same number of diners now arrive at one point in the same 20 minutes, so crowd concentration "
           "and nearby washroom/waste load rise together.")
    alternatives = [
        dict(label="Second smaller food point near hostels", why="Cuts distance without central overcrowding."),
        dict(label="Keep location, add 3 counters + staggered breaks", why="Attacks the queue, which is the real complaint."),
        dict(label="Grab-and-go kiosks in the academic block", why="Distributes lunch demand across campus."),
    ]
    return dict(
        scenario=dict(title="Cafeteria at the campus centre", type="B · Infrastructure",
                      description="Relocate main food service to the central lawn."),
        direct_impacts=direct, indirect_impacts=indirect, metrics=metrics,
        benefits=benefits, risks=risks, tradeoffs=tradeoffs,
        recommendations=alternatives, ripple=ripple, why=why,
    )


def _parking_capacity(sw, data, b):
    sol = sw.get("preferred_solution", "increase_capacity")
    add = sol == "increase_capacity"
    metrics = {
        "parking": _m(b["parking"], b["parking"] * (0.8 if add else 0.92)),
        "traffic": _m(b["traffic"], b["traffic"] * (1.06 if add else 0.96)),
        "walking_distance": _m(b["walking_distance"], b["walking_distance"] * (1.1 if add else 1.0), unit="m"),
        "campus_energy": _m(b["campus_energy"], b["campus_energy"] * (1.03 if add else 1.0), unit="idx"),
    }
    direct = [
        dict(label="Parking capacity", building_id="parking_a", status="increased" if add else "reallocated",
             note="+180 spaces (new deck)" if add else "Dynamic allocation by pass type & time"),
    ]
    indirect = [
        dict(label="Circling traffic", building_id="main_gate", delta_pct=-14.0 if add else -8.0,
             note="Fewer drivers hunting for a spot"),
        dict(label="Induced demand", building_id="parking_a", delta_pct=9.0 if add else 2.0,
             note="More supply nudges more people to drive"),
        dict(label="Walking distance", building_id="academic_block", delta_pct=metrics["walking_distance"]["delta_pct"],
             note="New deck sits further out" if add else "Unchanged"),
    ]
    ripple = _ripple([
        ("parking_demand", "direct", metrics["parking"]["delta_pct"]),
        ("road_traffic", "indirect", metrics["traffic"]["delta_pct"]),
        ("parking_fill_time", "indirect", -15.0),
        ("campus_energy", "indirect", metrics["campus_energy"]["delta_pct"]),
    ])
    benefits = [f"Peak occupancy eases {b['parking']}% → {metrics['parking']['after']}%",
                "Less circling, calmer gate approach" if not add else "More guaranteed spaces",
                "Predictable parking for the target group"]
    risks = (["A new deck induces more car trips over time",
              "Construction cost & disruption",
              "Deck sits further from class — walk rises",
              "Does nothing for bus / cycle users"] if add else
             ["Reallocation angers whoever loses priority",
              "Needs enforcement & an app to work",
              "Capacity is still fundamentally fixed"])
    tradeoffs = ["Build = capital + induced demand. Reallocate = political + enforcement."]
    why = (f"Baseline evening occupancy is {b['parking']}%. {'Adding ~180 spaces' if add else 'Smart reallocation'} "
           f"brings modelled occupancy to {metrics['parking']['after']}%. "
           f"{'But extra supply induces ~9% more car trips, partially eroding the gain.' if add else 'Traffic also dips slightly as circling falls.'}")
    alternatives = [
        dict(label="Peak-hour parking pass + carpool priority", why="Cuts demand instead of chasing it with concrete."),
        dict(label="Shuttle from a remote lot", why="Adds effective capacity without central-campus land."),
        dict(label="Shift 1 department to staggered hours", why="Flattens the 4 PM spike that causes the complaint."),
    ]
    return dict(
        scenario=dict(title="Fix peak parking", type="A/B · Operational + Infra",
                      description=f"Problem: {sw.get('problem','capacity')} · Window: {sw.get('time','evening')} · Fix: {sol}"),
        direct_impacts=direct, indirect_impacts=indirect, metrics=metrics,
        benefits=benefits, risks=risks, tradeoffs=tradeoffs,
        recommendations=alternatives, ripple=ripple, why=why,
    )


def _bus_stop_move(sw, data, b):
    metrics = {
        "walking_distance": _m(300, 120, unit="m"),
        "traffic": _m(b["traffic"], b["traffic"] * 1.12),
        "faculty_delay": _m(b["faculty_delay"], b["faculty_delay"] * 1.05, unit="min"),
        "bus_peak_load": _m(b["bus_peak_load"], b["bus_peak_load"] * 1.05, unit="riders"),
    }
    direct = [
        dict(label="Bus stop location", building_id="bus_stop", status="relocated",
             note="Now beside the academic block"),
        dict(label="Walk from bus to class", building_id="academic_block", status="shorter", note="300 m → 120 m"),
    ]
    indirect = [
        dict(label="Bus traffic on the spine", building_id="academic_block", delta_pct=metrics["traffic"]["delta_pct"],
             note="Large vehicles now enter the core"),
        dict(label="Pedestrian safety (core)", building_id="academic_block", delta_pct=-12.0,
             note="Buses & students share the same space"),
        dict(label="Gate approach congestion", building_id="main_gate", delta_pct=-6.0,
             note="Buses no longer idle at the old stop"),
    ]
    ripple = _ripple([
        ("bus_routing", "direct", None),
        ("walking_distance", "direct", -_pct(300, 120)),
        ("road_traffic", "indirect", metrics["traffic"]["delta_pct"]),
        ("students_on_campus", "indirect", 0.0),
        ("emergency_access", "indirect", -8.0),
    ])
    benefits = ["Bus riders walk 300→120 m to class", "Better in the rain", "Old gate approach frees up"]
    risks = ["Buses in the pedestrian core raise congestion +12%",
             "Bus–pedestrian conflict near the busiest building",
             "Noise & fumes next to classrooms",
             "Turning radius may force road widening"]
    tradeoffs = ["Convenience for bus riders vs. a calmer, safer academic core."]
    why = ("Moving the stop inward is a short-walk win for riders, but it drives buses through the "
           "central spine at exactly the times it's most crowded, so core congestion and pedestrian "
           "conflict rise together.")
    alternatives = [
        dict(label="Covered walkway from the current stop", why="Solves 'walk is long/wet' without buses in the core."),
        dict(label="Small EV shuttle from gate stop to block", why="Keeps big buses out, still cuts the walk."),
        dict(label="Move the stop only 80 m, not fully in", why="Half the walk saving, none of the core-traffic risk."),
    ]
    return dict(
        scenario=dict(title="Move the bus stop to the academic block", type="B · Infrastructure",
                      description="Relocate the campus bus stop next to the main academic block."),
        direct_impacts=direct, indirect_impacts=indirect, metrics=metrics,
        benefits=benefits, risks=risks, tradeoffs=tradeoffs,
        recommendations=alternatives, ripple=ripple, why=why,
    )


def _library_hours(sw, data, b):
    metrics = {
        "campus_energy": _m(b["campus_energy"], b["campus_energy"] * 1.08, unit="idx"),
        "washroom": _m(b["washroom"], min(b["washroom"] * 1.05, 99)),
        "faculty_delay": _m(b["faculty_delay"], b["faculty_delay"], unit="min"),
    }
    direct = [
        dict(label="Library hours", building_id="library", status="extended",
             note="Now open to 01:00 during exam weeks"),
        dict(label="Night study seats", building_id="library", status="+220", note="Reading rooms stay open"),
    ]
    indirect = [
        dict(label="Night security workload", building_id="admin_block", delta_pct=25.0,
             note="Patrols + a guard posted at the library"),
        dict(label="Campus energy (night)", building_id="library", delta_pct=metrics["campus_energy"]["delta_pct"],
             note="Lighting, HVAC, systems run longer"),
        dict(label="Hostel foot traffic (late)", building_id="hostel_a", delta_pct=15.0,
             note="Students walk back after midnight"),
        dict(label="Canteen / vending demand (late)", building_id="cafeteria", delta_pct=10.0, note="Late-night snack demand"),
    ]
    ripple = _ripple([
        ("students_on_campus", "direct", None),
        ("campus_energy", "indirect", metrics["campus_energy"]["delta_pct"]),
        ("security_workload", "indirect", 25.0),
        ("washroom_usage", "indirect", metrics["washroom"]["delta_pct"]),
    ])
    benefits = ["More quiet study capacity when it's actually needed",
                "Safer than students studying in unlit corridors / hostels rooms",
                "Signals the campus takes academics seriously"]
    risks = ["Night security cost and staffing up ~25%",
             "Higher night energy bill",
             "Late-night solo walks to hostels — lighting & escort needed",
             "Harder to justify off exam season"]
    tradeoffs = ["Extra study hours cost real money in security + energy."]
    why = ("Keeping the library open past midnight mostly converts existing demand into a safer, "
           "supervised setting. The ripple is operational: security workload (+25%) and night energy "
           "(+8%) are the price of the extra hours.")
    alternatives = [
        dict(label="24×7 only during the 3 exam weeks", why="90% of the benefit, a fraction of the annual cost."),
        dict(label="Open one wing + one guard, not the whole building", why="Caps energy and staffing."),
        dict(label="Night study room in each hostel instead", why="No late walk home; cheaper to secure."),
    ]
    return dict(
        scenario=dict(title="Library open late", type="A · Operational",
                      description=f"Goal: {sw.get('goal','hours')} · Peak: {sw.get('when','evening')}"),
        direct_impacts=direct, indirect_impacts=indirect, metrics=metrics,
        benefits=benefits, risks=risks, tradeoffs=tradeoffs,
        recommendations=alternatives, ripple=ripple, why=why,
    )


def _washroom_ops(sw, data, b):
    metrics = {
        "washroom": _m(b["washroom"], b["washroom"] * 0.82),
        "campus_energy": _m(b["campus_energy"], b["campus_energy"] * 1.01, unit="idx"),
    }
    direct = [
        dict(label="Cleaning frequency", building_id="washroom_block", status="2× rounds",
             note="Peak-hour rounds after each class break"),
        dict(label="Maintenance backlog", building_id="washroom_block", status="cleared",
             note="Sensor-flagged issues fixed same day"),
    ]
    indirect = [
        dict(label="Perceived campus cleanliness", building_id="academic_block", delta_pct=20.0,
             note="Knock-on satisfaction effect"),
        dict(label="Housekeeping workload", building_id="admin_block", delta_pct=18.0,
             note="More staff-hours on the same shift"),
        dict(label="Water & supplies cost", building_id="admin_block", delta_pct=9.0, note="More frequent restocking"),
    ]
    ripple = _ripple([
        ("students_on_campus", "direct", None),
        ("washroom_usage", "direct", metrics["washroom"]["delta_pct"]),
        ("worker_schedule", "indirect", 18.0),
    ])
    benefits = ["Congestion / unusable-stall rate down ~18%",
                "Big satisfaction win for a low-glamour fix",
                "Sensor data tells admin where to build next"]
    risks = ["Recurring staffing cost, not one-time",
             "Needs supervision or rounds get skipped",
             "Sensors add a small maintenance surface of their own"]
    tradeoffs = ["Ongoing labour cost for a continuous quality improvement."]
    why = ("This is a staffing + monitoring change, not a construction one. Doubling peak-hour rounds "
           "cuts modelled washroom congestion ~18%; the only ripple is housekeeping workload and "
           "supply cost.")
    alternatives = [
        dict(label="Sensor alerts + on-call cleaner (no fixed 2× rounds)", why="Same result, less idle labour."),
        dict(label="Build 2 washrooms at the worst-hit block", why="Attacks capacity, not just cleaning."),
        dict(label="Student-reported QR feedback per washroom", why="Cheapest signal; targets effort where it matters."),
    ]
    return dict(
        scenario=dict(title="Cleaner washrooms", type="A · Operational",
                      description=f"Problem: {sw.get('problem','maintenance')} · Peak: {sw.get('time','morning_break')}"),
        direct_impacts=direct, indirect_impacts=indirect, metrics=metrics,
        benefits=benefits, risks=risks, tradeoffs=tradeoffs,
        recommendations=alternatives, ripple=ripple, why=why,
    )


def _creative_retheme(sw, data, b):
    theme = sw.get("theme", "medieval")
    theme_map = {"medieval": "medieval", "night": "night", "forest": "pedestrian", "futuristic": "default"}
    labels = {
        "medieval": ("Medieval Geniepolis", "Buildings become keeps, the lawn a jousting green, the gate a drawbridge."),
        "night": ("Eternal Night Campus", "Perpetual dusk, lantern light, and a suspiciously photogenic moon."),
        "forest": ("Forest Campus", "Canopy walkways, moss on the admin block, owls in the auditorium."),
        "futuristic": ("Neo-Geniepolis 2099", "Chrome, holograms, and a cafeteria that prints dosa."),
    }
    name, desc = labels.get(theme, labels["medieval"])
    direct = [
        dict(label="Campus theme", building_id="academic_block", status="transformed", note=desc),
        dict(label="Building names", building_id="library", status="renamed", note="The Library → The Grand Archive"),
    ]
    indirect = [
        dict(label="Student photos / social buzz", building_id="main_gate", delta_pct=300.0, note="Wildly up. Obviously."),
        dict(label="Actual operations", building_id="admin_block", delta_pct=0.0, note="Unchanged — this is a visual wish"),
    ]
    ripple = _ripple([
        ("students_on_campus", "direct", None),
        ("campus_energy", "indirect", 0.0),
    ])
    return dict(
        scenario=dict(title=name, type="C · Creative / Visual",
                      description=f"{desc}  Intensity: {sw.get('intensity','vibe')}. Kept normal: {sw.get('keep','none')}."),
        direct_impacts=direct, indirect_impacts=indirect, metrics={},
        benefits=["Campus morale and identity soar", "Amazing for open-day and marketing",
                  "Zero operational risk — it's paint and signage"],
        risks=["Facilities team files 14 complaints", "Wayfinding confusion for a week",
               "Someone will try to actually raise the drawbridge"],
        tradeoffs=["Pure delight vs. a very confused delivery driver."],
        recommendations=[
            dict(label="Theme just the central lawn + gate", why="Maximum photo impact, minimum confusion."),
            dict(label="Keep old names on small plaques", why="Fun overlay without breaking wayfinding."),
            dict(label="Run it as a one-week festival", why="All the joy, none of the permanent upkeep."),
        ],
        ripple=ripple, why="Creative wishes skip the simulation engine — GENIEPOLIS just re-skins the "
                           "map. Operations, traffic and crowd numbers are deliberately left unchanged.",
        theme=theme_map.get(theme, "default"),
    )


def _generic(sw, data, b):
    metrics = {
        "traffic": _m(b["traffic"], b["traffic"] * 1.05),
        "parking": _m(b["parking"], min(b["parking"] * 1.05, 99)),
    }
    return dict(
        scenario=dict(title=sw.get("raw_text", "Your wish"), type="A · Operational",
                      description="Generic what-if — mapped to nearest known pattern."),
        direct_impacts=[dict(label="Requested change", building_id="academic_block", status="applied", note=sw.get("raw_text", ""))],
        indirect_impacts=[dict(label="Traffic", building_id="main_gate", delta_pct=5.0, note="Mild knock-on"),
                          dict(label="Parking", building_id="parking_a", delta_pct=5.0, note="Mild knock-on")],
        metrics=metrics,
        benefits=["Addresses the stated need directly"],
        risks=["Second-order effects are approximate for this wish type"],
        tradeoffs=["Precision vs. coverage — refine the wish for a sharper simulation."],
        recommendations=[dict(label="Pick a more specific version of this wish", why="Unlocks a dedicated model.")],
        ripple=_ripple([("students_on_campus", "direct", None), ("road_traffic", "indirect", 5.0)]),
        why="This wish didn't match a specific model, so a conservative generic ripple was applied.",
    )


HANDLERS = {
    "class_start_time": _class_start_time,
    "move_gate": _move_gate,
    "pedestrian_zone": _pedestrian_zone,
    "sports_participation": _sports_participation,
    "cafeteria_center": _cafeteria_center,
    "cafeteria_ops": _cafeteria_center,
    "parking_capacity": _parking_capacity,
    "bus_stop_move": _bus_stop_move,
    "bus_ops": _bus_stop_move,
    "library_hours": _library_hours,
    "washroom_ops": _washroom_ops,
    "creative_retheme": _creative_retheme,
}
