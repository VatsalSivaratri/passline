"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { submitQuestionnaire } from "@/lib/api";
import AuditSteps from "@/components/AuditSteps";
import Notice from "@/components/Notice";

const US_STATES = [
  "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY",
  "LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND",
  "OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY",
];

const FACILITY_TYPES = [
  { value: "restaurant", label: "Restaurant or food service" },
  { value: "retail", label: "Retail store" },
  { value: "office", label: "Office" },
  { value: "medical", label: "Medical or healthcare" },
  { value: "hotel", label: "Hotel or lodging" },
  { value: "education", label: "School or university" },
  { value: "assembly", label: "Venue or entertainment" },
  { value: "other", label: "Something else" },
];

const BUILDING_AGES = [
  { value: "pre-1992", label: "Before 1992", hint: "Built before the ADA’s design rules took effect" },
  { value: "1992-2012", label: "1992 to 2012", hint: "Built under the 1991 ADA Standards" },
  { value: "post-2012", label: "After 2012", hint: "Built under the current 2010 ADA Standards" },
];

export default function QuestionnairePage() {
  const router = useRouter();
  const { id } = useParams<{ id: string }>();

  const [state, setState] = useState("IN");
  const [facilityType, setFacilityType] = useState("restaurant");
  const [buildingAge, setBuildingAge] = useState("pre-1992");
  const [renovated, setRenovated] = useState(false);
  const [renovationCost, setRenovationCost] = useState("");
  const [parkingSpaces, setParkingSpaces] = useState("0");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(false);
    try {
      await submitQuestionnaire(id, {
        state,
        facility_type: facilityType,
        building_age: buildingAge,
        recent_renovation: renovated,
        renovation_cost: renovated && renovationCost ? parseFloat(renovationCost) : null,
        parking_spaces: parseInt(parkingSpaces, 10) || 0,
      });
      router.push(`/audit/${id}/modules`);
    } catch {
      setError(true);
      setSaving(false);
    }
  }

  return (
    <div className="max-w-prose">
      <AuditSteps current={0} />
      <h1 className="text-2xl">About the building</h1>
      <p className="mt-2 text-ink-2">These answers decide which spaces to record and which rules apply.</p>

      <form onSubmit={handleSubmit} className="mt-10 flex flex-col gap-10">
        <div>
          <label htmlFor="state" className="block font-bold">State</label>
          <select id="state" value={state} onChange={(e) => setState(e.target.value)} className="field mt-2 max-w-[10rem]">
            {US_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        <fieldset>
          <legend className="font-bold">What kind of business uses the building?</legend>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {FACILITY_TYPES.map((f) => (
              <Choice key={f.value} name="facility" value={f.value} checked={facilityType === f.value} onChange={setFacilityType}>
                {f.label}
              </Choice>
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend className="font-bold">When was it built?</legend>
          <div className="mt-3 flex flex-col gap-2">
            {BUILDING_AGES.map((a) => (
              <Choice key={a.value} name="age" value={a.value} checked={buildingAge === a.value} onChange={setBuildingAge}>
                {a.label}
                <span className="block text-sm font-normal text-ink-2">{a.hint}</span>
              </Choice>
            ))}
          </div>
        </fieldset>

        <div>
          <label className="flex min-h-[48px] cursor-pointer items-center gap-3">
            <input
              type="checkbox"
              checked={renovated}
              onChange={(e) => setRenovated(e.target.checked)}
              className="h-6 w-6 accent-ink"
            />
            <span className="font-bold">Renovated in the last 3 years</span>
          </label>
          {renovated && (
            <div className="mt-3 pl-9">
              <label htmlFor="cost" className="block">Approximate renovation cost, in dollars</label>
              <input
                id="cost"
                type="number"
                inputMode="numeric"
                min="0"
                value={renovationCost}
                onChange={(e) => setRenovationCost(e.target.value)}
                className="field mt-2 max-w-[14rem]"
              />
            </div>
          )}
        </div>

        <div>
          <label htmlFor="parking" className="block font-bold">Parking spaces</label>
          <p id="parking-hint" className="text-sm text-ink-2">Enter 0 if the building has no parking lot.</p>
          <input
            id="parking"
            aria-describedby="parking-hint"
            type="number"
            inputMode="numeric"
            min="0"
            value={parkingSpaces}
            onChange={(e) => setParkingSpaces(e.target.value)}
            className="field mt-2 max-w-[10rem]"
          />
        </div>

        {error && (
          <Notice tone="error" title="Your answers weren’t saved.">
            The server didn’t respond. Check that it’s running, then select Continue again.
          </Notice>
        )}

        <div>
          <button type="submit" disabled={saving} className="btn-primary">
            {saving ? "Saving…" : "Continue"}
          </button>
        </div>
      </form>
    </div>
  );
}

function Choice({
  name, value, checked, onChange, children,
}: {
  name: string; value: string; checked: boolean; onChange: (v: string) => void; children: React.ReactNode;
}) {
  return (
    <label
      className={`flex min-h-[48px] cursor-pointer items-start gap-3 rounded-md border-2 px-3 py-3 font-bold
        ${checked ? "border-ink bg-mist" : "border-rule hover:border-ink-2"}`}
    >
      <input
        type="radio"
        name={name}
        value={value}
        checked={checked}
        onChange={() => onChange(value)}
        className="mt-1 h-5 w-5 shrink-0 accent-ink"
      />
      <span>{children}</span>
    </label>
  );
}
