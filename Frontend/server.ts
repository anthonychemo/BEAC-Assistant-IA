/**
 * Serveur Express minimal — uniquement pour la production (serve du build Vite).
 * En développement, utiliser `vite` directement (proxy configuré dans vite.config.ts).
 *
 * Relaie aussi /api/* vers le backend FastAPI (BACKEND_URL), pour que les appels
 * du frontend fonctionnent en production sans reverse-proxy externe supplémentaire.
 */
import express from "express";
import path from "path";
import dotenv from "dotenv";
import http from "http";
import { URL } from "url";

dotenv.config();

const app = express();
const PORT = process.env.PORT ? Number(process.env.PORT) : 3000;
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

// Relais /api/* -> backend FastAPI, en reecrivant le prefixe comme en dev
// (voir vite.config.ts pour la table de correspondance des routes).
const API_REWRITES: [RegExp, string][] = [
  [/^\/api\/chat\/stream/, "/query/stream"],
  [/^\/api\/chat/, "/query"],
  [/^\/api\/cache\/clear/, "/cache/clear"],
  [/^\/api\/documents/, "/documents"],
  [/^\/api\/metadata/, "/metadata"],
  [/^\/api\/health/, "/health"],
  [/^\/api\/files/, "/images"],
  [/^\/api\/pipeline/, "/pipeline"],
  [/^\/api\/admin\/stats/, "/admin/stats"],
];

app.use("/api", (req, res) => {
  let targetPath = req.originalUrl;
  for (const [pattern, replacement] of API_REWRITES) {
    if (pattern.test(targetPath)) {
      targetPath = targetPath.replace(pattern, replacement);
      break;
    }
  }

  const target = new URL(targetPath, BACKEND_URL);
  const proxyReq = http.request(
    target,
    { method: req.method, headers: { ...req.headers, host: target.host } },
    (proxyRes) => {
      res.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
      proxyRes.pipe(res);
    },
  );
  proxyReq.on("error", (err) => {
    console.error("[BEAC PORTAL] Erreur proxy backend:", err.message);
    res.status(502).json({ error: "Backend indisponible" });
  });
  req.pipe(proxyReq);
});

const distPath = path.join(process.cwd(), "dist");
app.use(express.static(distPath));
app.get("*", (_req, res) => {
  res.sendFile(path.join(distPath, "index.html"));
});

app.listen(PORT, "0.0.0.0", () => {
  console.log(`[BEAC PORTAL] Frontend served on http://localhost:${PORT}`);
  console.log(`[BEAC PORTAL] Relaie /api/* vers le backend : ${BACKEND_URL}`);
});
