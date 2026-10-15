import DimensionSteps from "./DimensionSteps";

const STEPS = ["Facility", "Spaces", "Report"];

export default function AuditSteps({ current }: { current: 0 | 1 | 2 }) {
  return (
    <div className="mb-10">
      <DimensionSteps
        label="Audit progress"
        steps={STEPS.map((label, i) => ({
          label,
          state: i < current ? "done" : i === current ? "current" : "todo",
        }))}
      />
    </div>
  );
}
