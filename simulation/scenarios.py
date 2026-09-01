"""
Wish classification + Akinator-style narrowing trees for the GENIEPOLIS Genie.

The Genie NARROWS the wish here (fast, deterministic, 3-5 questions).
Databricks Genie is used alongside this for data-grounded answers/explanations;
this module guarantees the game flow never stalls or asks 15 questions.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# 1. Classification
# ---------------------------------------------------------------------------
# Order matters: earlier domains win ties (more specific first).
# Some keywords are multi-word / high-signal — they score 2 instead of 1.
DOMAIN_KEYWORDS = {
    "creative":      ["medieval", "castle", "night campus", "theme", "look like", "futuristic", "forest", "beach"],
    "faculty":       ["teacher", "teachers", "faculty", "professor", "lecturer", "staff room",
                      "faculty room", "substitute", "class teacher", "instructor", "mentor",
                      "faculty availability", "more faculty", "change teacher"],
    "gate":          ["gate", "entrance", "entry point", "front gate"],
    "traffic":       ["traffic", "congestion", "road", "pedestrian", "car-free", "cars from", "no cars", "one-way"],
    "transport":     ["bus", "shuttle", "bus stop"],
    "sports":        ["sports", "gym", "football", "cricket", "fitness", "friday sports", "sports day", "sports ground"],
    "cafeteria":     ["cafeteria", "canteen", "food", "mess", "queue", "lunch"],
    "library":       ["library", "study space", "reading room"],
    "washroom":      ["washroom", "toilet", "restroom", "bathroom"],
    "parking":       ["parking", "car space", "vehicle space", "parking lot"],
    "schedule":      ["class start", "classes start", "start at", "class timing", "timing",
                      "10 am", "8 pm", "9 am", "8 am", "schedule", "lecture time",
                      "morning class", "late class", "start time", "end at"],
}

# phrases that, if present, strongly pin the domain regardless of other hits
DOMAIN_STRONG = {
    "faculty": ["teacher", "faculty", "professor", "lecturer", "instructor"],
    "creative": ["medieval", "futuristic", "theme the", "look like a"],
    "gate": ["the gate", "front gate", "move the gate"],
    "cafeteria": ["cafeteria", "canteen", "mess"],
    "library": ["library"],
    "washroom": ["washroom", "toilet", "restroom"],
    "sports": ["sports", "ground", "gym"],
    "transport": ["bus"],
    "parking": ["parking"],
}

DEFAULT_DOMAIN = "schedule"

# Broad campus vocabulary — if a wish contains NONE of these (and no domain
# keyword), it's probably not a campus wish and the Genie should push back.
CAMPUS_VOCAB = [
    "campus", "college", "university", "student", "students", "faculty", "teacher",
    "professor", "staff", "worker", "class", "classroom", "lecture", "exam", "semester",
    "hostel", "block", "building", "room", "lab", "library", "canteen", "cafeteria",
    "mess", "food", "washroom", "toilet", "parking", "gate", "entrance", "road",
    "traffic", "bus", "shuttle", "transport", "sports", "ground", "gym", "auditorium",
    "wifi", "fee", "admin", "department", "schedule", "timing", "crowd", "queue",
    "event", "seminar", "placement", "study", "attendance", "corridor", "lawn", "quad",
    "here", "this place", "move", "build", "start", "closer", "more", "less", "better",
]

# Obvious non-campus tells
OFFTOPIC_TELLS = [
    "weather", "stock", "bitcoin", "crypto", "president", "war", "movie", "song",
    "recipe", "girlfriend", "boyfriend", "marry", "dragon", "unicorn", "lottery",
    "football match tonight", "who won", "cricket score", "translate", "python code",
]


def classify(text: str) -> str:
    t = (text or "").lower()
    # strong phrases short-circuit (first match by dict order wins)
    for domain, phrases in DOMAIN_STRONG.items():
        if any(p in t for p in phrases):
            return domain
    best, best_hits = DEFAULT_DOMAIN, 0.0
    for domain, kws in DOMAIN_KEYWORDS.items():
        hits = sum(2 if " " in k else 1 for k in kws if k in t)
        if hits > best_hits:
            best, best_hits = domain, hits
    return best if best_hits else DEFAULT_DOMAIN


def is_campus_wish(text: str) -> bool:
    """True if the text plausibly concerns the campus. Cheap guard, not a classifier."""
    t = (text or "").strip().lower()
    if len(t) < 3:
        return False
    if any(tell in t for tell in OFFTOPIC_TELLS):
        return False
    # a direct domain keyword hit is an instant yes
    for kws in DOMAIN_KEYWORDS.values():
        if any(k in t for k in kws):
            return True
    return any(re.search(rf"\b{re.escape(w)}\b", t) for w in CAMPUS_VOCAB)


OFFTOPIC_REPLIES = [
    "That is a fine wish, but I am bound to this campus. Ask me something about "
    "*here* — buildings, classes, parking, buses, food, that sort of chaos.",
    "My lamp only has campus-shaped magic in it. Try a wish about the college.",
    "Out of scope for a campus genie. Give me a wish about the campus and watch it ripple.",
]


# ---------------------------------------------------------------------------
# 2. Genie one-liners
# ---------------------------------------------------------------------------
GENIE_REACTIONS = {
    "parking":   "Ahhh... parking. The eternal campus battlefield.",
    "schedule":  "Rearranging *time* itself? Bold. I like bold.",
    "gate":      "Oh, we're moving the campus around already? Day one energy.",
    "traffic":   "You want to fight the traffic monster. Noble. Slightly reckless.",
    "cafeteria": "The cafeteria. Where hunger meets queue theory.",
    "sports":    "Sweat, glory, and a suspicious number of missed classes. Go on.",
    "transport": "Buses. The unsung heroes nobody thanks. Let's help them.",
    "library":   "More study space? Who *are* you and what have you done with students?",
    "washroom":  "A wish about washrooms. Unglamorous. Deeply appreciated by all.",
    "faculty":   "Ah, a wish about the *humans* who teach. Delicate territory. Continue.",
    "creative":  "Finally... a student with *ambition*.",
}

THINKING_LINES = [
    "Hmmm...", "Interesting...", "You're hiding something from me...",
    "Let me narrow that down.", "Go on, I'm listening with all four ears.",
]

CONFIRM_OPENERS = ["Ahhh. NOW I understand.", "There it is. The *real* wish.",
                   "So that's what you were after all along."]

NAUGHTY_CLOSERS = {
    "good": [
        "Now THAT is a wish I can get behind. Don't tell the other students how easy that was.",
        "A rare wish that helps more people than it annoys. Suspicious. Approved.",
    ],
    "mixed": [
        "Not bad... but you've just moved the morning traffic monster 15 minutes closer to breakfast.",
        "Your wish is powerful. Perhaps TOO powerful. The buses are already writing complaints.",
    ],
    "risky": [
        "Bold. Somewhere, a security guard just felt a disturbance in the campus.",
        "I granted it. I also stocked up on popcorn for what happens next.",
    ],
    "creative": [
        "Done. If anyone asks, the drawbridge was always there.",
        "The campus has been re-themed. The pigeons are furious. I find it hilarious.",
    ],
}

# ---------------------------------------------------------------------------
# 3. Akinator question trees  (3-5 questions, fixed order, tiny branching)
# ---------------------------------------------------------------------------
# Each question: key, genie, prompt, options[(label, value)]
def _q(key, genie, prompt, options):
    return dict(key=key, genie=genie, prompt=prompt,
                options=[dict(label=l, value=v) for l, v in options])


QUESTION_TREES = {
    "parking": [
        _q("problem", "Are you suffering from...", "What's the actual parking pain?",
           [("Too few parking spaces", "capacity"),
            ("Parking is badly distributed", "distribution"),
            ("Too much traffic while parking", "traffic"),
            ("Parking is too far from class", "distance")]),
        _q("time", "When does it become a battlefield?", "Peak pain window?",
           [("Morning 8-10", "morning"), ("Lunch 12-2", "lunch"),
            ("Evening 4-7", "evening"), ("During events", "events")]),
        _q("group", "And who suffers the most?", "Most affected group?",
           [("Students", "students"), ("Faculty", "faculty"),
            ("Staff", "staff"), ("Visitors", "visitors")]),
        _q("solution", "One final question... would you rather...", "Preferred fix?",
           [("Build more parking", "increase_capacity"),
            ("Move existing parking", "relocate"),
            ("Reduce peak traffic", "reduce_peak"),
            ("Improve parking allocation", "reallocate")]),
    ],
    "schedule": [
        _q("target_time", "You want classes to start at...", "New start time?",
           [("8 AM (as now)", "08:00"), ("9 AM", "09:00"),
            ("10 AM", "10:00"), ("A late / evening start", "18:00")]),
        _q("motivation", "And the reason behind this temporal rebellion?", "Why change it?",
           [("Students need more sleep", "sleep"),
            ("Reduce morning crowd & traffic", "decongest"),
            ("Free up mornings for internships/labs", "flexibility"),
            ("Just to see what breaks", "chaos")]),
        _q("scope", "How brave are we being?", "Apply to whom?",
           [("All classes", "all"), ("First-year classes only", "first_year"),
            ("One department", "one_dept")]),
        _q("group", "Whose day are we optimising for?", "Primary beneficiary?",
           [("Students", "students"), ("Faculty", "faculty"),
            ("Commuters", "commuters")]),
    ],
    "gate": [
        _q("action", "What are we doing to the gate?", "Gate change?",
           [("Move it near Parking Zone A", "move_parking"),
            ("Move it near the academic block", "move_academic"),
            ("Add a second gate", "add_gate"),
            ("Widen the current gate", "widen")]),
        _q("driver", "What's driving this?", "Main motivation?",
           [("Shorten the walk", "walk"),
            ("Cut entry traffic jams", "traffic"),
            ("Better security control", "security"),
            ("Smoother bus flow", "bus")]),
        _q("time", "When is the entry chaos worst?", "Peak window?",
           [("Morning", "morning"), ("Evening", "evening"), ("During events", "events")]),
        _q("group", "Who benefits most?", "Primary beneficiary?",
           [("Students", "students"), ("Faculty", "faculty"), ("Visitors", "visitors")]),
    ],
    "traffic": [
        _q("scope", "How far are we taking this?", "Scope of the change?",
           [("Central road pedestrian-only", "core_pedestrian"),
            ("Ban cars from the whole core", "core_carfree"),
            ("One-way loop system", "one_way"),
            ("Just slow traffic down", "calming")]),
        _q("time", "Applies when?", "When is it in force?",
           [("All day", "all_day"), ("Class hours only", "class_hours"),
            ("Peak hours only", "peak")]),
        _q("parking_plan", "Where do the displaced cars go?", "Parking plan?",
           [("Perimeter lots + walk in", "perimeter"),
            ("Build a new edge parking deck", "new_deck"),
            ("Push people to buses", "modal_shift")]),
        _q("group", "Who is this really for?", "Primary beneficiary?",
           [("Students walking between classes", "students"),
            ("Everyone's lungs", "environment"),
            ("Emergency response", "safety")]),
    ],
    "cafeteria": [
        _q("problem", "The cafeteria sin is...", "Core problem?",
           [("Queue is too long", "queue"),
            ("Not enough seats", "seating"),
            ("It's too far from class", "distance"),
            ("Crowd is dangerous at lunch", "crowd")]),
        _q("fix", "Your instinct is to...", "Preferred fix?",
           [("Move cafeteria to campus centre", "relocate_center"),
            ("Add more counters", "more_counters"),
            ("Stagger lunch breaks", "stagger"),
            ("Add a second food point", "second_point")]),
        _q("time", "Worst window?", "Peak?",
           [("Breakfast", "breakfast"), ("Lunch", "lunch"), ("Evening", "evening")]),
        _q("group", "Feeding whom, mainly?", "Primary group?",
           [("Day scholars", "students"), ("Hostel students", "hostel"), ("Staff", "staff")]),
    ],
    "sports": [
        _q("goal", "The sporting dream is...", "Goal?",
           [("More students actually playing", "participation"),
            ("A bigger / better ground", "capacity"),
            ("A dedicated sports day", "sports_day"),
            ("Better indoor facilities", "indoor")]),
        _q("when", "When does this happen?", "Timing?",
           [("Early morning", "morning"), ("Evening", "evening"),
            ("Friday afternoons", "friday"), ("Weekends", "weekend")]),
        _q("tradeoff", "What are you willing to trade?", "Acceptable cost?",
           [("Some class time", "class_time"),
            ("Some parking near the ground", "parking"),
            ("Nothing, make it free", "none")]),
        _q("group", "Who's the target athlete?", "Primary group?",
           [("All students", "students"), ("Hostelers", "hostel"),
            ("Staff & faculty too", "everyone")]),
    ],
    "transport": [
        _q("problem", "The bus problem is...", "Core issue?",
           [("Buses too infrequent at peak", "frequency"),
            ("Bus stop is too far", "location"),
            ("Buses stuck in traffic", "traffic"),
            ("Wrong timing vs classes", "timing")]),
        _q("fix", "Your fix of choice?", "Preferred fix?",
           [("Move bus stop near academic block", "relocate_stop"),
            ("Add buses in the peak window", "add_buses"),
            ("Shift bus timings", "retime"),
            ("Dedicated bus lane", "bus_lane")]),
        _q("time", "Which window matters?", "Peak?",
           [("Morning 8:30-9:15", "am_peak"), ("Evening 4:45-5:45", "pm_peak"),
            ("Lunch", "lunch")]),
        _q("group", "Riders you care about?", "Primary group?",
           [("Students", "students"), ("Faculty", "faculty"), ("Staff", "staff")]),
    ],
    "library": [
        _q("goal", "The library wish is...", "Goal?",
           [("More study space", "space"),
            ("Open later at night", "hours"),
            ("Move it to campus centre", "relocate"),
            ("Quieter zones", "quiet")]),
        _q("when", "Peak demand is...", "When?",
           [("Exam season evenings", "exam_eve"), ("Regular evenings", "evening"),
            ("Late night", "late_night")]),
        _q("tradeoff", "Willing to trade...", "Acceptable cost?",
           [("More night security & lighting cost", "security_cost"),
            ("Convert some classrooms", "convert_rooms"),
            ("Nothing", "none")]),
        _q("group", "For whom?", "Primary group?",
           [("Hostel students", "hostel"), ("Day scholars", "students"),
            ("Research scholars", "research")]),
    ],
    "washroom": [
        _q("problem", "The washroom issue is...", "Core issue?",
           [("Cleanliness / maintenance", "maintenance"),
            ("Not enough of them", "capacity"),
            ("Overcrowded between classes", "crowd"),
            ("Poorly located", "location")]),
        _q("time", "Worst window?", "Peak?",
           [("Between morning classes", "morning_break"),
            ("After lunch", "post_lunch"), ("During events", "events")]),
        _q("fix", "Fix of choice?", "Preferred fix?",
           [("More cleaning staff & rounds", "more_staff"),
            ("Build additional washrooms", "build_more"),
            ("Smart sensors + alerts", "sensors")]),
        _q("group", "Mainly affecting...", "Primary group?",
           [("Students", "students"), ("Faculty", "faculty"), ("Visitors", "visitors")]),
    ],
    "faculty": [
        _q("problem", "The faculty pain is...", "What's actually wrong?",
           [("Not enough teachers for the class load", "shortage"),
            ("Teachers hard to reach outside class", "availability"),
            ("Too many last-minute teacher swaps", "instability"),
            ("Want a specific class's teacher changed", "reassign")]),
        _q("when", "When does it bite hardest?", "Worst window?",
           [("During class hours", "class_hours"),
            ("During office / doubt-clearing hours", "office_hours"),
            ("Around exams", "exams"),
            ("All the time", "always")]),
        _q("fix", "Your preferred fix?", "How to solve it?",
           [("Hire / add faculty", "add_faculty"),
            ("Fixed, published office-hour slots", "office_slots"),
            ("Lock the timetable — no ad-hoc swaps", "stable_timetable"),
            ("Reassign the specific class", "reassign_class")]),
        _q("group", "Who is this for?", "Primary group?",
           [("All students", "students"),
            ("One department", "one_dept"),
            ("First-year students", "first_year")]),
    ],
    "creative": [
        _q("theme", "Pick your reality...", "Which theme?",
           [("🏰 Medieval city", "medieval"),
            ("🌙 Eternal night campus", "night"),
            ("🌲 Forest campus", "forest"),
            ("🚀 Futuristic campus", "futuristic")]),
        _q("intensity", "How committed are we?", "Intensity?",
           [("Just the vibe / colours", "vibe"),
            ("Rename every building", "rename"),
            ("Full transformation", "full")]),
        _q("keep", "One thing must stay normal. Which?", "Keep realistic?",
           [("The cafeteria", "cafeteria"), ("The library", "library"),
            ("Nothing, go wild", "none")]),
    ],
}

FALLBACK_TREE = QUESTION_TREES["schedule"]


def get_tree(domain: str):
    return QUESTION_TREES.get(domain, FALLBACK_TREE)


# ---------------------------------------------------------------------------
# 4. Structured wish assembly
# ---------------------------------------------------------------------------
def build_structured_wish(domain: str, raw_text: str, answers: dict) -> dict:
    """answers = {question_key: chosen_value}"""
    sw = dict(domain=domain, raw_text=raw_text.strip(), **answers)

    # normalise a few common fields the engine looks for
    sw.setdefault("affected_group", answers.get("group", "students"))
    if domain == "schedule":
        sw["problem"] = answers.get("motivation", "decongest")
        sw["preferred_solution"] = "shift_start_time"
        sw["time"] = answers.get("target_time", "10:00")
    elif domain == "parking":
        sw["preferred_solution"] = answers.get("solution", "increase_capacity")
    elif domain == "gate":
        sw["preferred_solution"] = answers.get("action", "move_parking")
    elif domain == "traffic":
        sw["preferred_solution"] = answers.get("scope", "core_pedestrian")
    elif domain == "cafeteria":
        sw["preferred_solution"] = answers.get("fix", "relocate_center")
    elif domain == "sports":
        sw["preferred_solution"] = answers.get("goal", "participation")
    elif domain == "transport":
        sw["preferred_solution"] = answers.get("fix", "relocate_stop")
    elif domain == "library":
        sw["preferred_solution"] = answers.get("goal", "hours")
    elif domain == "washroom":
        sw["preferred_solution"] = answers.get("fix", "more_staff")
    elif domain == "faculty":
        sw["problem"] = answers.get("problem", "availability")
        sw["preferred_solution"] = answers.get("fix", "office_slots")
    elif domain == "creative":
        sw["preferred_solution"] = "retheme"
        sw["theme"] = answers.get("theme", "medieval")
    return sw


def scenario_key(sw: dict) -> str:
    """Map a structured wish to a simulation-engine handler key."""
    d = sw["domain"]
    if d == "schedule":
        return "class_start_time"
    if d == "gate":
        return "move_gate"
    if d == "traffic":
        return "pedestrian_zone"
    if d == "cafeteria":
        return "cafeteria_center" if sw.get("preferred_solution") == "relocate_center" else "cafeteria_ops"
    if d == "sports":
        return "sports_participation"
    if d == "parking":
        return "parking_capacity"
    if d == "transport":
        return "bus_stop_move" if sw.get("preferred_solution") == "relocate_stop" else "bus_ops"
    if d == "library":
        return "library_hours"
    if d == "washroom":
        return "washroom_ops"
    if d == "faculty":
        return "faculty_ops"
    if d == "creative":
        return "creative_retheme"
    return "class_start_time"


def confirm_sentence(sw: dict) -> str:
    d = sw["domain"]
    g = sw.get("affected_group", "students")
    t = sw.get("time", "")
    templ = {
        "schedule": f"You want class start moved to {sw.get('time','10:00')} "
                    f"({sw.get('scope','all')} classes), mainly to help {g} with '{sw.get('motivation','decongest')}'.",
        "parking":  f"You want to fix '{sw.get('problem','capacity')}' parking pain in the {sw.get('time','evening')} "
                    f"for {g}, by choosing to '{sw.get('preferred_solution')}'.",
        "gate":     f"You want to '{sw.get('preferred_solution')}' to help {g}, driven by '{sw.get('driver','walk')}', "
                    f"worst in the {sw.get('time','morning')}.",
        "traffic":  f"You want '{sw.get('preferred_solution')}' in force during '{sw.get('time','peak')}', "
                    f"with displaced cars going to '{sw.get('parking_plan','perimeter')}', for {g}.",
        "cafeteria":f"You want to fix '{sw.get('problem','queue')}' at {sw.get('time','lunch')} by '{sw.get('fix')}', for {g}.",
        "sports":   f"You want '{sw.get('goal','participation')}' happening at '{sw.get('when','evening')}', "
                    f"trading '{sw.get('tradeoff','none')}', for {g}.",
        "transport":f"You want to fix '{sw.get('problem','frequency')}' in the '{sw.get('time','am_peak')}' by '{sw.get('fix')}', for {g}.",
        "library":  f"You want '{sw.get('goal','hours')}' for the library during '{sw.get('when','evening')}', for {g}.",
        "washroom": f"You want to fix '{sw.get('problem','maintenance')}' at '{sw.get('time','morning_break')}' via '{sw.get('fix')}', for {g}.",
        "faculty":  f"You want to fix faculty '{sw.get('problem','availability')}' (worst during '{sw.get('when','class_hours')}') "
                    f"by '{sw.get('fix','office_slots')}', for {g}.",
        "creative": f"You want the campus re-themed as '{sw.get('theme','medieval')}' at intensity '{sw.get('intensity','vibe')}', "
                    f"keeping '{sw.get('keep','none')}' normal.",
    }
    return templ.get(d, "You want a campus change. I have decoded it.")


# ---------------------------------------------------------------------------
# 5. Recommended / inspiration wishes
# ---------------------------------------------------------------------------
RECOMMENDED_WISHES = [
    ("✨", "Move the front gate near parking", "gate"),
    ("🌙", "Start classes at 10 AM", "schedule"),
    ("🏰", "Turn the campus into a medieval city", "creative"),
    ("🚶", "Make the central road pedestrian-only", "traffic"),
    ("🏟", "Turn Friday into sports day", "sports"),
    ("🚌", "Move the bus stop closer to the academic block", "transport"),
    ("🍔", "Put the cafeteria at the center of campus", "cafeteria"),
]
