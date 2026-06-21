import { useState } from "react";
import { DashboardLayout } from "@/components/DashboardLayout";
import { Panel, Badge, ListRow } from "@/components/sahbukti-ui";
import { MessageSquareText, FileSpreadsheet, Sparkles } from "lucide-react";
import { toast } from "sonner";

const RECENT = [
  { src: "WhatsApp", text: "dah bayar for the last order", time: "2 min ago", tone: "warn" as const, status: "Parsed" },
  { src: "CSV", text: "32 rows imported from sales.csv", time: "1 hr ago", tone: "success" as const, status: "Logged" },
  { src: "WhatsApp", text: "nasi lemak dua, teh tarik satu", time: "3 hr ago", tone: "accent" as const, status: "New" },
];

export default function Evidence() {
  const [wa, setWa] = useState("");
  const [csv, setCsv] = useState("");

  async function postEvidence(path: string, body: Record<string, unknown>) {
    const token = localStorage.getItem("kede_token");
    const businessId = localStorage.getItem("kede_business_id");
    const useDemo = !token || !businessId;
    const query = useDemo ? "demo=1" : `business_id=${encodeURIComponent(businessId)}`;

    const response = await fetch(`/api/v1${path}?${query}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ business_id: businessId ? Number(businessId) : 1, ...body }),
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail || `Request failed: ${response.status}`);
    }
    return response.json();
  }

  async function submitWhatsAppEvidence() {
    if (!wa.trim()) {
      toast.error("Paste WhatsApp evidence first.");
      return;
    }
    try {
      await postEvidence("/evidence/whatsapp", {
        from_phone: "manual-paste",
        message: wa,
        transcript: null,
        media_type: "text",
        media_metadata: { source: "frontend_paste" },
      });
      toast.success("WhatsApp evidence sent to Review");
      setWa("");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Evidence import failed");
    }
  }

  function fillSampleOrder() {
    setWa("nasi lemak dua teh tarik satu");
  }

  function fillSamplePayment() {
    setWa("dah bayar for the last order");
  }

  async function submitCsvEvidence() {
    if (!csv.trim()) {
      toast.error("Paste CSV rows first.");
      return;
    }
    try {
      await postEvidence("/evidence/import", {
        source_type: "csv_export",
        raw_text: csv,
        filename: "frontend-csv-export.csv",
        mime_type: "text/csv",
        media_metadata: { source: "frontend_csv_textarea" },
      });
      toast.success("CSV rows sent to Review");
      setCsv("");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "CSV import failed");
    }
  }

  return (
    <DashboardLayout
      title="Evidence"
      subtitle="Bring in WhatsApp and CSV evidence — nothing posts until reviewed."
    >
      <div className="grid gap-5 lg:grid-cols-2">
        <Panel
          title="WhatsApp paste"
          aside={<MessageSquareText className="h-5 w-5 text-accent" />}
        >
          <p className="mb-3 text-sm text-muted-foreground">Paste an order or payment message. Sah.Bukti turns it into a pending invoice or reviewable proof.</p>
          <div className="mb-3 flex flex-wrap gap-2">
            <button
              onClick={fillSampleOrder}
              className="inline-flex items-center gap-2 rounded-full border border-border px-4 py-2 text-xs font-medium transition-colors hover:bg-secondary"
            >
              Sample order
            </button>
            <button
              onClick={fillSamplePayment}
              className="inline-flex items-center gap-2 rounded-full border border-border px-4 py-2 text-xs font-medium transition-colors hover:bg-secondary"
            >
              Sample paid message
            </button>
          </div>
          <textarea
            value={wa}
            onChange={(e) => setWa(e.target.value)}
            rows={8}
            placeholder={"nasi lemak dua teh tarik satu\n\ndah bayar for the last order"}
            className="w-full resize-none rounded-xl border border-input bg-background p-4 text-sm outline-none transition-all focus:border-accent focus:ring-4 focus:ring-accent/10"
          />
          <button
            onClick={submitWhatsAppEvidence}
            className="mt-4 inline-flex items-center gap-2 rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-accent-foreground transition-transform hover:-translate-y-0.5 active:scale-[0.97]"
          >
            <Sparkles className="h-4 w-4" /> Create review record
          </button>
        </Panel>

        <Panel
          title="CSV import"
          aside={<FileSpreadsheet className="h-5 w-5 text-accent" />}
        >
          <p className="mb-3 text-sm text-muted-foreground">Paste rows from a CSV export.</p>
          <textarea
            value={csv}
            onChange={(e) => setCsv(e.target.value)}
            rows={8}
            placeholder={"date,customer,amount,ref\n2026-06-19,Ali,45.00,INV-001"}
            className="w-full resize-none rounded-xl border border-input bg-background p-4 font-mono text-[13px] outline-none transition-all focus:border-accent focus:ring-4 focus:ring-accent/10"
          />
          <button
            onClick={submitCsvEvidence}
            className="mt-4 inline-flex items-center gap-2 rounded-full border border-border px-5 py-2.5 text-sm font-medium transition-colors hover:bg-secondary"
          >
            Import rows
          </button>
        </Panel>
      </div>

      <div className="mt-5">
        <Panel title="Recent evidence">
          <div className="space-y-3">
            {RECENT.map((r, i) => (
              <ListRow
                key={i}
                title={r.text}
                subtitle={`${r.src} · ${r.time}`}
                badge={<Badge tone={r.tone}>{r.status}</Badge>}
              />
            ))}
          </div>
        </Panel>
      </div>
    </DashboardLayout>
  );
}
