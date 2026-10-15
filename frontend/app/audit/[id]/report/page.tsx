"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { getAudit, getReport } from "@/lib/api";
import { spaceInfo } from "@/lib/spaces";
import AuditSteps from "@/components/AuditSteps";
import Notice from "@/components/Notice";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const SEVERITY: Record<string, { label: string; cls: string }> = {
  critical: { label: "Critical", cls: "bg-fail text-paper border-fail" },
  high: { label: "High", cls: "text-fail border-fail" },
  medium: { label: "Medium", cls: "text-ink border-ink" },
  low: { label: "Low", cls: "text-ink-2 border-rule" },
};

const FACILITY_LABEL: Record<string, string> = {
  restaurant: "Restaurant", retail: "Retail store", office: "Office", medical: "Medical facility",
  hotel: "Hotel", education: "School", assembly: "Venue", other: "Building",
};
const AGE_LABEL: Record<string, string> = {
  "pre-1992": "built before 1992", "1992-2012": "built between 1992 and 2012", "post-2012": "built after 2012",
};

const usd = (n: number) => `$${Math.round(n).toLocaleString("en-US")}`;

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<any>(null);
  const [audit, setAudit] = useState<any>(null);
  const [waiting, setWaiting] = useState(true);
  const [frame, setFrame] = useState<{ src: string; alt: string } | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    async function load() {
      try {
        const [r, a] = await Promise.all([getReport(id), getAudit(id)]);
        if (cancelled) return;
        setReport(r); setAudit(a); setWaiting(false);
        return; // loaded: stop polling
      } catch {
        // 404 until generation finishes
      }
      if (!cancelled) timer = setTimeout(load, 4000);
    }
    load();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [id]);

  if (waiting) {
    return (
      <div className="max-w-prose">
        <AuditSteps current={2} />
        <h1 className="text-2xl">Writing the report</h1>
        <p className="mt-3" aria-live="polite">
          Passline is writing a description and suggested fix for each finding. This page updates
          when it’s ready, usually within a minute.
        </p>
      </div>
    );
  }

  const facility = audit?.facility ?? {};
  const modulesById: Record<string, any> = Object.fromEntries((audit?.modules ?? []).map((m: any) => [m.module_id, m]));
  const groups: { module_id: string; module_type: string; room_name?: string; violations: any[] }[] =
    report.module_violations?.length
      ? report.module_violations
      : Object.values(
          (report.violations ?? []).reduce((acc: any, v: any) => {
            (acc[v.module_id] ??= { module_id: v.module_id, module_type: v.module_type, violations: [] }).violations.push(v);
            return acc;
          }, {}),
        );

  const total: number = report.total_violations ?? 0;
  const critical: number = report.critical_violations ?? 0;
  const spaces: number = report.modules_audited ?? groups.length;
  const cost = report.estimated_remediation_total ?? { low: 0, high: 0 };
  const generated = report.generated_at ? new Date(report.generated_at) : new Date();

  return (
    <div>
      <AuditSteps current={2} />

      <header className="flex flex-wrap items-end justify-between gap-6 border-b-2 border-ink pb-8">
        <div className="max-w-prose">
          <h1 className="text-3xl">Pre-screening report</h1>
          <p className="mt-3 text-ink-2">
            {FACILITY_LABEL[facility.facility_type] ?? "Building"}
            {facility.state ? ` in ${facility.state}` : ""}
            {AGE_LABEL[facility.building_age] ? `, ${AGE_LABEL[facility.building_age]}` : ""}.
            {" "}Generated {generated.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}.
          </p>
          <p className="mt-5 text-xl font-bold">
            {total === 0
              ? `No possible violations in ${spaces} ${spaces === 1 ? "space" : "spaces"}.`
              : `${total} possible ${total === 1 ? "violation" : "violations"} in ${spaces} ${spaces === 1 ? "space" : "spaces"}${critical ? `, ${critical} marked critical` : ""}.`}
          </p>
          {total > 0 && (
            <p className="mt-1 text-ink-2">
              Rough cost to fix: {usd(cost.low)} to {usd(cost.high)}. These are broad placeholder ranges, not quotes.
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-3">
          {report.pdf_url && (
            <a href={`${API_BASE}${report.pdf_url}`} className="btn-primary" download>Download PDF</a>
          )}
          <Link href={`/audit/${id}/modules`} className="btn-secondary">Add more spaces</Link>
        </div>
      </header>

      <div className="mt-8 max-w-prose">
        <Notice tone="info" title="How to read this">
          Each finding is what Passline’s vision model saw in your video, matched to a section of the
          2010 ADA Standards. Measure or have a professional confirm each one before acting on it.
          Older buildings may be covered by different rules than the ones cited.
        </Notice>
      </div>

      {groups.length === 0 && (
        <div className="mt-8 max-w-prose">
          <Notice tone="success" title="No possible violations found">
            That isn’t proof the building complies. Passline only checks what the camera captured, and
            some requirements, like door opening force, can’t be judged from video.
          </Notice>
        </div>
      )}

      {groups.map((g) => {
        const mod = modulesById[g.module_id] ?? {};
        const title = g.room_name || mod.room_name || spaceInfo(g.module_type).title;
        const annotated: string[] = mod.annotated_frames ?? [];
        return (
          <section key={g.module_id} aria-labelledby={`s-${g.module_id}`} className="mt-14">
            <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-rule pb-2">
              <h2 id={`s-${g.module_id}`} className="text-xl">{title}</h2>
              <p className="text-ink-2">
                {g.violations.length} possible {g.violations.length === 1 ? "violation" : "violations"}
              </p>
            </div>

            {mod.calibrated === false && g.violations.length > 0 && (
              <p className="mt-3 max-w-prose text-sm text-ink-2">
                No reference object was found in this video, so any size judgments are visual estimates.
                Recording again with a sheet of printer paper in view gives Passline a known scale.
              </p>
            )}

            {annotated.length > 0 && (
              <div className="mt-5">
                <h3 className="text-base font-bold">Evidence frames</h3>
                <ul className="mt-2 flex gap-2 overflow-x-auto pb-2">
                  {annotated.slice(0, 8).map((f, i) => (
                    <li key={f} className="shrink-0">
                      <button
                        onClick={() => setFrame({ src: `${API_BASE}/frames/${f}`, alt: `${title}, frame ${i + 1} with detected features outlined` })}
                        className="block overflow-hidden rounded-md border-2 border-rule hover:border-ink"
                        aria-label={`Enlarge frame ${i + 1} of ${title}`}
                      >
                        <img src={`${API_BASE}/frames/${f}`} alt="" className="h-24 w-auto" />
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <ol className="mt-4">
              {g.violations.map((v: any) => <Finding key={v.violation_id} v={v} />)}
            </ol>
          </section>
        );
      })}

      <FrameDialog frame={frame} onClose={() => setFrame(null)} />
    </div>
  );
}

function Finding({ v }: { v: any }) {
  const sev = SEVERITY[v.severity] ?? SEVERITY.low;
  const section = String(v.code ?? "").replace(/^ADA\s*/, "");
  return (
    <li className="border-b border-rule py-6">
      <article className="grid gap-x-8 gap-y-3 md:grid-cols-[11rem_1fr]">
        <div className="flex flex-row flex-wrap items-center gap-3 md:flex-col md:items-start">
          <span className={`inline-block rounded border-2 px-2 py-0.5 text-sm font-bold ${sev.cls}`}>
            {sev.label}<span className="sr-only"> severity</span>
          </span>
          {section && <span className="text-sm font-bold">{section}</span>}
        </div>
        <div className="max-w-prose">
          <h3 className="text-lg">{v.element}</h3>
          <p className="mt-1"><span className="font-bold">Seen: </span>{v.finding}</p>
          {v.description && v.description !== v.finding && <p className="mt-2 text-ink-2">{v.description}</p>}
          {v.remediation && <p className="mt-2"><span className="font-bold">Suggested fix: </span>{v.remediation}</p>}
          {v.remediation_cost && (
            <p className="mt-2 text-sm text-ink-2">
              Rough cost: {usd(v.remediation_cost.low)} to {usd(v.remediation_cost.high)}
            </p>
          )}
        </div>
      </article>
    </li>
  );
}

// Native <dialog>: focus moves in, Escape closes, focus returns to the thumbnail.
function FrameDialog({ frame, onClose }: { frame: { src: string; alt: string } | null; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (frame && !d.open) d.showModal();
    if (!frame && d.open) d.close();
  }, [frame]);
  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onClick={(e) => { if (e.target === ref.current) onClose(); }}
      className="max-h-[92vh] max-w-[92vw] rounded-md bg-paper p-3 backdrop:bg-ink/80"
      aria-label={frame?.alt ?? "Frame"}
    >
      {frame && (
        <div className="flex flex-col gap-3">
          <img src={frame.src} alt={frame.alt} className="max-h-[78vh] w-auto" />
          <button onClick={onClose} className="btn-secondary self-end" autoFocus>Close</button>
        </div>
      )}
    </dialog>
  );
}
