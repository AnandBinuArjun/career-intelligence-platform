import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        graphite: "#0B0F19",
        panel: "#121A2A",
        accent: "#5B8CFF",
        "accent-soft": "#172B50"
      }
    }
  },
  plugins: []
};
export default config;
