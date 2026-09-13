import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { VitePWA } from "vite-plugin-pwa";

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.ico", "apple-touch-icon.png"],
      manifest: {
        name: "TerraSense NER",
        short_name: "TerraSense",
        description: "AI-powered landslide early warning and monitoring platform",
        theme_color: "#0f172a",
        background_color: "#0f172a",
        display: "standalone",
        icons: [
          {
            src: "icon-192.png",
            sizes: "192x192",
            type: "image/png"
          },
          {
            src: "icon-512.png",
            sizes: "512x512",
            type: "image/png"
          }
        ]
      }
    })
  ],
  resolve: {
    dedupe: ["react", "react-dom"],
  },
  // MapLibre owns a dedicated worker module that Vite's dev pre-bundler cannot
  // safely relocate. The renderer remains code-split by MapSurface.
  optimizeDeps: {
    exclude: ["maplibre-gl"],
  },
});
