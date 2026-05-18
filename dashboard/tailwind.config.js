/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx}", "./components/**/*.{js,jsx}"],
  theme: {
    extend: {
      boxShadow: {
        dash: "0 18px 45px rgba(15, 23, 42, 0.10)",
        insetPanel: "inset 0 1px 0 rgba(255, 255, 255, 0.92), inset 0 -18px 35px rgba(14, 165, 233, 0.06)",
      },
      colors: {
        cockpit: {
          ink: "#0f172a",
          line: "#dbe5ef",
          soft: "#f4f8fb",
          teal: "#0f766e",
          sky: "#0ea5e9",
          amber: "#f59e0b",
        },
      },
    },
  },
  plugins: [],
};
