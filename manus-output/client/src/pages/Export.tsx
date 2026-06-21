import { useState } from "react";
import { DashboardLayout } from "@/components/DashboardLayout";
import { Panel } from "@/components/sahbukti-ui";
import { Download, FileJson, FileText, Loader2 } from "lucide-react";
import { toast } from "sonner";

function buildMonthOptions() {
  const formatter = new Intl.DateTimeFormat("en-MY", { month: "long", year: "numeric" });
  const today = new Date();
  return Array.from({ length: 4 }, (_, index) => {
    const date = new Date(today.getFullYear(), today.getMonth() - index, 1);
    const value = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
    return { label: formatter.format(date), value };
  });
}

export default function Export() {
  const months = buildMonthOptions();
  const [month, setMonth] = useState(months[0].value);
  const [format, setFormat] = useState<"csv" | "json">("csv");
  const [loading, setLoading] = useState(false);

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/exports/accountant?month=${encodeURIComponent(month)}&include_proof_payloads=false&format=${format}&demo=1`, {
        headers: { Accept: format === "json" ? "application/json" : "text/csv" },
        credentials: "include",
        cache: "no-store",
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Export failed (${res.status})`);
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const ext = format === "json" ? "json" : "csv";
      a.download = `sahbukti-export-${month}-${Date.now()}.${ext}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success(`Export downloaded (${format.toUpperCase()})`);
    } catch (err: any) {
      toast.error(err.message || "Export failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <DashboardLayout title="Accountant export" subtitle="Hand off a clean, reviewed package for the books.">
      <div className="grid gap-5 lg:grid-cols-[1fr_1fr]">
        <Panel title="Build export">
          <div className="space-y-5">
            <div>
              <label className="mb-2 block text-[13px] font-semibold text-muted-foreground">Period</label>
              <select
                value={month}
                onChange={(e) => setMonth(e.target.value)}
                className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm outline-none focus:border-accent focus:ring-4 focus:ring-accent/10"
              >
                {months.map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-2 block text-[13px] font-semibold text-muted-foreground">Format</label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => setFormat("csv")}
                  className={`flex items-center gap-2 rounded-xl border p-4 text-sm font-medium transition-all ${
                    format === "csv" ? "border-accent bg-accent/8" : "border-border bg-background text-muted-foreground hover:border-accent/40"
                  }`}
                >
                  <FileText className="h-4 w-4" /> CSV
                </button>
                <button
                  onClick={() => setFormat("json")}
                  className={`flex items-center gap-2 rounded-xl border p-4 text-sm font-medium transition-all ${
                    format === "json" ? "border-accent bg-accent/8" : "border-border bg-background text-muted-foreground hover:border-accent/40"
                  }`}
                >
                  <FileJson className="h-4 w-4" /> JSON
                </button>
              </div>
            </div>
            <button
              onClick={handleGenerate}
              disabled={loading}
              className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-accent py-3.5 text-sm font-medium text-accent-foreground transition-transform hover:-translate-y-0.5 active:scale-[0.98] disabled:opacity-60"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              {loading ? "Generating..." : "Generate export"}
            </button>
          </div>
        </Panel>

        <Panel title="What's included">
          <ul className="space-y-3 text-sm text-muted-foreground">
            {[
              "Only reviewed and approved transactions",
              "Reconciled invoices with payment references",
              "Logged supplier bills and expenses",
              "A readiness note flagging anything still pending",
            ].map((li) => (
              <li key={li} className="flex items-start gap-3">
                <span className="mt-0.5 text-accent">✓</span>
                {li}
              </li>
            ))}
          </ul>
          <div className="mt-6 rounded-xl border border-border bg-background p-4 text-sm">
            <div className="font-medium">Last export</div>
            <div className="mt-1 text-muted-foreground">May 2026 · CSV · generated 2 June 2026</div>
          </div>
        </Panel>
      </div>
    </DashboardLayout>
  );
}
