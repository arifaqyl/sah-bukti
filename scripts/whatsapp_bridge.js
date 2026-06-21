const express = require("express");
const qrcode = require("qrcode-terminal");
const { Client, LocalAuth } = require("whatsapp-web.js");

const port = Number(process.env.SAHBUKTI_WHATSAPP_BRIDGE_PORT || 3010);
const defaultSessionName = process.env.SAHBUKTI_WHATSAPP_SESSION_NAME || "sahbukti";

const app = express();
app.use(express.json());

const sessions = new Map();

function buildEvidenceUrl() {
  const explicit = process.env.SAHBUKTI_WHATSAPP_EVIDENCE_URL;
  if (explicit) {
    return explicit;
  }
  const apiBase = (process.env.SAHBUKTI_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
  return `${apiBase}/api/v1/evidence/whatsapp`;
}

function buildMediaType(message) {
  if (message.type === "ptt" || message.type === "audio") {
    return "voice_note";
  }
  if (message.type === "image") {
    return "receipt_image";
  }
  if (message.type === "document") {
    return "document";
  }
  return "text";
}

function buildMockTranscript(message, mediaType) {
  if (mediaType !== "voice_note") {
    return null;
  }
  return process.env.SAHBUKTI_MOCK_TRANSCRIPT || null;
}

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
    if (message.fromMe) {
      return;
    }

    try {
      const phone = message.from.replace("@c.us", "");
      const mediaType = buildMediaType(message);
      const transcript = buildMockTranscript(message, mediaType);
      const evidenceUrl = buildEvidenceUrl();
      const accessToken = process.env.SAHBUKTI_ACCESS_TOKEN;
      const businessId = Number(process.env.SAHBUKTI_WHATSAPP_BUSINESS_ID || 1);
      const response = await fetch(`${evidenceUrl}?business_id=${businessId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
        body: JSON.stringify({
          business_id: businessId,
          from_phone: phone,
          message: message.body || null,
          transcript,
          media_type: mediaType,
          media_metadata: {
            whatsapp_type: message.type,
            has_media: Boolean(message.hasMedia),
            timestamp: message.timestamp,
          },
        }),
      });

      if (response.status === 401 || response.status === 403) {
        const webhookUrl = process.env.SAHBUKTI_WHATSAPP_WEBHOOK_URL;
        if (webhookUrl) {
          await fetch(webhookUrl, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...(process.env.SAHBUKTI_WEBHOOK_SECRET
                ? { "x-sahbukti-webhook-secret": process.env.SAHBUKTI_WEBHOOK_SECRET }
                : {}),
            },
            body: JSON.stringify({
              message: message.body || transcript || `[${mediaType}]`,
              from: phone,
              business_id: businessId,
            }),
          });
          return;
        }
      }

      const payload = await response.json().catch(() => null);
      if (payload && payload.message) {
        await message.reply(payload.message);
      }
    } catch (error) {
      console.error(`[${sessionName}] evidence forward failed`, error);
    }
  });

  client.initialize();
  sessions.set(sessionName, client);
  return client;
}

app.post("/send", async (req, res) => {
  const session = req.body.session || defaultSessionName;
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
  getClient(defaultSessionName);
});
