const express = require("express");
const qrcode = require("qrcode-terminal");
const { Client, LocalAuth } = require("whatsapp-web.js");

const port = Number(process.env.KEDE_WHATSAPP_BRIDGE_PORT || 3010);

const app = express();
app.use(express.json());

const sessions = new Map();

function getClient(sessionName) {
  if (sessions.has(sessionName)) {
    return sessions.get(sessionName);
  }

  const client = new Client({
    authStrategy: new LocalAuth({ clientId: sessionName }),
    puppeteer: { headless: true },
  });

  client.on("qr", (qr) => {
    console.log(`[${sessionName}] Scan this QR in WhatsApp:`);
    qrcode.generate(qr, { small: true });
  });

  client.on("ready", () => {
    console.log(`[${sessionName}] WhatsApp bridge ready`);
  });

  client.on("message", async (message) => {
    const webhookUrl = process.env.KEDE_WHATSAPP_WEBHOOK_URL;
    if (!webhookUrl || message.fromMe) {
      return;
    }

    try {
      await fetch(webhookUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: message.body,
          from: message.from.replace("@c.us", ""),
          business_id: Number(process.env.KEDE_WHATSAPP_BUSINESS_ID || 1),
        }),
      });
    } catch (error) {
      console.error(`[${sessionName}] webhook forward failed`, error);
    }
  });

  client.initialize();
  sessions.set(sessionName, client);
  return client;
}

app.post("/send", async (req, res) => {
  const session = req.body.session || "kede";
  const phone = String(req.body.phone || "").replace(/\D/g, "");
  const text = req.body.text;

  if (!phone || !text) {
    res.status(400).json({ ok: false, detail: "phone and text are required" });
    return;
  }

  try {
    const client = getClient(session);
    await client.sendMessage(`${phone}@c.us`, text);
    res.json({ ok: true });
  } catch (error) {
    res.status(502).json({ ok: false, detail: String(error) });
  }
});

app.get("/health", (_req, res) => {
  res.json({ ok: true });
});

app.listen(port, () => {
  console.log(`WhatsApp bridge listening on ${port}`);
  getClient(process.env.KEDE_WHATSAPP_SESSION_NAME || "kede");
});
