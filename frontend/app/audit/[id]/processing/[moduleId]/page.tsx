"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { getModuleStatus } from "@/lib/api";
import { spaceInfo } from "@/lib/spaces";
import DimensionSteps from "@/components/DimensionSteps";
import Notice from "@/components/Notice";

// Backend statuses in pipeline order, grouped into the stages a person cares about.
const STAGES: { label: string; statuses: string[] }[] = [
  { label: "Pull frames", statuses: ["uploading", "extracting_frames", "classifying"] },
  { label: "Find features", statuses: ["analyzing"] },
  { label: "Check rules", statuses: ["checking_compliance"] },
  { label: "Done", statuses: ["complete"] },
];

function stageIndex(status: string) {
  const i = STAGES.findIndex((s) => s.statuses.includes(status));
  return i < 0 ? 0 : i;
}

export default function ProcessingPage() {
  const { id, moduleId } = useParams<{ id: string; moduleId: string }>();
  const [data, setData] = useState<{
    status: string; progress: number; module_type: string | null;
    violations_found: number | null; error_message: string | null;
  } | null>(null);
  const [unreachable, setUnreachable] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const d = await getModuleStatus(id, moduleId);
        if (cancelled) return;
        setData(d);
        setUnreachable(false);
        if (d.status === "complete" || d.status === "error") return; // stop polling
      } catch {
        if (!cancelled) setUnreachable(true);
      }
      timer = setTimeout(poll, 2500);
    }
    poll();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [id, moduleId]);

  const status = data?.status ?? "extracting_frames";
  const failed = status === "error";
  const complete = status === "complete";
  const current = stageIndex(status);
  const title = spaceInfo(data?.module_type).title;
  const n = data?.violations_found ?? 0;

  const steps = STAGES.map((s, i) => ({
    label: s.label,
    state: (complete || i < current ? "done" : i === current ? "current" : "todo") as "done" | "current" | "todo",
  }));

  return (
    <div className="max-w-prose">
      <Link href={`/audit/${id}/modules`} className="link">Back to spaces</Link>
      <h1 className="mt-4 text-2xl">
        {failed ? `${title}: processing failed` : complete ? `${title}: done` : `Analyzing ${title.toLowerCase()}`}
      </h1>

      {/* The backend doesn't report which stage failed, so on failure the track is hidden
          rather than guessing; the error message names the cause. */}
      {!failed && (
        <div className="mt-10">
          <DimensionSteps label="Processing stages" steps={steps} />
        </div>
      )}

      <div className="mt-10" aria-live="polite">
        {!failed && !complete && (
          <p>
            {STAGES[current].label}. This usually takes under two minutes; you can leave this page and
            check back from the space list.
            {data && <span className="text-ink-2"> ({data.progress}% done)</span>}
          </p>
        )}

        {complete && (
          <div className="flex flex-col items-start gap-5">
            <Notice tone={n > 0 ? "info" : "success"} title={n > 0 ? `${n} possible ${n === 1 ? "violation" : "violations"} found` : "No violations found"}>
              {n > 0
                ? "They’ll appear in the report with the ADA section and the frames they came from."
                : "Nothing in this video matched a rule. That isn’t proof the space complies; Passline only checks what the camera can see."}
            </Notice>
            <Link href={`/audit/${id}/modules`} className="btn-primary">Back to spaces</Link>
          </div>
        )}

        {failed && (
          <div className="flex flex-col items-start gap-5">
            <Notice tone="error" title="This video couldn’t be analyzed.">
              {data?.error_message ?? "The server stopped before finishing."}
            </Notice>
            <div className="flex flex-wrap gap-3">
              <Link href={`/audit/${id}/capture/${data?.module_type ?? "auto"}`} className="btn-primary">Record again</Link>
              <Link href={`/audit/${id}/modules`} className="btn-secondary">Back to spaces</Link>
            </div>
          </div>
        )}

        {unreachable && (
          <div className="mt-5">
            <Notice tone="error" title="Lost contact with the server.">This page keeps retrying. Processing continues on the server.</Notice>
          </div>
        )}
      </div>
    </div>
  );
}
