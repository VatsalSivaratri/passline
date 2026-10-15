import type { Config } from "tailwindcss";

// Passline tokens. Every text/background pair used in the app meets WCAG AA;
// `mark` is a fill only (ink text on it), never a text color.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#FFFFFF",
        mist: "#F1F4F7",     // quiet surface
        rule: "#D5DBE2",     // borders and dimension lines
        ink: "#14243B",      // plan ink: body text, primary actions (15.4:1 on paper)
        "ink-2": "#4E5B6B",  // secondary text (6.9:1 on paper)
        mark: "#FFD23F",     // detectable-warning yellow, used as a highlighter fill
        fail: "#A8231A",     // violations (7.0:1 on paper)
        "fail-bg": "#FBEAE8",
        pass: "#1C6B3A",     // passes, completion (6.4:1 on paper)
        "pass-bg": "#E6F2EA",
      },
      fontFamily: {
        sans: ['"Atkinson Hyperlegible Next"', "system-ui", "sans-serif"],
      },
      fontSize: {
        // scale on a 1.25 ratio from an 18px base
        sm: ["0.889rem", { lineHeight: "1.45" }],
        base: ["1rem", { lineHeight: "1.55" }],
        lg: ["1.25rem", { lineHeight: "1.4" }],
        xl: ["1.563rem", { lineHeight: "1.25" }],
        "2xl": ["1.953rem", { lineHeight: "1.2" }],
        "3xl": ["2.441rem", { lineHeight: "1.1" }],
        "4xl": ["3.052rem", { lineHeight: "1.05" }],
      },
      maxWidth: { prose: "38rem" },
    },
  },
  plugins: [],
};
export default config;
