"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { createModule, uploadVideo } from "@/lib/api";
import { spaceInfo } from "@/lib/spaces";
import Notice from "@/components/Notice";

type Source = "upload" | "record";

// Safari records MP4, Chrome and Firefox record WebM; use whichever this browser supports.
function recorderType(): { mime: string; ext: string } {
  const options = [
    { mime: "video/mp4", ext: "mp4" },
    { mime: "video/webm;codecs=vp9", ext: "webm" },
    { mime: "video/webm", ext: "webm" },
  ];
  for (const o of options) {
    if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(o.mime)) return o;
  }
  return { mime: "", ext: "webm" };
}

export default function CapturePage() {
  const router = useRouter();
  const { id, moduleType } = useParams<{ id: string; moduleType: string }>();
  const info = spaceInfo(moduleType);

  const [source, setSource] = useState<Source>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<{ title: string; body: string } | null>(null);

  const liveRef = useRef<HTMLVideoElement>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // One object URL per selected file, released when it changes.
  useEffect(() => {
    if (!file) { setPreviewUrl(null); return; }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  // Release the camera if the person leaves mid-recording.
  useEffect(() => () => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    if (timerRef.current) clearInterval(timerRef.current);
  }, []);

  async function startRecording() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } }, // rear camera on phones
        audio: false,
      });
      streamRef.current = stream;
      if (liveRef.current) {
        liveRef.current.srcObject = stream;
        await liveRef.current.play();
      }
      const { mime, ext } = recorderType();
      const rec = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      recorderRef.current = rec;
      chunksRef.current = [];
      rec.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      rec.onstop = () => {
        const type = rec.mimeType || mime || "video/webm";
        setFile(new File([new Blob(chunksRef.current, { type })], `recording.${ext}`, { type }));
        stream.getTracks().forEach((t) => t.stop());
      };
      rec.start();
      setRecording(true);
      setElapsed(0);
      timerRef.current = setInterval(() => setElapsed((s) => s + 1), 1000);
    } catch {
      setError({
        title: "The camera didn’t start.",
        body: "Allow camera access for this site in your browser settings, or record with your phone’s camera app and upload the file instead.",
      });
    }
  }

  function stopRecording() {
    recorderRef.current?.stop();
    setRecording(false);
    if (timerRef.current) clearInterval(timerRef.current);
  }

  async function submit() {
    if (!file) return;
    setSubmitting(true);
    setError(null);
    try {
      const { module_id } = await createModule(id, moduleType);
      await uploadVideo(id, module_id, file);
      router.push(`/audit/${id}/processing/${module_id}`);
    } catch {
      setError({
        title: "The upload didn’t finish.",
        body: "Check your connection and that the server is running, then select Upload and analyze again.",
      });
      setSubmitting(false);
    }
  }

  const minutes = `${Math.floor(elapsed / 60)}:${String(elapsed % 60).padStart(2, "0")}`;

  return (
    <div>
      <Link href={`/audit/${id}/modules`} className="link">Back to spaces</Link>
      <h1 className="mt-4 text-2xl">Record: {info.title}</h1>

      <div className="mt-8 grid gap-12 lg:grid-cols-[1fr_1.15fr]">
        <section aria-labelledby="what">
          <h2 id="what" className="text-lg">What to show</h2>
          <p className="mt-2 max-w-prose">{info.instructions}</p>
          <p className="mt-3">
            Aim for <span className="marked font-bold">{info.seconds} seconds</span> of steady footage.
          </p>
          <ul className="mt-5 flex flex-col gap-2">
            {info.tips.map((tip) => (
              <li key={tip} className="flex gap-3">
                <span aria-hidden className="mt-[0.7em] h-[2px] w-4 shrink-0 bg-ink" />
                <span>{tip}</span>
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="video">
          <h2 id="video" className="text-lg">Your video</h2>

          {!file && (
            <fieldset className="mt-3">
              <legend className="sr-only">How to add the video</legend>
              <div className="inline-flex rounded-md border-2 border-ink p-1">
                {(["upload", "record"] as Source[]).map((s) => (
                  <label
                    key={s}
                    className={`relative flex min-h-[44px] cursor-pointer items-center rounded px-4 font-bold has-[:focus-visible]:outline has-[:focus-visible]:outline-[3px]
                      ${source === s ? "bg-ink text-paper" : "text-ink hover:bg-mist"}`}
                  >
                    <input
                      type="radio"
                      name="source"
                      value={s}
                      checked={source === s}
                      onChange={() => setSource(s)}
                      disabled={recording}
                      className="absolute inset-0 cursor-pointer opacity-0"
                    />
                    {s === "upload" ? "Upload a file" : "Record here"}
                  </label>
                ))}
              </div>
            </fieldset>
          )}

          {!file && source === "upload" && (
            <label className="relative mt-5 flex cursor-pointer flex-col items-start gap-3 rounded-md border-2 border-dashed border-ink-2 p-8 hover:border-ink has-[:focus-visible]:border-ink">
              <span className="font-bold">Choose a video file</span>
              <span className="text-sm text-ink-2">From your phone’s camera roll or your computer. MOV, MP4 or WebM.</span>
              <span className="btn-secondary pointer-events-none">Browse files</span>
              <input
                type="file"
                accept="video/*"
                className="absolute inset-0 cursor-pointer opacity-0"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) setFile(f); }}
              />
            </label>
          )}

          {!file && source === "record" && (
            <div className="mt-5 flex flex-col gap-4">
              <div className="relative aspect-video overflow-hidden rounded-md bg-ink">
                <video ref={liveRef} muted playsInline className="h-full w-full object-cover" aria-label="Camera preview" />
                {recording && (
                  <p className="absolute left-3 top-3 bg-mark px-2 py-1 font-bold text-ink" aria-live="off">
                    Recording {minutes}
                  </p>
                )}
                {!recording && (
                  <p className="absolute inset-0 flex items-center justify-center p-6 text-center text-paper">
                    The camera starts when you select Start recording.
                  </p>
                )}
              </div>
              {!recording ? (
                <button onClick={startRecording} className="btn-primary self-start">Start recording</button>
              ) : (
                <button onClick={stopRecording} className="btn-primary self-start">Stop recording</button>
              )}
            </div>
          )}

          {file && previewUrl && (
            <div className="mt-5 flex flex-col gap-4">
              <video src={previewUrl} controls playsInline className="aspect-video w-full rounded-md bg-ink object-contain" aria-label="Preview of your video" />
              <p className="text-sm text-ink-2">{file.name}, {(file.size / 1_000_000).toFixed(1)} MB</p>
              <div className="flex flex-wrap gap-3">
                <button onClick={submit} disabled={submitting} className="btn-primary">
                  {submitting ? "Uploading…" : "Upload and analyze"}
                </button>
                <button onClick={() => setFile(null)} disabled={submitting} className="btn-secondary">
                  Use a different video
                </button>
              </div>
            </div>
          )}

          {error && <div className="mt-5"><Notice tone="error" title={error.title}>{error.body}</Notice></div>}
        </section>
      </div>
    </div>
  );
}
