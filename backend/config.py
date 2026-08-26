import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "passline")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
FEATHERLESS_API_KEY = os.getenv("FEATHERLESS_API_KEY", "")
FEATHERLESS_MODEL = os.getenv("FEATHERLESS_MODEL", "meta-llama/Meta-Llama-3.1-70B-Instruct")
ANVILGPT_API_KEY = os.getenv("ANVILGPT_API_KEY", "")
ANVILGPT_BASE_URL = os.getenv("ANVILGPT_BASE_URL", "https://anvilgpt.rcac.purdue.edu/api")
ANVILGPT_MODEL = os.getenv("ANVILGPT_MODEL", "llama3.2:latest")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
FRAMES_DIR = Path(os.getenv("FRAMES_DIR", "./frames"))
REPORTS_DIR = Path(os.getenv("REPORTS_DIR", "./reports"))
DEPTH_MODEL_PATH = Path(os.getenv("DEPTH_MODEL_PATH", "./checkpoints/depth_anything_v2_vits.pth"))

for d in (UPLOAD_DIR, FRAMES_DIR, REPORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

BLUR_THRESHOLD = 100.0
SSIM_DUPLICATE_THRESHOLD = 0.92
MIN_FRAMES = 3
MAX_FRAMES = 20
EXTRACT_FPS = 2

MODULE_TYPES = [
    # Universal
    "entrance", "hallway", "restroom", "parking",
    "elevator", "stairway", "signage", "drinking_fountain",
    # Dining / Food Service
    "dining", "counter", "outdoor_seating", "cafeteria", "concession",
    # Retail
    "sales_floor", "checkout", "fitting_room",
    # Office / Professional
    "reception", "conference_room", "break_room",
    # Medical / Healthcare
    "waiting_room", "exam_room", "patient_room", "pharmacy",
    # Hotel / Lodging
    "lobby", "guest_room", "pool", "fitness_center",
    # Education
    "classroom", "gymnasium", "auditorium", "library",
    # Assembly / Entertainment
    "assembly_seating", "stage", "ticket_booth",
]

MODULE_INSTRUCTIONS = {
    # ── Universal ────────────────────────────────────────────────────────────
    "entrance": {
        "title": "Entrance / Door",
        "instructions": (
            "Walk slowly through your entrance area. Include the door fully open if possible, "
            "the handle/hardware, the threshold at floor level, and any signage nearby. "
            "Place a credit card flat on the door frame for measurement reference if possible. "
            "Record for 15-30 seconds."
        ),
        "tips": [
            "Hold phone at chest height",
            "Move slowly and steadily",
            "Ensure good lighting",
        ],
    },
    "hallway": {
        "title": "Hallway / Corridor",
        "instructions": (
            "Walk slowly down the hallway. Show the full width, any obstacles, signage, and "
            "floor surface. Place a credit card on the floor for scale. Record for 15-30 seconds."
        ),
        "tips": [
            "Walk down the center",
            "Capture any narrowing points",
            "Show both walls",
        ],
    },
    "restroom": {
        "title": "Restroom",
        "instructions": (
            "Record a slow pan of the entire restroom. Show the toilet area including grab bar "
            "locations (or absence), the sink and faucet, the mirror, the door, and the overall "
            "floor space. Place a credit card on a flat surface for scale. Record for 20-40 seconds."
        ),
        "tips": [
            "Start at the door, pan clockwise",
            "Show grab bar mounting points clearly",
            "Capture the floor clearance area",
        ],
    },
    "parking": {
        "title": "Parking Lot",
        "instructions": (
            "Walk through the accessible parking area. Show the parking spaces, signage (both "
            "ground markings and vertical signs), access aisles, and the path from parking to "
            "the building entrance including any curb ramps. Record for 20-40 seconds."
        ),
        "tips": [
            "Capture signage from a readable distance",
            "Show the path to the entrance",
            "Include curb ramp if present",
        ],
    },
    "elevator": {
        "title": "Elevator",
        "instructions": (
            "Record the elevator call button panel, the interior cab including floor area and "
            "control panel height, door width when fully open, and any braille/tactile signage. "
            "Record for 20-30 seconds."
        ),
        "tips": [
            "Show the call button height from the floor",
            "Capture the interior control panel",
            "Show the door width when open",
        ],
    },
    "stairway": {
        "title": "Stairs & Handrails",
        "instructions": (
            "Walk the full length of the stairway. Show the handrails on both sides, the height "
            "and extension of handrails beyond the top and bottom steps, stair nosing contrast, "
            "and any tactile warning strips. Record for 20-30 seconds."
        ),
        "tips": [
            "Show handrail height and grip surface",
            "Capture both sides of the stairway",
            "Show the top and bottom handrail extensions",
        ],
    },
    "signage": {
        "title": "Signage & Wayfinding",
        "instructions": (
            "Walk through the facility capturing all directional and room-identification signage. "
            "Focus on sign height, braille presence, high-contrast text, and mounting location "
            "relative to door frames. Record for 20-40 seconds."
        ),
        "tips": [
            "Get close enough to read sign text",
            "Show sign height from floor",
            "Capture braille panels if present",
        ],
    },
    "drinking_fountain": {
        "title": "Drinking Fountain",
        "instructions": (
            "Record the drinking fountain(s) showing the height of the spout and controls, "
            "knee clearance underneath (if a hi-lo fountain), and the forward reach distance. "
            "Place a credit card on the spout level for scale. Record for 15-20 seconds."
        ),
        "tips": [
            "Show spout height from the floor",
            "Capture knee clearance underneath",
            "Include both hi and lo units if present",
        ],
    },

    # ── Dining / Food Service ─────────────────────────────────────────────
    "dining": {
        "title": "Dining Area",
        "instructions": (
            "Pan through the dining area showing table heights, aisle widths between tables, "
            "and accessible seating arrangements. Record for 20-40 seconds."
        ),
        "tips": [
            "Show table heights at eye level",
            "Capture aisle widths",
            "Include accessible seating",
        ],
    },
    "counter": {
        "title": "Service Counter",
        "instructions": (
            "Record the service counter showing its height from the floor, accessible section "
            "if any, and the approach space. Place a credit card on the counter for scale. "
            "Record for 15-30 seconds."
        ),
        "tips": [
            "Show the counter height clearly",
            "Capture the accessible lowered section",
            "Show approach clearance",
        ],
    },
    "outdoor_seating": {
        "title": "Outdoor Seating",
        "instructions": (
            "Record the outdoor seating area showing table heights, surface material, route "
            "from the entrance, and any barriers or obstacles. Record for 20-30 seconds."
        ),
        "tips": [
            "Show the path from entrance to outdoor area",
            "Capture surface texture (pavers, gravel, etc.)",
            "Include any accessible table setups",
        ],
    },
    "cafeteria": {
        "title": "Cafeteria / Dining Hall",
        "instructions": (
            "Walk through the cafeteria showing the food service line height and reach, tray "
            "slide height, seating area aisles, and accessible table arrangements. "
            "Record for 25-40 seconds."
        ),
        "tips": [
            "Show food service counter height",
            "Capture tray slide accessibility",
            "Show aisle widths between tables",
        ],
    },
    "concession": {
        "title": "Concession Stand",
        "instructions": (
            "Record the concession stand showing counter height, an accessible lowered section "
            "if present, the approach space, and any queue barriers. Record for 15-25 seconds."
        ),
        "tips": [
            "Show full counter height from floor",
            "Capture accessible section if present",
            "Show queue/line setup",
        ],
    },

    # ── Retail ────────────────────────────────────────────────────────────
    "sales_floor": {
        "title": "Sales Floor & Aisles",
        "instructions": (
            "Walk down representative aisles showing the clear width between merchandise "
            "displays, any protruding objects, floor surface, and accessible route to all "
            "areas of the store. Record for 25-40 seconds."
        ),
        "tips": [
            "Walk the narrowest aisles first",
            "Capture any protruding displays",
            "Show the path to all departments",
        ],
    },
    "checkout": {
        "title": "Checkout Counter",
        "instructions": (
            "Record the checkout counter area showing counter height, accessible lowered "
            "section if present, PIN pad placement, approach clearance, and queue aisle width. "
            "Record for 15-25 seconds."
        ),
        "tips": [
            "Show counter height from floor",
            "Capture PIN pad position and reach",
            "Show queue aisle width",
        ],
    },
    "fitting_room": {
        "title": "Fitting / Dressing Room",
        "instructions": (
            "Record the accessible fitting room showing the door width, interior turning space, "
            "bench height and clear floor space beside it, and hook heights. "
            "Record for 20-30 seconds."
        ),
        "tips": [
            "Show door clear width",
            "Capture interior turning radius space",
            "Show bench height and side clearance",
        ],
    },

    # ── Office / Professional ─────────────────────────────────────────────
    "reception": {
        "title": "Reception / Lobby Desk",
        "instructions": (
            "Record the reception desk showing counter height, accessible lowered section, "
            "approach space, and any barriers between the visitor and staff. "
            "Record for 15-25 seconds."
        ),
        "tips": [
            "Show full counter height",
            "Capture accessible lowered section",
            "Show approach clearance",
        ],
    },
    "conference_room": {
        "title": "Conference Room",
        "instructions": (
            "Record the conference room showing the door width, table height, knee clearance "
            "under the table, turning space in the room, and accessible path to all seats. "
            "Record for 20-35 seconds."
        ),
        "tips": [
            "Show door width when fully open",
            "Capture table height and knee clearance",
            "Show turning space in the room",
        ],
    },
    "break_room": {
        "title": "Break Room / Kitchen",
        "instructions": (
            "Record the break room showing counter and appliance heights, knee clearance under "
            "the sink, microwave and coffee maker reach distance, and floor clearance. "
            "Record for 20-30 seconds."
        ),
        "tips": [
            "Show sink and counter heights",
            "Capture appliance reach distances",
            "Show knee clearance under sink",
        ],
    },

    # ── Medical / Healthcare ──────────────────────────────────────────────
    "waiting_room": {
        "title": "Waiting Room",
        "instructions": (
            "Pan through the waiting room showing seating arrangements with accessible spaces "
            "for wheelchairs, aisle widths, check-in counter height, and route from entrance. "
            "Record for 20-35 seconds."
        ),
        "tips": [
            "Show wheelchair-accessible seating spaces",
            "Capture aisle widths between chairs",
            "Show check-in counter height",
        ],
    },
    "exam_room": {
        "title": "Examination Room",
        "instructions": (
            "Record the exam room showing door width, exam table height and any adjustable "
            "mechanism, turning space, accessible equipment placement, and grab bars if present. "
            "Record for 20-35 seconds."
        ),
        "tips": [
            "Show exam table height from floor",
            "Capture door width",
            "Show turning space near table",
        ],
    },
    "patient_room": {
        "title": "Patient Room",
        "instructions": (
            "Record the patient room showing door width, clear floor space on both sides of the "
            "bed, bathroom access, call button placement, and any overhead reach equipment. "
            "Record for 25-40 seconds."
        ),
        "tips": [
            "Show clear floor space on each side of the bed",
            "Capture bathroom door width",
            "Show call button placement",
        ],
    },
    "pharmacy": {
        "title": "Pharmacy Counter",
        "instructions": (
            "Record the pharmacy counter showing counter height, accessible consultation window "
            "or lowered section, approach space, and PIN pad placement. Record for 15-25 seconds."
        ),
        "tips": [
            "Show full counter height",
            "Capture consultation area",
            "Show accessible reach distances",
        ],
    },

    # ── Hotel / Lodging ───────────────────────────────────────────────────
    "lobby": {
        "title": "Hotel Lobby",
        "instructions": (
            "Walk through the lobby showing the check-in desk height and accessible section, "
            "seating arrangement, accessible route to elevators and amenities, and any "
            "floor surface changes. Record for 25-40 seconds."
        ),
        "tips": [
            "Show check-in desk height",
            "Capture route to elevator",
            "Show floor surface transitions",
        ],
    },
    "guest_room": {
        "title": "Accessible Guest Room",
        "instructions": (
            "Record the accessible guest room showing door width, clear floor space around "
            "the bed, bathroom with grab bars and roll-in shower or tub, closet rod height, "
            "and accessible controls. Record for 35-60 seconds."
        ),
        "tips": [
            "Show clear floor space on each side of the bed",
            "Capture bathroom grab bars",
            "Show roll-in shower clearance",
        ],
    },
    "pool": {
        "title": "Pool & Spa Area",
        "instructions": (
            "Record the pool area showing the pool lift or sloped entry, deck surface, "
            "changing area access, and route from the locker room to the pool. "
            "Record for 25-40 seconds."
        ),
        "tips": [
            "Show pool lift or entry ramp",
            "Capture deck surface (slip resistance)",
            "Show route from changing area",
        ],
    },
    "fitness_center": {
        "title": "Fitness Center",
        "instructions": (
            "Walk through the fitness center showing equipment aisle widths, accessible "
            "equipment (adjustable machines), locker height, and route from entrance. "
            "Record for 25-40 seconds."
        ),
        "tips": [
            "Show aisle widths between equipment",
            "Capture accessible machine examples",
            "Show locker and bench heights",
        ],
    },

    # ── Education ─────────────────────────────────────────────────────────
    "classroom": {
        "title": "Classroom",
        "instructions": (
            "Record the classroom showing door width, aisle widths between desks, an accessible "
            "desk or table with knee clearance, blackboard/whiteboard reach height, and turning "
            "space. Record for 25-40 seconds."
        ),
        "tips": [
            "Show aisle width between desks",
            "Capture accessible desk knee clearance",
            "Show whiteboard reach height",
        ],
    },
    "gymnasium": {
        "title": "Gymnasium / Sports Area",
        "instructions": (
            "Walk through the gymnasium showing accessible spectator seating, route from "
            "entrance to the floor, locker room access, and any fixed equipment clearances. "
            "Record for 25-40 seconds."
        ),
        "tips": [
            "Show accessible spectator area",
            "Capture route from entrance to floor",
            "Show locker room door widths",
        ],
    },
    "auditorium": {
        "title": "Auditorium / Assembly Hall",
        "instructions": (
            "Record the auditorium showing accessible seating spaces (wheelchair locations), "
            "companion seat placement, route from entrance to accessible seating, stage access "
            "ramp or lift, and sight lines. Record for 30-50 seconds."
        ),
        "tips": [
            "Show wheelchair seating spaces and companion seats",
            "Capture route to accessible seating",
            "Show stage access ramp or lift",
        ],
    },
    "library": {
        "title": "Library",
        "instructions": (
            "Walk through the library showing aisle widths between stacks, reach height of "
            "shelves, accessible study table knee clearance, catalog terminal height, and "
            "checkout counter. Record for 25-40 seconds."
        ),
        "tips": [
            "Show aisle width between shelves",
            "Capture shelf reach height",
            "Show study table knee clearance",
        ],
    },

    # ── Assembly / Entertainment ──────────────────────────────────────────
    "assembly_seating": {
        "title": "Assembly Seating Area",
        "instructions": (
            "Record the seating area showing wheelchair accessible spaces, companion seating, "
            "route from entrance, sight lines to the stage or screen, and aisle widths. "
            "Record for 25-40 seconds."
        ),
        "tips": [
            "Show wheelchair space dimensions",
            "Capture companion seat placement",
            "Show route from entrance to seating",
        ],
    },
    "stage": {
        "title": "Stage / Performance Access",
        "instructions": (
            "Record the stage access route showing any ramps, lifts, or steps, handrail "
            "placement, approach clearance, and the performer/presenter area. "
            "Record for 20-35 seconds."
        ),
        "tips": [
            "Show ramp or lift for stage access",
            "Capture handrail height and extension",
            "Show approach clearance",
        ],
    },
    "ticket_booth": {
        "title": "Ticket / Box Office",
        "instructions": (
            "Record the ticket booth or box office showing counter height, accessible window "
            "or lowered section, approach space, and any queue barriers. Record for 15-25 seconds."
        ),
        "tips": [
            "Show counter/window height from floor",
            "Capture accessible lowered section",
            "Show approach clearance",
        ],
    },
}
