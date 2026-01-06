// server/server.js
const express = require("express");
const cors = require("cors");
const dotenv = require("dotenv");
const { spawn } = require("child_process");
const path = require("path");

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5050;

app.use(cors());
app.use(express.json({ limit: "1mb" }));

app.get("/", (_req, res) => res.send("Backend Grammalecte (Python) OK"));

app.post("/correct", (req, res) => {
  const text = req.body?.text;

  if (!text || typeof text !== "string" || !text.trim()) {
    return res.status(400).json({ error: "Texte vide ou invalide." });
  }

  const bridgePath = path.join(__dirname, "gl_bridge.py");

  const py = spawn("python", [bridgePath], {
    cwd: __dirname,
    stdio: ["pipe", "pipe", "pipe"],
    env: {
      ...process.env,
      PYTHONIOENCODING: "utf-8",
      PYTHONUTF8: "1",
    },
  });

  // IMPORTANT: forcer encodage côté Node
  py.stdout.setEncoding("utf8");
  py.stderr.setEncoding("utf8");

  let stdout = "";
  let stderr = "";

  py.stdout.on("data", (data) => (stdout += data));
  py.stderr.on("data", (data) => (stderr += data));

  py.on("close", (code) => {
    if (code !== 0) {
      return res.status(500).json({
        error: "Erreur Python (bridge)",
        details: stderr || `Process exited with code ${code}`,
      });
    }

    try {
      const parsed = JSON.parse(stdout.trim());
      return res.json(parsed);
    } catch (e) {
      return res.status(500).json({
        error: "Réponse JSON invalide du bridge",
        raw: stdout,
        details: String(e),
      });
    }
  });

  // On envoie un JSON au bridge (plus robuste que texte brut)
  py.stdin.write(JSON.stringify({ text }));
  py.stdin.end();
});

app.listen(PORT, () => {
  console.log(`Listening on http://localhost:${PORT}`);
});
