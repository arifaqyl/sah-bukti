import { Link } from "wouter";
import { useState, useEffect, useMemo } from "react";
import { DashboardLayout } from "@/components/DashboardLayout";
import { StatCard, Panel, ListRow, Badge } from "@/components/sahbukti-ui";
import { useAuth } from "@/contexts/AuthContext";
import { currency } from "@/lib/sahbukti";
import { Plus, ArrowRight, Inbox, CheckCircle2, MessageCircle, X, BookOpen, Loader2, ShieldCheck, Send, Database } from "lucide-react";
import { toast } from "sonner";

const WELCOME_KEY = "sahbukti_welcome_dismissed";

function currentBusinessQuery() {
  const token = localStorage.getItem("sahbukti_token");
  const businessId = localStorage.getItem("sahbukti_business_id");
  return token && businessId ? `business_id=${encodeURIComponent(businessId)}` : "demo=1";
}

function authHeaders() {
  const token = localStorage.getItem("sahbukti_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export default function Dashboard() {
  const { user } = useAuth();
  const [showWelcome, setShowWelcome] = useState(() => {
    try {
      return localStorage.getItem(WELCOME_KEY) !== "1";
    } catch {
      return true;
    }
  });
  const [stats, setStats] = useState({ pending: 0, revenue: 0, customers: 0, lowStock: 0 });
  const [invoices, setInvoices] = useState<any[]>([]);
  const [readiness, setReadiness] = useState<{ score: number; status: string }>({ score: 0, status: "loading" });
  const [loading, setLoading] = useState(true);
  const [demoLoading, setDemoLoading] = useState(false);
  const [waLoading, setWaLoading] = useState(false);
  const [waPhone, setWaPhone] = useState("");
  const [waMessage, setWaMessage] = useState("status");
  const [agentResult, setAgentResult] = useState<{ reply: string; sent: boolean; detail: string } | null>(null);

  const month = useMemo(() => new Date().toISOString().slice(0, 7), []);

  const dismissWelcome = () => {
    try {
      localStorage.setItem(WELCOME_KEY, "1");
    } catch {
    }
    setShowWelcome(false);
  };

  const load = async () => {
    setLoading(true);
    try {
      const query = currentBusinessQuery();
      const [proofRes, invoiceRes, customerRes, inventoryRes, readinessRes, sessionRes] = await Promise.all([
        fetch(`/api/v1/review/payment-proofs?review_state=needs_review&${query}`, { headers: authHeaders(), credentials: "include" }),
        fetch(`/api/v1/invoices?${query}`, { headers: authHeaders(), credentials: "include" }),
        fetch(`/api/v1/customers?${query}`, { headers: authHeaders(), credentials: "include" }),
        fetch(`/api/v1/inventory/ingredients?${query}`, { headers: authHeaders(), credentials: "include" }),
        fetch(`/api/v1/month-end/readiness?month=${month}&${query}`, { headers: authHeaders(), credentials: "include" }),
        fetch(`/api/v1/whatsapp/session?demo=1`),
      ]);

      const proofs = proofRes.ok ? await proofRes.json() : [];
      const invoiceData = invoiceRes.ok ? await invoiceRes.json() : [];
      const customerData = customerRes.ok ? await customerRes.json() : [];
      const inventoryData = inventoryRes.ok ? await inventoryRes.json() : [];
      const readinessData = readinessRes.ok ? await readinessRes.json() : null;
      const sessionData = sessionRes.ok ? await sessionRes.json() : null;

      setStats({
        pending: proofs.length,
        revenue: invoiceData.filter((invoice: any) => invoice.payment_status === "paid").reduce((sum: number, invoice: any) => sum + Number(invoice.total || 0), 0),
        customers: customerData.length,
        lowStock: inventoryData.filter((item: any) => Number(item.current_stock) <= Number(item.reorder_point)).length,
      });
      setInvoices(invoiceData.slice(0, 4));
      setReadiness({
        score: readinessData?.readiness_score || 0,
        status: readinessData?.readiness_status || "unknown",
      });
      if (sessionData?.me?.id && !waPhone) {
        setWaPhone(String(sessionData.me.id));
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const seedDemo = async () => {
    setDemoLoading(true);
    try {
      const response = await fetch("/api/v1/demo/seed?demo=1", { method: "POST" });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail || `Demo seed failed (${response.status})`);
      }
      toast.success("Demo data loaded");
      await load();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Demo seed failed");
    } finally {
      setDemoLoading(false);
    }
  };

  const sendAgentCommand = async () => {
    if (!waPhone.trim() || !waMessage.trim()) {
      toast.error("Phone and message are required.");
      return;
    }
    setWaLoading(true);
    try {
      const response = await fetch(`/api/v1/whatsapp/agent/command?demo=1`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ from_phone: waPhone.trim(), message: waMessage.trim() }),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(payload?.detail || "WhatsApp agent command failed");
      }
      setAgentResult({
        reply: payload?.reply || "",
        sent: Boolean(payload?.sent),
        detail: payload?.detail || "",
      });
      toast.success(payload?.sent ? "WhatsApp reply sent" : "Agent processed command");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "WhatsApp agent command failed");
    } finally {
      setWaLoading(false);
    }
  };

  return (
    <DashboardLayout
      title={`Selamat datang, ${user?.display_name || "Owner"}`}
      subtitle="Here is what's happening with your shop today."
      action={
        <Link href="/invoices" className="inline-flex items-center gap-2 rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-accent-foreground transition-transform hover:-translate-y-0.5 active:scale-[0.97]">
          <Plus className="h-4 w-4" /> New invoice
        </Link>
      }
    >
      {showWelcome && (
        <div className="relative mb-6 overflow-hidden rounded-[1.5rem] border border-accent/30 bg-[var(--clay-soft)]/50 p-6">
          <button
            onClick={dismissWelcome}
            aria-label="Dismiss"
            className="absolute right-4 top-4 flex h-7 w-7 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-card hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-accent">
                <MessageCircle className="h-6 w-6 text-white" />
              </div>
              <div>
                <h2 className="font-serif text-xl leading-tight">New here? Connect WhatsApp in 5 minutes.</h2>
                <p className="mt-1 max-w-xl text-sm leading-relaxed text-muted-foreground">
                  Sah.Bukti works best when your shop phone sends order messages and payment confirmations into Review first, then you approve what is true.
                </p>
              </div>
            </div>
            <div className="flex shrink-0 gap-2.5">
              <Link href="/help" className="inline-flex items-center gap-2 rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-white transition-transform active:scale-[0.97]">
                <BookOpen className="h-4 w-4" /> Open setup guide
              </Link>
            </div>
          </div>
        </div>
      )}

      <div className="mb-6 grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <Panel title="Trust boundary" aside={<Badge tone="success">Live</Badge>}>
          <div className="flex items-start gap-3 text-sm">
            <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-accent" />
            <div>
              <div className="font-medium">No ledger mutation without owner approval.</div>
              <div className="mt-1 text-muted-foreground">
                WhatsApp evidence, CSV imports, direct payment pages, and provider callbacks all stop in Review first.
              </div>
            </div>
          </div>
        </Panel>

        <Panel title="Demo controls">
          <div className="flex flex-wrap gap-3">
            <button
              onClick={seedDemo}
              disabled={demoLoading}
              className="inline-flex items-center gap-2 rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-accent-foreground transition-transform hover:-translate-y-0.5 active:scale-[0.97] disabled:opacity-60"
            >
              {demoLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Database className="h-4 w-4" />}
              {demoLoading ? "Loading demo..." : "Load demo data"}
            </button>
            <Link href="/review" className="inline-flex items-center gap-2 rounded-full border border-border px-5 py-2.5 text-sm font-medium transition-colors hover:bg-secondary">
              Open review queue
            </Link>
          </div>
        </Panel>
      </div>

      <div className="stagger grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Pending review" value={String(stats.pending)} hint="Proofs awaiting your approval" />
        <StatCard label="Ready for export" value={currency(stats.revenue)} hint="Approved this month" />
        <StatCard label="Active customers" value={String(stats.customers)} hint="Real customer records" />
        <StatCard label="Low stock items" value={String(stats.lowStock)} hint="Needs reordering" />
      </div>

      <div className="mt-7 grid gap-5 lg:grid-cols-[1.6fr_1fr]">
        <Panel
          title="Recent activity"
          aside={
            <Link href="/invoices" className="inline-flex items-center gap-1 text-sm font-medium text-accent">
              View all <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          }
        >
          <div className="space-y-3">
            {loading ? <div>Loading...</div> : invoices.map((row: any) => (
              <ListRow
                key={row.id}
                title={row.invoice_number}
                subtitle={`Customer: ${row.customer_name || "Unknown"}`}
                amount={currency(row.total)}
                badge={<Badge tone={row.payment_status === "paid" ? "success" : row.payment_status === "pending" ? "warn" : "danger"}>{row.payment_status === "pending" ? "unpaid" : row.payment_status}</Badge>}
              />
            ))}
            {!loading && invoices.length === 0 && <div className="text-sm text-muted-foreground">No invoices yet. Use “Load demo data” or create one now.</div>}
          </div>
        </Panel>

        <div className="space-y-5">
          <Panel title="Daily summary">
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-muted-foreground">Ready score</span><span className="font-medium">{readiness.score}%</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Pending proofs</span><span className="font-medium">{stats.pending}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Approved revenue</span><span className="font-medium">{currency(stats.revenue)}</span></div>
            </div>
            <Link href="/readiness" className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-accent">
              Open readiness <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </Panel>

        <Panel title="Assistant simulator">
            <div className="space-y-3">
              <input
                value={waPhone}
                onChange={(e) => setWaPhone(e.target.value)}
                placeholder="Owner phone"
                className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm outline-none focus:border-accent focus:ring-4 focus:ring-accent/10"
              />
              <input
                value={waMessage}
                onChange={(e) => setWaMessage(e.target.value)}
                placeholder="status or menu"
                className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm outline-none focus:border-accent focus:ring-4 focus:ring-accent/10"
              />
              <button
                onClick={sendAgentCommand}
                disabled={waLoading}
                className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-accent py-3 text-sm font-medium text-accent-foreground transition-transform hover:-translate-y-0.5 active:scale-[0.98] disabled:opacity-60"
              >
                {waLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                {waLoading ? "Sending..." : "Run assistant command"}
              </button>
              {agentResult && (
                <div className="rounded-xl border border-border bg-background p-4 text-sm">
                  <div className="font-medium">Agent reply</div>
                  <pre className="mt-2 whitespace-pre-wrap font-sans text-muted-foreground">{agentResult.reply}</pre>
                  <div className="mt-2 text-xs text-muted-foreground">
                    Delivery: {agentResult.sent ? "sent via adapter" : agentResult.detail || "not delivered"}
                  </div>
                </div>
              )}
            </div>
          </Panel>

          <Panel title="Next steps">
            <div className="space-y-3">
              <Link href="/review" className="flex items-start gap-3 rounded-xl border border-border bg-background p-4 transition-colors hover:border-accent/50">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg" style={{ background: "var(--clay-soft)" }}>
                  <CheckCircle2 className="h-5 w-5 text-accent" />
                </div>
                <div>
                  <div className="text-sm font-medium">{stats.pending} payment proofs to approve</div>
                  <div className="text-xs text-muted-foreground">Nothing posts to your ledger until you do.</div>
                </div>
              </Link>
              <Link href="/evidence" className="flex items-start gap-3 rounded-xl border border-border bg-background p-4 transition-colors hover:border-accent/50">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg" style={{ background: "var(--clay-soft)" }}>
                  <Inbox className="h-5 w-5 text-accent" />
                </div>
                <div>
                  <div className="text-sm font-medium">Import today's WhatsApp evidence</div>
                  <div className="text-xs text-muted-foreground">Paste an order or payment message, or run the assistant simulator.</div>
                </div>
              </Link>
            </div>
          </Panel>
        </div>
      </div>
    </DashboardLayout>
  );
}
