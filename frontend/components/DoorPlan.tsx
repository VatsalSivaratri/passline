// Plan view of a doorway, drawn the way an architect would: two wall stubs,
// the door leaf open at 90 degrees with its swing arc, and the clear-width
// dimension that ADA 404.2.3 requires. Purely illustrative.

export default function DoorPlan({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 420 330"
      className={className}
      role="img"
      aria-label="Plan drawing of a doorway with the door open 90 degrees and a 32 inch minimum clear width dimension"
    >
      <defs>
        <pattern id="wall-hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <line x1="0" y1="0" x2="0" y2="8" stroke="#14243B" strokeWidth="1.5" />
        </pattern>
      </defs>

      {/* walls */}
      <rect x="10" y="200" width="90" height="26" fill="url(#wall-hatch)" stroke="#14243B" strokeWidth="2.5" />
      <rect x="320" y="200" width="90" height="26" fill="url(#wall-hatch)" stroke="#14243B" strokeWidth="2.5" />

      {/* door stop on the latch side */}
      <rect x="312" y="200" width="8" height="26" fill="#14243B" />

      {/* door leaf, open 90 degrees, hinged at the left jamb */}
      <rect x="100" y="34" width="9" height="166" fill="#FFFFFF" stroke="#14243B" strokeWidth="2.5" />

      {/* swing arc */}
      <path d="M 109 34 A 203 203 0 0 1 312 200" fill="none" stroke="#14243B" strokeWidth="1.5" strokeDasharray="6 5" />

      {/* clear width dimension: face of door to the stop */}
      <g stroke="#14243B" strokeWidth="1.5">
        <line x1="109" y1="252" x2="109" y2="282" />
        <line x1="312" y1="252" x2="312" y2="282" />
        <line x1="109" y1="270" x2="312" y2="270" />
        <line x1="101" y1="278" x2="117" y2="262" strokeWidth="2.5" />
        <line x1="304" y1="278" x2="320" y2="262" strokeWidth="2.5" />
      </g>
      <rect x="122" y="284" width="178" height="34" fill="#FFD23F" />
      <text x="211" y="307" textAnchor="middle" fontSize="19" fontWeight="800" fill="#14243B" fontFamily="inherit">
        32 in min. clear
      </text>
    </svg>
  );
}
