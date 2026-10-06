import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "VITE_");
  const apiTarget = env.VITE_API_BASE_URL || "http://localhost:8000";

  return {
    plugins: [react()],
    server: {
      proxy: {
        "/v1": { target: apiTarget, changeOrigin: true },
        "/healthz": { target: apiTarget, changeOrigin: true },
      },
    },
  };
});
