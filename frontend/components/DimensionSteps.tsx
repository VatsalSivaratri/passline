// A dimension line, as on a construction drawing, used as a step track.
// Each step is a segment between end ticks; finished segments are drawn solid,
// the current one is highlighted, later ones are dashed.

interface Step {
  label: string;
  state: "done" | "current" | "todo" | "failed";
}

export default function DimensionSteps({ steps, label }: { steps: Step[]; label: string }) {
  return (
    <ol aria-label={label} className="grid w-full" style={{ gridTemplateColumns: `repeat(${steps.length}, minmax(0, 1fr))` }}>
      {steps.map((s, i) => (
        <li
          key={s.label}
          aria-current={s.state === "current" ? "step" : undefined}
          className="relative pt-5"
        >
          {/* the line segment with its end ticks */}
          <span aria-hidden className="absolute left-0 right-0 top-2 flex items-center">
            <span className={`h-4 w-[2px] ${tick(s.state)}`} />
            <span
              className={`h-0 flex-1 ${
                s.state === "done"
                  ? "border-t-2 border-ink"
                  : s.state === "current"
                  ? "border-t-[6px] border-mark"
                  : s.state === "failed"
                  ? "border-t-2 border-fail"
                  : "border-t-2 border-dashed border-rule"
              }`}
            />
            {i === steps.length - 1 && <span className={`h-4 w-[2px] ${tick(s.state)}`} />}
          </span>
          <span
            className={`block pr-2 text-sm ${
              s.state === "current" ? "font-bold text-ink" : s.state === "failed" ? "font-bold text-fail" : s.state === "done" ? "text-ink" : "text-ink-2"
            }`}
          >
            {s.label}
            <span className="sr-only">
              {s.state === "done" ? " (done)" : s.state === "current" ? " (in progress)" : s.state === "failed" ? " (failed)" : ""}
            </span>
          </span>
        </li>
      ))}
    </ol>
  );
}

function tick(state: Step["state"]) {
  return state === "todo" ? "bg-rule" : state === "failed" ? "bg-fail" : "bg-ink";
}
