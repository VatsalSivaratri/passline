"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createAudit } from "@/lib/api";
import DoorPlan from "@/components/DoorPlan";
import Notice from "@/components/Notice";

const HOW = [
  {
    title: "Describe the building",
    body: "State, type of business, when it was built and whether it was renovated. This decides which rules apply.",
  },
  {
    title: "Record each space",
    body: "Walk through the entrance, restroom, parking and other public areas with your phone, 15 to 40 seconds each.",
  },
  {
    title: "Review the findings",
    body: "Each likely barrier comes with the ADA section, what was seen, a suggested fix and the frames it came from.",
  },
];

export default function Home() {
  const router = useRouter();
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState(false);

  async function start() {
    setStarting(true);
    setError(false);
    try {
      const { audit_id } = await createAudit();
      router.push(`/audit/${audit_id}/questionnaire`);
    } catch {
      setError(true);
      setStarting(false);
    }
  }

  return (
    <>
      <section className="grid items-center gap-10 md:grid-cols-[1.1fr_1fr]">
        <div>
          <h1 className="text-3xl sm:text-4xl">Find the barriers in your building before someone else does.</h1>
          <p className="mt-5 max-w-prose text-lg text-ink-2">
            Record each public space on your phone. Passline checks what it sees against the 2010 ADA
            Standards and tells you what may need fixing, with the rule behind each finding.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <button onClick={start} disabled={starting} className="btn-primary px-7 text-lg">
              {starting ? "Starting audit…" : "Start an audit"}
            </button>
            <span className="text-ink-2">No account needed.</span>
          </div>
          {error && (
            <div className="mt-6 max-w-prose">
              <Notice tone="error" title="Couldn’t reach the Passline server.">
                Check that the backend is running on port 8000, then try again.
              </Notice>
            </div>
          )}
        </div>
        <DoorPlan className="w-full max-w-md justify-self-center md:justify-self-end" />
      </section>

      <section aria-labelledby="how" className="mt-20 border-t-2 border-ink pt-8">
        <h2 id="how" className="text-xl">How an audit works</h2>
        <ol className="mt-6 grid gap-8 sm:grid-cols-3">
          {HOW.map((step, i) => (
            <li key={step.title}>
              <span className="text-3xl font-extrabold text-ink" aria-hidden>
                {i + 1}
              </span>
              <h3 className="mt-2 text-lg">{step.title}</h3>
              <p className="mt-2 text-ink-2">{step.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="limits" className="mt-16 max-w-prose">
        <h2 id="limits" className="text-xl">What it can’t tell you</h2>
        <p className="mt-3 text-ink-2">
          A camera can’t feel how hard a door is to open, test whether a floor is slip resistant, or
          read braille, so Passline doesn’t check those. Treat every finding as a lead to verify with
          a tape measure or a professional, not as a ruling.
        </p>
      </section>
    </>
  );
}
