/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        legalBlue: '#002b47',
        legalGold: '#a87a4d',
      }
    },
  },
  plugins: [],
}