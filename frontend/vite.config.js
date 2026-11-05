// =====================================================================
// vite.config.js  —  settings for Vite, the tool that runs and builds
// the React app.
// =====================================================================
// Plugins add extra abilities to Vite:
//   react()        -> understands React's JSX syntax (<div> inside JavaScript)
//   tailwindcss()  -> turns Tailwind class names (e.g. "bg-white p-4") into CSS
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // The development address will be http://localhost:5173
    // (this must match FRONTEND_URLS in backend/.env, or CORS will block it).
    port: 5173,
  },
})
