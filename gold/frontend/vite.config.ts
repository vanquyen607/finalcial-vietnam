import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy API/WS về backend để dev chạy song song không cần build lại.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", ws: true },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    chunkSizeWarningLimit: 700,
  },
});
