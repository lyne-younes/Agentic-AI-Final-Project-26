import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    strictPort: true, // must match APP_URL and the redirect URI registered with Google
    proxy: {
      // Same-origin API (mirrors nginx.conf in Docker) so the session cookie is first-party.
      "/api": {
        target: "http://localhost:8000",
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
