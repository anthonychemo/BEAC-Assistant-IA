/**
 * Serveur Express minimal — uniquement pour la production (serve du build Vite).
 * En développement, utiliser `vite` directement (proxy configuré dans vite.config.ts).
 */
import express from "express";
import path from "path";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const PORT = process.env.PORT ? Number(process.env.PORT) : 3000;

const distPath = path.join(process.cwd(), "dist");
app.use(express.static(distPath));
app.get("*", (_req, res) => {
  res.sendFile(path.join(distPath, "index.html"));
});

app.listen(PORT, "0.0.0.0", () => {
  console.log(`[BEAC PORTAL] Frontend served on http://localhost:${PORT}`);
  console.log(`[BEAC PORTAL] Backend API expected on http://localhost:8000`);
});
