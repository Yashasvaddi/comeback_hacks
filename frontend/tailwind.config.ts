import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Warm near-black base (control room at dusk)
        base: "#0a0b0d",
        surface: "#131419",
        raised: "#191b21",
        line: "#262830",
        // Text — warm paper, not blue-white
        paper: "#eae8e3",
        muted: "#9a968d",
        faint: "#6b675f",
        // Single confident signal accent — ember
        ember: "#e8833a",
        "ember-dim": "#b8632a",
        // Cool secondary for data variety (petrol)
        petrol: "#4f9db0",
        // Muted semantics (no neon)
        ok: "#6fa368",
        warn: "#d9a441",
        danger: "#c9564c",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        panel: "0 1px 0 rgba(255,255,255,0.04) inset, 0 8px 24px -12px rgba(0,0,0,0.7)",
        raised: "0 12px 32px -16px rgba(0,0,0,0.8)",
        ember: "0 6px 20px -8px rgba(232,131,58,0.45)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "scan": {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(100%)" },
        },
        "blink": {
          "0%,100%": { opacity: "1" },
          "50%": { opacity: "0.35" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.5s ease-out both",
        scan: "scan 1.4s ease-in-out infinite",
        blink: "blink 1.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
