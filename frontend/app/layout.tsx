import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Passline: ADA pre-screening from a phone video",
  description:
    "Record each space in your building and get a list of likely ADA barriers with the rule behind each one.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col">
        <a
          href="#main"
          className="absolute left-4 top-4 z-50 -translate-y-[200%] bg-mark px-4 py-3 font-bold text-ink focus:translate-y-0"
        >
          Skip to content
        </a>
        <header className="border-b-2 border-ink">
          <div className="mx-auto flex max-w-5xl items-center px-5 py-4">
            <Link href="/" className="flex items-center gap-3 text-xl font-extrabold tracking-tight">
              <Wordmark />
              Passline
            </Link>
          </div>
        </header>
        <main id="main" className="mx-auto w-full max-w-5xl flex-1 px-5 py-10 sm:py-14">
          {children}
        </main>
        <footer className="border-t border-rule">
          <div className="mx-auto flex max-w-5xl flex-col gap-2 px-5 py-6 text-sm text-ink-2 sm:flex-row sm:items-end sm:justify-between sm:gap-8">
            <p className="max-w-prose">
              Passline is a pre-screening tool. It is not a certified inspection, a compliance
              determination or legal advice.
            </p>
            <p className="shrink-0">Frontend designed with Claude by Anthropic.</p>
          </div>
        </footer>
      </body>
    </html>
  );
}

// A short dimension line: the mark that runs through the whole interface.
function Wordmark() {
  return (
    <svg width="30" height="16" viewBox="0 0 30 16" aria-hidden>
      <line x1="2" y1="2" x2="2" y2="14" stroke="#14243B" strokeWidth="2.5" />
      <line x1="28" y1="2" x2="28" y2="14" stroke="#14243B" strokeWidth="2.5" />
      <rect x="2" y="5.5" width="26" height="5" fill="#FFD23F" />
      <line x1="2" y1="8" x2="28" y2="8" stroke="#14243B" strokeWidth="2" />
    </svg>
  );
}
