import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import svgr from "vite-plugin-svgr";
import path from "path";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), svgr()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        // 필요시 아래 옵션 추가
        // rewrite: (path) => path.replace(/^\/api/, "/api"),
      },
    },
  },
  resolve: {
    alias: {
      "@styles/": path.resolve(__dirname, "assets/styles/"),
      "@icons": path.resolve(__dirname, "src/assets/icons"),
      // ...다른 alias
    },
  },
});
