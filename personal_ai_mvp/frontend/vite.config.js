import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, resolve(__dirname, ".."), "");
  const devHost = env.PERSONAL_AI_UI_DEV_HOST || "127.0.0.1";
  const devPort = Number.parseInt(env.PERSONAL_AI_UI_DEV_PORT || "5173", 10);
  const apiTarget = env.PERSONAL_AI_UI_DEV_API_TARGET || "http://127.0.0.1:8765";

  return {
    envDir: resolve(__dirname, ".."),
    plugins: [react()],
    server: {
      host: devHost,
      port: Number.isFinite(devPort) ? devPort : 5173,
      proxy: {
        "/api": {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  };
});
