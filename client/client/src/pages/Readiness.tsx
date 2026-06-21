import { Link } from "wouter";
import { useEffect, useMemo, useState } from "react";
import { DashboardLayout } from "@/components/DashboardLayout";
import { Panel, Badge, ListRow } from "@/components/sahbukti-ui";
import { currency } from "@/lib/sahbukti";
import { ArrowRight, Loader2 } from "lucide-react";
import { toast } from "sonner";

interface ReadinessPayload {
  readiness_score: number;
  readiness_status: string;
  summary: {
    pending_proof_count: number;
    overdue_total: number;
  };
  blockers: Array<{ title: string; severity: "high" | "medium" | "low"; message: string; count: number }>;
  action_plan: Array<{ title: string; action: string }>;
}

function currentBusinessQuery() {
  const token = localStorage.getItem("sahbukti_token");
  const businessId = localStorage.getItem("sahbukti_business_id");
  return token && businessId ? `business_id=${encodeURIComponent(businessId)}` : "demo=1";
}

function authHeaders() {
  const token = localStorage.getItem("sahbukti_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export default function Readiness() {
  const month = useMemo(() => new Date().toISOString().slice(0, 7), []);
  const [payload, setPayload] = useState<ReadinessPayload | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const res = await fetch(`/api/v1/month-end/readiness?month=${month}&${currentBusinessQuery()}`, {
          headers: { Accept: "application/json", ...authHeaders() },
          credentials: "include",
        });
        if (!res.ok) {
          const body = await res.json().catch(() => null);
          throw new Error(body?.detail || "Failed to load readiness");
        }
        setPayload(await res.json());
      } catch (err: any) {
        toast.error(err.message || "Failed to load readiness");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [month]);

  const score = payload?.readiness_score || 0;
  const tone = payload?.readiness_status === "ready" ? "success" : payload?.readiness_status === "blocked" ? "danger" : "warn";

  return (
    <DashboardLayout title="Month-end readiness" subtitle={`What is actually ready for the accountant — ${month}.`}>
      {loading || !payload ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-accent" />
        </div>
      ) : (
        <div className="grid gap-5 lg:grid-cols-[1fr_1.4fr]">
          <Panel title="Readiness score">
            <div className="flex items-end justify-between">
              <span className="font-serif text-5xl">{score}%</span>
              <Badge tone={tone}>{payload.readiness_status.replace("_", " ")}</Badge>
            </div>
            <div className="mt-4 h-3 overflow-hidden rounded-full bg-background">
              <div className="h-full rounded-full transition-all" style={{ width: `${score}%`, background: "var(--clay)" }} />
            </div>
            <div className="mt-6 space-y-3">
              {payload.blockers.map((blocker) => (
                <div key={blocker.title} className="flex items-start gap-3">
                  <span
                    className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-bold"
                    style={{
                      background: blocker.severity === "high" ? "oklch(0.9 0.05 25)" : "var(--clay-soft)",
                      color: blocker.severity === "high" ? "oklch(0.46 0.14 25)" : "var(--clay)",
                    }}
                  >
                    {blocker.severity === "high" ? "!" : "•"}
                  </span>
                  <div>
                    <div className="text-sm font-medium">{blocker.title}</div>
                    <div className="text-xs text-muted-foreground">{blocker.message} ({blocker.count})</div>
                  </div>
                </div>
              ))}
              {payload.blockers.length === 0 && <div className="text-sm text-muted-foreground">No blockers right now. This month is clean enough to hand off.</div>}
            </div>
          </Panel>

          <div className="space-y-5">
            <Panel
              title="Pending proof impact"
              aside={
                <Link href="/review" className="inline-flex items-center gap-1 text-sm font-medium text-accent">
                  Resolve <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              }
            >
              <p className="text-sm text-muted-foreground">
                {payload.summary.pending_proof_count} payment proofs are still waiting for owner approval. They will not affect the ledger until reviewed.
              </p>
              <div className="mt-4 rounded-xl border border-border bg-background p-4 text-sm">
                Overdue value still open: <span className="font-medium text-foreground">{currency(payload.summary.overdue_total || 0)}</span>
              </div>
            </Panel>

            <Panel title="Action plan">
              <div className="space-y-3">
                {payload.action_plan.map((step) => (
                  <ListRow key={step.title} title={step.title} subtitle={step.action} badge={<Badge tone="accent">Next</Badge>} />
                ))}
                {payload.action_plan.length === 0 && <div className="text-sm text-muted-foreground">No follow-up action needed.</div>}
              </div>
            </Panel>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
