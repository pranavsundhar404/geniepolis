"""
Static campus layout for GENIEPOLIS.

BMS College of Engineering is used as a *fictional demonstration context*.
Every coordinate, capacity and name here is SYNTHETIC DEMONSTRATION DATA
and must not be presented as real BMSCE information.

Visualization concept adapted (2.5D / fast) from the Smart-Campus-Digital-Twin
project (https://github.com/Smart-Campus-Digital-Twin), which uses Three.js +
IoT streaming. We keep the "interactive digital twin with live conditions and
clickable entities" idea, implemented quickly with Plotly.
"""

CAMPUS_NAME = "BMS College of Engineering"
DATA_DISCLAIMER = "SYNTHETIC DEMONSTRATION DATA — not real institutional data"

# Canvas is 1000 (x) by 700 (y). Origin bottom-left (Plotly default).
CANVAS = {"w": 1000, "h": 700}

# ---------------------------------------------------------------------------
# Buildings / campus entities
# ---------------------------------------------------------------------------
# type drives colour + icon + which "current conditions" panel is shown.
BUILDINGS = [
    # id, name, type, x, y, w, h, capacity, rooms
    dict(id="main_gate",         name="Main Gate",              type="gate",       x=500, y=40,  w=90,  h=40,  capacity=0,    rooms=0),
    dict(id="bus_stop",          name="Bus Stop",               type="transport",  x=360, y=95,  w=110, h=40,  capacity=180,  rooms=0),
    dict(id="parking_a",         name="Parking Zone A",         type="parking",    x=140, y=140, w=170, h=150, capacity=320,  rooms=0),
    dict(id="parking_b",         name="Parking Zone B",         type="parking",    x=780, y=150, w=170, h=150, capacity=260,  rooms=0),
    dict(id="admin_block",       name="Administrative Block",   type="admin",      x=300, y=430, w=140, h=90,  capacity=260,  rooms=22),
    dict(id="academic_block",    name="Main Academic Block",    type="academic",   x=470, y=330, w=180, h=130, capacity=2400, rooms=42),
    dict(id="faculty_block",     name="Faculty Block",          type="faculty",    x=680, y=340, w=130, h=100, capacity=420,  rooms=48),
    dict(id="library",           name="Central Library",        type="library",    x=300, y=250, w=140, h=110, capacity=700,  rooms=12),
    dict(id="cafeteria",         name="Cafeteria",              type="cafeteria",  x=520, y=180, w=120, h=90,  capacity=520,  rooms=4),
    dict(id="auditorium",        name="Auditorium",             type="auditorium", x=690, y=180, w=150, h=110, capacity=900,  rooms=3),
    dict(id="innovation_center", name="Innovation Center",      type="academic",   x=690, y=490, w=140, h=90,  capacity=380,  rooms=18),
    dict(id="sports_complex",    name="Sports Complex",         type="sports",     x=840, y=440, w=130, h=110, capacity=600,  rooms=8),
    dict(id="ground",            name="Sports Ground",          type="sports",     x=760, y=560, w=210, h=110, capacity=1500, rooms=0),
    dict(id="hostel_a",          name="Hostel A",               type="hostel",     x=120, y=470, w=120, h=90,  capacity=400,  rooms=120),
    dict(id="hostel_b",          name="Hostel B",               type="hostel",     x=120, y=570, w=120, h=90,  capacity=400,  rooms=120),
    dict(id="washroom_block",    name="Central Washrooms",      type="washroom",   x=470, y=490, w=70,  h=50,  capacity=60,   rooms=6),
]

BUILDING_BY_ID = {b["id"]: b for b in BUILDINGS}

def building_center(b):
    return (b["x"] + b["w"] / 2, b["y"] + b["h"] / 2)

# ---------------------------------------------------------------------------
# Roads (poly-lines) and zones (decorative rectangles)
# ---------------------------------------------------------------------------
ROADS = [
    dict(id="spine",     name="Central Spine Road", pts=[(545, 60), (545, 300), (545, 470), (545, 600)]),
    dict(id="ring_w",    name="West Ring Road",     pts=[(545, 300), (360, 300), (200, 300), (200, 520), (200, 620)]),
    dict(id="ring_e",    name="East Ring Road",     pts=[(545, 300), (760, 300), (870, 300), (870, 500), (860, 610)]),
    dict(id="gate_link", name="Gate Approach",      pts=[(545, 60), (300, 95), (225, 140)]),
]

ZONES = [
    dict(id="central_lawn", name="Central Lawn", x=430, y=250, w=180, h=70, kind="lawn"),
    dict(id="quad",         name="Academic Quad", x=430, y=430, w=260, h=60, kind="lawn"),
]

# ---------------------------------------------------------------------------
# Building relationships (used for the "campus feels alive" panels)
# ---------------------------------------------------------------------------
BUILDING_LINKS = {
    "academic_block": ["faculty_block", "cafeteria", "library", "washroom_block", "bus_stop"],
    "faculty_block": ["academic_block", "admin_block"],
    "cafeteria": ["academic_block", "hostel_a", "hostel_b", "ground"],
    "library": ["academic_block", "hostel_a"],
    "ground": ["sports_complex", "cafeteria", "parking_b", "washroom_block"],
    "sports_complex": ["ground", "parking_b"],
    "main_gate": ["bus_stop", "parking_a", "spine"],
    "bus_stop": ["main_gate", "academic_block", "parking_a"],
    "parking_a": ["main_gate", "bus_stop"],
    "parking_b": ["ground", "sports_complex", "auditorium"],
}

TYPE_STYLE = {
    "gate":       dict(color="#f6c14b", icon="🚪"),
    "transport":  dict(color="#5ac8fa", icon="🚌"),
    "parking":    dict(color="#8e9bb3", icon="🅿️"),
    "admin":      dict(color="#b58bff", icon="🏛️"),
    "academic":   dict(color="#4f9dff", icon="🏫"),
    "faculty":    dict(color="#6ce0c8", icon="👩‍🏫"),
    "library":    dict(color="#ffa45c", icon="📚"),
    "cafeteria":  dict(color="#ff6f91", icon="🍔"),
    "auditorium": dict(color="#c792ea", icon="🎭"),
    "sports":     dict(color="#7ed957", icon="🏟️"),
    "hostel":     dict(color="#9aa7ff", icon="🛏️"),
    "washroom":   dict(color="#66d3fa", icon="🚻"),
}

# Themes for creative wishes (only recolours / relabels the map)
CAMPUS_THEMES = {
    "default": dict(bg="#0b1020", grid="#182034", label="Present Day"),
    "medieval": dict(bg="#2a2118", grid="#3d3020", label="Medieval Geniepolis"),
    "night": dict(bg="#05070f", grid="#0f1830", label="Night Campus"),
    "pedestrian": dict(bg="#0a1a12", grid="#123322", label="Car-Free Core"),
}
