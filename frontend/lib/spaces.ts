// Every space type the backend can audit: what to show on video and what gets checked.
// Single source for the space list, capture and processing pages.

export interface SpaceInfo {
  title: string;
  checks: string; // what Passline looks for in this space
  instructions: string;
  seconds: string; // suggested recording length
  tips: string[];
}

export const SPACES: Record<string, SpaceInfo> = {
  entrance: {
    title: "Entrance / Door",
    checks: "Door width, hardware, threshold, signage, ramps",
    instructions: "Walk slowly through your entrance area. Include the door fully open if possible, the handle/hardware, the threshold at floor level, and any signage nearby. Place a sheet of printer paper or a credit card flat on the door frame if you can, so measurements have a known scale.",
    seconds: "15\u201330",
    tips: ["Hold phone at chest height", "Move slowly and steadily", "Ensure good lighting"],
  },
  hallway: {
    title: "Hallway / Corridor",
    checks: "Width, obstructions, floor surface, signage",
    instructions: "Walk slowly down the hallway. Show the full width, any obstacles, signage, and floor surface. Place a sheet of printer paper or a credit card on the floor for scale.",
    seconds: "15\u201330",
    tips: ["Walk down the center", "Capture any narrowing points", "Show both walls"],
  },
  restroom: {
    title: "Restroom",
    checks: "Grab bars, faucet, door swing, clearance, mirror",
    instructions: "Record a slow pan of the entire restroom. Show the toilet area including grab bar locations (or absence), the sink and faucet, the mirror, the door, and the overall floor space. Place a sheet of printer paper or a credit card on a flat surface for scale.",
    seconds: "20\u201340",
    tips: ["Start at the door, pan clockwise", "Show grab bar mounting points clearly", "Capture the floor clearance area"],
  },
  parking: {
    title: "Parking Lot",
    checks: "Accessible spaces, signage, access aisles, curb ramps",
    instructions: "Walk through the accessible parking area. Show the parking spaces, signage (both ground markings and vertical signs), access aisles, and the path from parking to the building entrance including any curb ramps.",
    seconds: "20\u201340",
    tips: ["Capture signage from a readable distance", "Show the path to the entrance", "Include curb ramp if present"],
  },
  elevator: {
    title: "Elevator",
    checks: "Call button height, cab size, controls, braille",
    instructions: "Record the elevator call button panel, the interior cab including floor area and control panel height, door width when fully open, and any braille/tactile signage.",
    seconds: "20\u201330",
    tips: ["Show the call button height from the floor", "Capture the interior control panel", "Show the door width when open"],
  },
  stairway: {
    title: "Stairs & Handrails",
    checks: "Handrail height, extensions, nosing contrast",
    instructions: "Walk the full length of the stairway. Show the handrails on both sides, the height and extension of handrails beyond the top and bottom steps, stair nosing contrast, and any tactile warning strips.",
    seconds: "20\u201330",
    tips: ["Show handrail height and grip surface", "Capture both sides of the stairway", "Show the top and bottom handrail extensions"],
  },
  signage: {
    title: "Signage & Wayfinding",
    checks: "Height, braille, high contrast, mounting location",
    instructions: "Walk through the facility capturing all directional and room-identification signage. Focus on sign height, braille presence, high-contrast text, and mounting location relative to door frames.",
    seconds: "20\u201340",
    tips: ["Get close enough to read sign text", "Show sign height from floor", "Capture braille panels if present"],
  },
  drinking_fountain: {
    title: "Drinking Fountain",
    checks: "Spout height, knee clearance, hi-lo units",
    instructions: "Record the drinking fountain(s) showing the height of the spout and controls, knee clearance underneath (if a hi-lo fountain), and the forward reach distance. Place a sheet of printer paper or a credit card on the spout level for scale.",
    seconds: "15\u201320",
    tips: ["Show spout height from the floor", "Capture knee clearance underneath", "Include both hi and lo units if present"],
  },
  dining: {
    title: "Dining Area",
    checks: "Table heights, aisle widths, accessible seating",
    instructions: "Pan through the dining area showing table heights, aisle widths between tables, and accessible seating arrangements.",
    seconds: "20\u201340",
    tips: ["Show table heights at eye level", "Capture aisle widths", "Include accessible seating"],
  },
  counter: {
    title: "Service Counter",
    checks: "Counter height, accessible section, approach clearance",
    instructions: "Record the service counter showing its height from the floor, accessible section if any, and the approach space. Place a sheet of printer paper or a credit card on the counter for scale.",
    seconds: "15\u201330",
    tips: ["Show the counter height clearly", "Capture the accessible lowered section", "Show approach clearance"],
  },
  outdoor_seating: {
    title: "Outdoor Seating",
    checks: "Surface, route from entrance, accessible tables",
    instructions: "Record the outdoor seating area showing table heights, surface material, route from the entrance, and any barriers or obstacles.",
    seconds: "20\u201330",
    tips: ["Show the path from entrance to outdoor area", "Capture surface texture (pavers, gravel, etc.)", "Include any accessible table setups"],
  },
  cafeteria: {
    title: "Cafeteria / Dining Hall",
    checks: "Food line height, tray slide, aisle widths",
    instructions: "Walk through the cafeteria showing the food service line height and reach, tray slide height, seating area aisles, and accessible table arrangements.",
    seconds: "25\u201340",
    tips: ["Show food service counter height", "Capture tray slide accessibility", "Show aisle widths between tables"],
  },
  concession: {
    title: "Concession Stand",
    checks: "Counter height, accessible section, queue setup",
    instructions: "Record the concession stand showing counter height, an accessible lowered section if present, the approach space, and any queue barriers.",
    seconds: "15\u201325",
    tips: ["Show full counter height from floor", "Capture accessible section if present", "Show queue/line setup"],
  },
  sales_floor: {
    title: "Sales Floor & Aisles",
    checks: "Aisle width, protruding displays, accessible route",
    instructions: "Walk down representative aisles showing the clear width between merchandise displays, any protruding objects, floor surface, and accessible route to all areas of the store.",
    seconds: "25\u201340",
    tips: ["Walk the narrowest aisles first", "Capture any protruding displays", "Show the path to all departments"],
  },
  checkout: {
    title: "Checkout Counter",
    checks: "Counter height, PIN pad reach, queue width",
    instructions: "Record the checkout counter area showing counter height, accessible lowered section if present, PIN pad placement, approach clearance, and queue aisle width.",
    seconds: "15\u201325",
    tips: ["Show counter height from floor", "Capture PIN pad position and reach", "Show queue aisle width"],
  },
  fitting_room: {
    title: "Fitting Room",
    checks: "Door width, turning space, bench height",
    instructions: "Record the accessible fitting room showing the door width, interior turning space, bench height and clear floor space beside it, and hook heights.",
    seconds: "20\u201330",
    tips: ["Show door clear width", "Capture interior turning radius space", "Show bench height and side clearance"],
  },
  reception: {
    title: "Reception Desk",
    checks: "Counter height, accessible section, approach space",
    instructions: "Record the reception desk showing counter height, accessible lowered section, approach space, and any barriers between the visitor and staff.",
    seconds: "15\u201325",
    tips: ["Show full counter height", "Capture accessible lowered section", "Show approach clearance"],
  },
  conference_room: {
    title: "Conference Room",
    checks: "Door width, table height, knee clearance, turning space",
    instructions: "Record the conference room showing the door width, table height, knee clearance under the table, turning space in the room, and accessible path to all seats.",
    seconds: "20\u201335",
    tips: ["Show door width when fully open", "Capture table height and knee clearance", "Show turning space in the room"],
  },
  break_room: {
    title: "Break Room / Kitchen",
    checks: "Counter heights, sink clearance, appliance reach",
    instructions: "Record the break room showing counter and appliance heights, knee clearance under the sink, microwave and coffee maker reach distance, and floor clearance.",
    seconds: "20\u201330",
    tips: ["Show sink and counter heights", "Capture appliance reach distances", "Show knee clearance under sink"],
  },
  waiting_room: {
    title: "Waiting Room",
    checks: "Wheelchair spaces, aisle widths, check-in counter",
    instructions: "Pan through the waiting room showing seating arrangements with accessible spaces for wheelchairs, aisle widths, check-in counter height, and route from entrance.",
    seconds: "20\u201335",
    tips: ["Show wheelchair-accessible seating spaces", "Capture aisle widths between chairs", "Show check-in counter height"],
  },
  exam_room: {
    title: "Examination Room",
    checks: "Exam table height, door width, turning space",
    instructions: "Record the exam room showing door width, exam table height and any adjustable mechanism, turning space, accessible equipment placement, and grab bars if present.",
    seconds: "20\u201335",
    tips: ["Show exam table height from floor", "Capture door width", "Show turning space near table"],
  },
  patient_room: {
    title: "Patient Room",
    checks: "Bed clearance, bathroom access, call button",
    instructions: "Record the patient room showing door width, clear floor space on both sides of the bed, bathroom access, call button placement, and any overhead reach equipment.",
    seconds: "25\u201340",
    tips: ["Show clear floor space on each side of the bed", "Capture bathroom door width", "Show call button placement"],
  },
  pharmacy: {
    title: "Pharmacy Counter",
    checks: "Counter height, consultation window, PIN pad",
    instructions: "Record the pharmacy counter showing counter height, accessible consultation window or lowered section, approach space, and PIN pad placement.",
    seconds: "15\u201325",
    tips: ["Show full counter height", "Capture consultation area", "Show accessible reach distances"],
  },
  lobby: {
    title: "Hotel Lobby",
    checks: "Check-in desk height, route to elevator, seating",
    instructions: "Walk through the lobby showing the check-in desk height and accessible section, seating arrangement, accessible route to elevators and amenities, and any floor surface changes.",
    seconds: "25\u201340",
    tips: ["Show check-in desk height", "Capture route to elevator", "Show floor surface transitions"],
  },
  guest_room: {
    title: "Accessible Guest Room",
    checks: "Bed clearance, roll-in shower, grab bars, controls",
    instructions: "Record the accessible guest room showing door width, clear floor space around the bed, bathroom with grab bars and roll-in shower or tub, closet rod height, and accessible controls.",
    seconds: "35\u201360",
    tips: ["Show clear floor space on each side of the bed", "Capture bathroom grab bars", "Show roll-in shower clearance"],
  },
  pool: {
    title: "Pool & Spa Area",
    checks: "Pool lift or sloped entry, deck surface, locker access",
    instructions: "Record the pool area showing the pool lift or sloped entry, deck surface, changing area access, and route from the locker room to the pool.",
    seconds: "25\u201340",
    tips: ["Show pool lift or entry ramp", "Capture deck surface (slip resistance)", "Show route from changing area"],
  },
  fitness_center: {
    title: "Fitness Center",
    checks: "Equipment aisles, accessible machines, locker heights",
    instructions: "Walk through the fitness center showing equipment aisle widths, accessible equipment (adjustable machines), locker height, and route from entrance.",
    seconds: "25\u201340",
    tips: ["Show aisle widths between equipment", "Capture accessible machine examples", "Show locker and bench heights"],
  },
  classroom: {
    title: "Classroom",
    checks: "Desk aisles, accessible desk, whiteboard reach",
    instructions: "Record the classroom showing door width, aisle widths between desks, an accessible desk or table with knee clearance, blackboard/whiteboard reach height, and turning space.",
    seconds: "25\u201340",
    tips: ["Show aisle width between desks", "Capture accessible desk knee clearance", "Show whiteboard reach height"],
  },
  gymnasium: {
    title: "Gymnasium",
    checks: "Accessible seating, route to floor, locker access",
    instructions: "Walk through the gymnasium showing accessible spectator seating, route from entrance to the floor, locker room access, and any fixed equipment clearances.",
    seconds: "25\u201340",
    tips: ["Show accessible spectator area", "Capture route from entrance to floor", "Show locker room door widths"],
  },
  auditorium: {
    title: "Auditorium",
    checks: "Wheelchair spaces, companion seats, stage access",
    instructions: "Record the auditorium showing accessible seating spaces (wheelchair locations), companion seat placement, route from entrance to accessible seating, stage access ramp or lift, and sight lines.",
    seconds: "30\u201350",
    tips: ["Show wheelchair seating spaces and companion seats", "Capture route to accessible seating", "Show stage access ramp or lift"],
  },
  library: {
    title: "Library",
    checks: "Aisle widths, shelf reach, study tables, checkout",
    instructions: "Walk through the library showing aisle widths between stacks, reach height of shelves, accessible study table knee clearance, catalog terminal height, and checkout counter.",
    seconds: "25\u201340",
    tips: ["Show aisle width between shelves", "Capture shelf reach height", "Show study table knee clearance"],
  },
  assembly_seating: {
    title: "Assembly Seating",
    checks: "Wheelchair spaces, companion seats, sight lines",
    instructions: "Record the seating area showing wheelchair accessible spaces, companion seating, route from entrance, sight lines to the stage or screen, and aisle widths.",
    seconds: "25\u201340",
    tips: ["Show wheelchair space dimensions", "Capture companion seat placement", "Show route from entrance to seating"],
  },
  stage: {
    title: "Stage Access",
    checks: "Ramp or lift, handrails, approach clearance",
    instructions: "Record the stage access route showing any ramps, lifts, or steps, handrail placement, approach clearance, and the performer/presenter area.",
    seconds: "20\u201335",
    tips: ["Show ramp or lift for stage access", "Capture handrail height and extension", "Show approach clearance"],
  },
  ticket_booth: {
    title: "Ticket / Box Office",
    checks: "Counter height, accessible window, approach space",
    instructions: "Record the ticket booth or box office showing counter height, accessible window or lowered section, approach space, and any queue barriers.",
    seconds: "15\u201325",
    tips: ["Show counter/window height from floor", "Capture accessible lowered section", "Show approach clearance"],
  },
};

export const SPACE_GROUPS: { label: string; keys: string[] }[] = [
  { label: "Entrances & Circulation",  keys: ["entrance", "hallway", "elevator", "stairway"] },
  { label: "Core Facilities",          keys: ["restroom", "parking", "signage", "drinking_fountain"] },
  { label: "Dining & Food Service",    keys: ["dining", "counter", "outdoor_seating", "cafeteria", "concession"] },
  { label: "Retail",                   keys: ["sales_floor", "checkout", "fitting_room"] },
  { label: "Office & Professional",    keys: ["reception", "conference_room", "break_room"] },
  { label: "Medical & Healthcare",     keys: ["waiting_room", "exam_room", "patient_room", "pharmacy"] },
  { label: "Hotel & Lodging",          keys: ["lobby", "guest_room", "pool", "fitness_center"] },
  { label: "Education",                keys: ["classroom", "cafeteria", "gymnasium", "auditorium", "library"] },
  { label: "Assembly & Entertainment", keys: ["assembly_seating", "stage", "concession", "ticket_booth"] },
];

export function spaceInfo(key: string | null | undefined): SpaceInfo {
  if (key && SPACES[key]) return SPACES[key];
  const title = key ? key.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase()) : "Space";
  return {
    title,
    checks: "",
    instructions: "Record this space slowly and steadily, showing every wall, the floor and any fixtures.",
    seconds: "15–30",
    tips: ["Hold the phone at chest height", "Move slowly", "Make sure the space is well lit"],
  };
}
