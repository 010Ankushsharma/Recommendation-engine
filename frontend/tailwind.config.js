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
        purple: {
          50: '#f7f3ff',
          100: '#eee7ff',
          200: '#e0d4ff',
          300: '#c0b4fc',
          400: '#a492fb',
          500: '#8970f7',
          600: '#6f51f6',
          700: '#5a3ee1',
          800: '#4830c7',
          900: '#3a25a5',
        }
      }
    },
  },
  plugins: [],
}
