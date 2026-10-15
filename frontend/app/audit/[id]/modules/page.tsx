"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { getAudit, triggerReport } from "@/lib/api";
import { SPACE_GROUPS, spaceInfo } from "@/lib/spaces";
import AuditSteps from "@/components/AuditSteps";
import Notice from "@/components/Notice";

const PROCESSING = new Set(["uploading", "extracting_frames", "classifying", "analyzing", "checking_compliance"]);

export default function SpacesPage() {
  const router = useRouter();
  const { id } = useParams<{ id: string }>();
  const [audit, setAudit] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [reportError, setReportError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const data = await getAudit(id);
        if (!cancelled) { setAudit(data); setLoadError(false); }
      } catch {
        if (!cancelled) setLoadError(true);
      }
      if (!cancelled) setLoading(false);
    }
    poll();
    const t = setInterval(poll, 4000);
    return () => { cancelled = true; clearInterval(t); };
  }, [id]);

  const suggested: string[] = audit?.applicable_modules?.length ? audit.applicable_modules : ["entrance", "restroom"];
  const byType: Record<string, any> = {};
  for (const m of audit?.modules ?? []) byType[m.module_type] = m;

  // Spaces the backend classified itself ("auto" uploads) may not be in the suggested list.
  const extra = Object.keys(byType).filter((k) => !suggested.includes(k));
  const groups = SPACE_GROUPS
    .map((g) => ({ ...g, keys: g.keys.filter((k) => suggested.includes(k)) }))
    .filter((g) => g.keys.length > 0);
  const seen = new Set<string>();
  const dedupedGroups = groups.map((g) => ({ ...g, keys: g.keys.filter((k) => !seen.has(k) && seen.add(k)) })).filter((g) => g.keys.length);
  if (extra.length) dedupedGroups.push({ label: "Other recorded spaces", keys: extra });

  const all = dedupedGroups.flatMap((g) => g.keys);
  const done = all.filter((k) => byType[k]?.status === "complete").length;

  async function generate() {
    setGenerating(true);
    setReportError(false);
    try {
      await triggerReport(id);
      router.push(`/audit/${id}/report`);
    } catch {
      setReportError(true);
      setGenerating(false);
    }
  }

  return (
    <div>
      <AuditSteps current={1} />
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div className="max-w-prose">
          <h1 className="text-2xl">Record each space</h1>
          <p className="mt-2 text-ink-2">
            Start with entrances and the route to them; those matter most. You can generate the report
            once one space is done and add more later.
          </p>
        </div>
        <div className="flex flex-col items-start gap-2 sm:items-end">
          <p aria-live="polite" className="font-bold">
            {loading ? "Loading…" : `${done} of ${all.length} spaces done`}
          </p>
          <button onClick={generate} disabled={done === 0 || generating} className="btn-primary">
            {generating ? "Starting report…" : "Generate report"}
          </button>
        </div>
      </div>

      {loadError && (
        <div className="mt-6"><Notice tone="error" title="Couldn’t load this audit.">The server didn’t respond. This page retries every few seconds.</Notice></div>
      )}
      {reportError && (
        <div className="mt-6"><Notice tone="error" title="The report didn’t start.">At least one space must finish processing first. If one has, try again.</Notice></div>
      )}

      <div className="mt-10 flex flex-col gap-10">
        {dedupedGroups.map((g) => (
          <section key={g.label} aria-labelledby={`g-${g.label}`}>
            <h2 id={`g-${g.label}`} className="border-b-2 border-ink pb-2 text-lg">{g.label}</h2>
            <ul>
              {g.keys.map((key) => (
                <SpaceRow key={key} auditId={id} spaceKey={key} module={byType[key]} />
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}

function SpaceRow({ auditId, spaceKey, module }: { auditId: string; spaceKey: string; module: any }) {
  const info = spaceInfo(spaceKey);
  const status: string = module?.status ?? "created";
  const count: number = module?.violations?.length ?? 0;

  let statusText: React.ReactNode = <span className="text-ink-2">Not recorded</span>;
  let action = { label: "Record", href: `/audit/${auditId}/capture/${spaceKey}`, primary: true };

  if (PROCESSING.has(status)) {
    statusText = <span className="marked font-bold">Processing</span>;
    action = { label: "View progress", href: `/audit/${auditId}/processing/${module.module_id}`, primary: false };
  } else if (status === "complete") {
    statusText = count > 0
      ? <span className="font-bold text-fail">{count} possible {count === 1 ? "violation" : "violations"}</span>
      : <span className="font-bold text-pass">No violations found</span>;
    action = { label: "Record again", href: `/audit/${auditId}/capture/${spaceKey}`, primary: false };
  } else if (status === "error") {
    statusText = <span className="font-bold text-fail">Processing failed</span>;
    action = { label: "Record again", href: `/audit/${auditId}/capture/${spaceKey}`, primary: true };
  }

  return (
    <li className="grid gap-x-6 gap-y-2 border-b border-rule py-4 sm:grid-cols-[1fr_auto_auto] sm:items-center">
      <div>
        <h3 className="text-base font-bold">{module?.room_name || info.title}</h3>
        {info.checks && <p className="text-sm text-ink-2">Checks: {info.checks.toLowerCase()}</p>}
      </div>
      <p className="text-sm sm:text-right">{statusText}</p>
      <Link
        href={action.href}
        className={`${action.primary ? "btn-primary" : "btn-secondary"} min-w-[9rem]`}
        aria-label={`${action.label}: ${module?.room_name || info.title}`}
      >
        {action.label}
      </Link>
    </li>
  );
}
