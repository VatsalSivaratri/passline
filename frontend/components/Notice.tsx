// Inline message with a text label, so meaning never depends on color alone.

export default function Notice({
  tone,
  title,
  children,
}: {
  tone: "error" | "info" | "success";
  title: string;
  children?: React.ReactNode;
}) {
  const styles = {
    error: "border-fail bg-fail-bg",
    info: "border-ink bg-mist",
    success: "border-pass bg-pass-bg",
  }[tone];
  return (
    <div role={tone === "error" ? "alert" : "status"} className={`border-l-4 px-4 py-3 ${styles}`}>
      <p className={`font-bold ${tone === "error" ? "text-fail" : tone === "success" ? "text-pass" : "text-ink"}`}>{title}</p>
      {children && <div className="mt-1 text-ink">{children}</div>}
    </div>
  );
}
