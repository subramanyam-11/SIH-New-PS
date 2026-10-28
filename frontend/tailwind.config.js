/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        aicte: {
          navy: "#0f2b5c",
          dark: "#0a1d3f",
          light: "#1e3a8a",
          accent: "#d97706",
          slate: "#f8fafc",
          muted: "#64748b"
        }
      }
    },
  },
  plugins: [],
}
