import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// ATHAR runs on its own ports (web 5710, API 8710) so it never collides with other local projects.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5710,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:8710" },
  },
});
