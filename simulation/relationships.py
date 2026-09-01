"""
Campus impact-relationship graph.

This is the "butterfly effect" wiring. Each edge = "a change in SOURCE pushes
TARGET in some direction, with WEIGHT strength". The deterministic simulation
engine walks this graph to build ripple chains and indirect effects.

Also loaded into Databricks as the `impact_relationships` table so Genie can
*explain* relationships (but never compute them).
"""

# source, target, relationship, weight (0..1), explanation
IMPACT_EDGES = [
    dict(source="class_start_time", target="student_arrival", relationship="shifts", weight=0.9,
         explanation="Later class start times move the bulk of student arrivals later in the morning."),
    dict(source="student_arrival", target="bus_demand", relationship="shifts", weight=0.8,
         explanation="Arrival time controls when buses are most in demand at the campus stop."),
    dict(source="student_arrival", target="road_traffic", relationship="shifts", weight=0.75,
         explanation="Concentrated arrivals create a sharper vehicle peak on approach roads."),
    dict(source="bus_demand", target="road_traffic", relationship="increases", weight=0.55,
         explanation="More buses in a narrow window add to congestion on the gate approach."),
    dict(source="road_traffic", target="parking_fill_time", relationship="delays", weight=0.6,
         explanation="Congested roads slow how fast parking zones fill and clear."),
    dict(source="road_traffic", target="travel_time", relationship="increases", weight=0.85,
         explanation="Higher congestion directly raises average travel and arrival-delay minutes."),
    dict(source="class_start_time", target="faculty_schedule", relationship="shifts", weight=0.7,
         explanation="Teaching slots move with class times, changing faculty campus hours."),
    dict(source="class_start_time", target="worker_schedule", relationship="shifts", weight=0.5,
         explanation="Housekeeping, catering and security shifts are planned around class blocks."),
    dict(source="class_start_time", target="canteen_breakfast", relationship="increases", weight=0.6,
         explanation="A later start pushes more students to eat breakfast on campus."),
    dict(source="students_on_campus", target="cafeteria_demand", relationship="increases", weight=0.8,
         explanation="Cafeteria load tracks how many students are physically on campus."),
    dict(source="students_on_campus", target="washroom_usage", relationship="increases", weight=0.7,
         explanation="Washroom usage scales with people present, peaking between classes."),
    dict(source="students_on_campus", target="campus_energy", relationship="increases", weight=0.5,
         explanation="Lighting, HVAC and lab load rise with occupancy."),
    dict(source="sports_participation", target="parking_demand", relationship="increases", weight=0.5,
         explanation="More players and spectators near the ground raises Parking Zone B demand."),
    dict(source="sports_participation", target="washroom_usage", relationship="increases", weight=0.6,
         explanation="Sports activity spikes washroom and changing-room usage nearby."),
    dict(source="sports_participation", target="cafeteria_demand", relationship="increases", weight=0.45,
         explanation="Post-activity, players cluster at the cafeteria and juice counters."),
    dict(source="events", target="road_traffic", relationship="increases", weight=0.7,
         explanation="Large events pull in visitors, concentrating traffic before and after."),
    dict(source="events", target="parking_demand", relationship="increases", weight=0.8,
         explanation="Event visitors compete for the same fixed parking capacity."),
    dict(source="parking_demand", target="road_traffic", relationship="increases", weight=0.6,
         explanation="Drivers circling for a free spot add slow-moving vehicles to campus roads."),
    dict(source="gate_location", target="walking_distance", relationship="changes", weight=0.8,
         explanation="Where the gate sits sets how far pedestrians walk to the academic core."),
    dict(source="gate_location", target="traffic_concentration", relationship="changes", weight=0.7,
         explanation="Moving the gate re-routes all inbound vehicles through a new pinch point."),
    dict(source="gate_location", target="security_workload", relationship="changes", weight=0.6,
         explanation="A relocated gate changes patrol routes and checkpoint staffing needs."),
    dict(source="gate_location", target="bus_routing", relationship="changes", weight=0.5,
         explanation="Bus approach and drop-off must follow the gate."),
    dict(source="pedestrian_zone", target="road_traffic", relationship="decreases", weight=0.7,
         explanation="Closing the core to cars removes through-traffic from the central spine."),
    dict(source="pedestrian_zone", target="walking_distance", relationship="increases", weight=0.4,
         explanation="Drivers park at the edge and walk further into a car-free core."),
    dict(source="pedestrian_zone", target="parking_demand", relationship="shifts", weight=0.6,
         explanation="Parking pressure moves from central lots to perimeter lots."),
    dict(source="pedestrian_zone", target="emergency_access", relationship="risks", weight=0.5,
         explanation="Fewer vehicle routes can slow ambulance / fire access to the core."),
    dict(source="cafeteria_location", target="walking_distance", relationship="changes", weight=0.7,
         explanation="A central cafeteria shortens the average walk from classrooms."),
    dict(source="cafeteria_location", target="crowd_concentration", relationship="increases", weight=0.6,
         explanation="Centralising food service concentrates the lunch crowd in one place."),
    dict(source="cafeteria_location", target="waste_workload", relationship="increases", weight=0.5,
         explanation="A single busy hub raises cleaning and waste-collection load there."),
]

# convenient adjacency
def build_adjacency():
    adj = {}
    for e in IMPACT_EDGES:
        adj.setdefault(e["source"], []).append(e)
    return adj

ADJ = build_adjacency()

# Human-friendly labels for ripple nodes
NODE_LABELS = {
    "class_start_time": "Class Timing",
    "student_arrival": "Student Arrival",
    "students_on_campus": "Students on Campus",
    "bus_demand": "Bus Demand",
    "road_traffic": "Road Traffic",
    "parking_fill_time": "Parking Fill Rate",
    "parking_demand": "Parking Demand",
    "travel_time": "Travel / Arrival Delay",
    "faculty_schedule": "Faculty Schedule",
    "worker_schedule": "Worker Schedule",
    "canteen_breakfast": "Breakfast Demand",
    "cafeteria_demand": "Cafeteria Load",
    "washroom_usage": "Washroom Usage",
    "campus_energy": "Campus Energy",
    "sports_participation": "Sports Participation",
    "events": "Campus Events",
    "gate_location": "Gate Location",
    "walking_distance": "Walking Distance",
    "traffic_concentration": "Traffic Concentration",
    "security_workload": "Security Workload",
    "bus_routing": "Bus Routing",
    "pedestrian_zone": "Pedestrian Core",
    "emergency_access": "Emergency Access",
    "cafeteria_location": "Cafeteria Location",
    "crowd_concentration": "Crowd Concentration",
    "waste_workload": "Waste / Cleaning Load",
}

# Which campus building each ripple node visually maps to (for map highlighting)
NODE_TO_BUILDING = {
    "class_start_time": "academic_block",
    "student_arrival": "main_gate",
    "students_on_campus": "academic_block",
    "bus_demand": "bus_stop",
    "road_traffic": "main_gate",
    "parking_fill_time": "parking_a",
    "parking_demand": "parking_b",
    "travel_time": "main_gate",
    "faculty_schedule": "faculty_block",
    "worker_schedule": "admin_block",
    "canteen_breakfast": "cafeteria",
    "cafeteria_demand": "cafeteria",
    "washroom_usage": "washroom_block",
    "campus_energy": "academic_block",
    "sports_participation": "ground",
    "events": "auditorium",
    "gate_location": "main_gate",
    "walking_distance": "academic_block",
    "traffic_concentration": "main_gate",
    "security_workload": "main_gate",
    "bus_routing": "bus_stop",
    "pedestrian_zone": "academic_block",
    "emergency_access": "admin_block",
    "cafeteria_location": "cafeteria",
    "crowd_concentration": "cafeteria",
    "waste_workload": "cafeteria",
}


def label(node: str) -> str:
    return NODE_LABELS.get(node, node.replace("_", " ").title())
