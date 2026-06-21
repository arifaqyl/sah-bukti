import { useEffect, useMemo, useState } from "react";
import { DashboardLayout } from "@/components/DashboardLayout";
import { Panel, Badge, EmptyState } from "@/components/sahbukti-ui";
import { currency } from "@/lib/sahbukti";
import { Check, ChevronDown, ChevronUp, FileText, Inbox, Loader2, Pencil, RotateCcw, X } from "lucide-react";
import { toast } from "sonner";

interface Proof {
  id: number;
  invoice_number: string;
  extracted_amount: number;
  source_channel: string;
  extracted_reference: string | null;
  review_state: string;
  created_at: string | null;
  ocr_payload: Record<string, any> | null;
  decision_reason: string | null;
}

function currentBusinessQuery() {
  const token = localStorage.getItem("kede_token");
  const businessId = localStorage.getItem("kede_business_id");
  return token && businessId ? `business_id=${encodeURIComponent(businessId)}` : "demo=1";
}

function authHeaders() {
  const token = localStorage.getItem("kede_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export default function Review() {
  const [proofs, setProofs] = useState<Proof[]>([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [amountDraft, setAmountDraft] = useState("");
  const [referenceDraft, setReferenceDraft] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/review/payment-proofs?review_state=needs_review&${currentBusinessQuery()}`, {
        headers: { Accept: "application/json", ...authHeaders() },
        credentials: "include",
      });
      if (!res.ok) {
        throw new Error("Failed to load proofs");
      }
      const data = await res.json();
      const normalized = Array.isArray(data)
        ? data.map((proof) => ({
            id: Number(proof?.id ?? 0),
            invoice_number: proof?.invoice_number ?? "",
            extracted_amount: typeof proof?.extracted_amount === "number" ? proof.extracted_amount : 0,
            source_channel: proof?.source_channel ?? "unknown",
            extracted_reference: proof?.extracted_reference ?? null,
            review_state: proof?.review_state ?? "needs_review",
            created_at: proof?.created_at ?? null,
            ocr_payload: proof?.ocr_payload && typeof proof.ocr_payload === "object" ? proof.ocr_payload : null,
            decision_reason: proof?.decision_reason ?? null,
          }))
        : [];
      setProofs(normalized);
    } catch (err: any) {
      toast.error(err.message || "Failed to load review queue");
      setProofs([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const act = async (id: number, approve: boolean) => {
    const proof = proofs.find((item) => item.id === id);
    if (approve && proof) {
      const hasReference = Boolean((proof.extracted_reference || proof.invoice_number || "").trim());
      const hasAmount = Number(proof.extracted_amount || 0) > 0;
      if (!hasReference && !hasAmount) {
        startEdit(proof);
        toast.error("Add amount and invoice reference first, then approve.");
        return;
      }
    }
    setProcessing(String(id));
    try {
      const endpoint = approve ? `/api/v1/review/${id}/approve` : `/api/v1/review/${id}/reject`;
      const res = await fetch(`${endpoint}?${currentBusinessQuery()}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(),
        },
        credentials: "include",
        body: JSON.stringify({}),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Failed (${res.status})`);
      }
      toast.success(approve ? "Proof approved — ledger updated" : "Proof rejected");
      setProofs((p) => p.filter((x) => x.id !== id));
      if (expandedId === id) setExpandedId(null);
      if (editingId === id) setEditingId(null);
    } catch (err: any) {
      if (approve && proof && String(err.message || "").includes("invoice_id is required")) {
        startEdit(proof);
        toast.error("Sah.Bukti needs an invoice reference or unique amount match. Edit this proof first.");
      } else {
        toast.error(err.message || "Action failed");
      }
    } finally {
      setProcessing(null);
    }
  };

  const startEdit = (proof: Proof) => {
    setEditingId(proof.id);
    setExpandedId(proof.id);
    setAmountDraft(String(Number(proof.extracted_amount || 0)));
    setReferenceDraft(proof.extracted_reference || proof.invoice_number || "");
  };

  const saveEdit = async (proofId: number) => {
    setProcessing(`edit-${proofId}`);
    try {
      const res = await fetch(`/api/v1/review/${proofId}?${currentBusinessQuery()}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(),
        },
        credentials: "include",
        body: JSON.stringify({
          amount: Number(amountDraft),
          reference: referenceDraft.trim() || null,
        }),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Failed (${res.status})`);
      }
      const updated = await res.json();
      setProofs((current) =>
        current.map((proof) =>
          proof.id === proofId
            ? {
                ...proof,
                extracted_amount: Number(updated.extracted_amount || 0),
                extracted_reference: updated.extracted_reference || null,
                decision_reason: updated.decision_reason || proof.decision_reason,
              }
            : proof,
        ),
      );
      setEditingId(null);
      toast.success("Proof updated");
    } catch (err: any) {
      toast.error(err.message || "Edit failed");
    } finally {
      setProcessing(null);
    }
  };

  const topPending = proofs.slice(0, 8);
  const totalPending = proofs.length;
  const totalAmount = useMemo(
    () => proofs.reduce((sum, proof) => sum + Number(proof.extracted_amount || 0), 0),
    [proofs],
  );

  return (
    <DashboardLayout
      title="Review"
      subtitle="Payment proofs wait here until you approve. The single gate before truth."
      action={<Badge tone="warn">{totalPending} pending</Badge>}
    >
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-accent" />
        </div>
      ) : topPending.length === 0 ? (
        <EmptyState
          icon={<Inbox className="h-10 w-10" />}
          title="All caught up"
          text="No payment proofs waiting. New evidence will appear here for your approval."
        />
      ) : (
        <>
          <div className="mb-6 flex flex-wrap gap-3">
            <div className="rounded-xl border border-border bg-card px-4 py-2.5 text-sm">
              <span className="text-muted-foreground">Total pending:</span> <strong>{totalPending}</strong>
            </div>
            <div className="rounded-xl border border-border bg-card px-4 py-2.5 text-sm">
              <span className="text-muted-foreground">Amount awaiting:</span> <strong>{currency(totalAmount)}</strong>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {topPending.map((proof) => {
              const amount = Number(proof.extracted_amount || 0);
              const createdAt = proof.created_at ? new Date(proof.created_at).toLocaleString("en-MY") : "Timestamp unavailable";
              const rawText = String(proof.ocr_payload?.raw_text || "").trim();
              const mediaType = String(proof.ocr_payload?.media_type || "text");
              const isExpanded = expandedId === proof.id;
              const isEditing = editingId === proof.id;
              return (
                <Panel key={proof.id}>
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                        {proof.invoice_number || proof.extracted_reference || `Proof #${proof.id}`}
                      </div>
                      <div className="mt-2 font-serif text-3xl">{currency(amount)}</div>
                    </div>
                    <Badge tone="warn">Pending</Badge>
                  </div>

                  <div className="mt-4 space-y-1 text-sm text-muted-foreground">
                    <p>Source: {proof.source_channel}{proof.extracted_reference ? ` · Ref: ${proof.extracted_reference}` : ""}</p>
                    <p>{createdAt}</p>
                    <p>Type: {mediaType.replaceAll("_", " ")}</p>
                    {proof.decision_reason && <p>Reason: {proof.decision_reason.replaceAll("_", " ")}</p>}
                  </div>

                  <div className="mt-5 flex flex-wrap gap-3">
                    <button
                      onClick={() => act(proof.id, true)}
                      disabled={processing === String(proof.id) || processing === `edit-${proof.id}`}
                      className="inline-flex flex-1 items-center justify-center gap-2 rounded-full bg-accent py-2.5 text-sm font-medium text-accent-foreground transition-transform hover:-translate-y-0.5 active:scale-[0.97] disabled:opacity-50"
                    >
                      {processing === String(proof.id) ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                      Approve
                    </button>
                    <button
                      onClick={() => act(proof.id, false)}
                      disabled={processing === String(proof.id) || processing === `edit-${proof.id}`}
                      className="inline-flex flex-1 items-center justify-center gap-2 rounded-full border border-border py-2.5 text-sm font-medium transition-colors hover:bg-secondary disabled:opacity-50"
                    >
                      {processing === String(proof.id) ? <Loader2 className="h-4 w-4 animate-spin" /> : <X className="h-4 w-4" />}
                      Reject
                    </button>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      onClick={() => setExpandedId(isExpanded ? null : proof.id)}
                      className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-accent/50 hover:text-foreground"
                    >
                      {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                      {isExpanded ? "Hide details" : "Show details"}
                    </button>
                    <button
                      onClick={() => startEdit(proof)}
                      className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-accent/50 hover:text-foreground"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                      Edit
                    </button>
                  </div>

                  {isExpanded && (
                    <div className="mt-4 rounded-2xl border border-border bg-background p-4">
                      <div className="mb-3 flex items-center gap-2 text-sm font-medium">
                        <FileText className="h-4 w-4 text-accent" />
                        Evidence details
                      </div>
                      {rawText ? (
                        <div className="rounded-xl border border-border bg-card p-3 text-sm text-foreground">
                          {rawText}
                        </div>
                      ) : (
                        <div className="rounded-xl border border-border bg-card p-3 text-sm text-muted-foreground">
                          No raw text was extracted for this proof.
                        </div>
                      )}

                      {isEditing && (
                        <div className="mt-4 grid gap-3 md:grid-cols-2">
                          <label className="block">
                            <span className="mb-2 block text-[13px] font-semibold text-muted-foreground">Amount</span>
                            <input
                              value={amountDraft}
                              onChange={(e) => setAmountDraft(e.target.value)}
                              type="number"
                              min="0"
                              step="0.01"
                              className="w-full rounded-xl border border-input bg-card px-4 py-3 text-sm outline-none focus:border-accent focus:ring-4 focus:ring-accent/10"
                            />
                          </label>
                          <label className="block">
                            <span className="mb-2 block text-[13px] font-semibold text-muted-foreground">Reference / invoice</span>
                            <input
                              value={referenceDraft}
                              onChange={(e) => setReferenceDraft(e.target.value)}
                              className="w-full rounded-xl border border-input bg-card px-4 py-3 text-sm outline-none focus:border-accent focus:ring-4 focus:ring-accent/10"
                            />
                          </label>
                          <div className="md:col-span-2 flex flex-wrap gap-2">
                            <button
                              onClick={() => saveEdit(proof.id)}
                              disabled={processing === `edit-${proof.id}`}
                              className="inline-flex items-center gap-2 rounded-full bg-accent px-4 py-2.5 text-sm font-medium text-accent-foreground transition-transform hover:-translate-y-0.5 active:scale-[0.97] disabled:opacity-60"
                            >
                              {processing === `edit-${proof.id}` ? <Loader2 className="h-4 w-4 animate-spin" /> : <Pencil className="h-4 w-4" />}
                              Save edit
                            </button>
                            <button
                              onClick={() => setEditingId(null)}
                              className="inline-flex items-center gap-2 rounded-full border border-border px-4 py-2.5 text-sm font-medium transition-colors hover:bg-secondary"
                            >
                              <RotateCcw className="h-4 w-4" />
                              Cancel
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </Panel>
              );
            })}
          </div>
          <button
            onClick={load}
            className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            Refresh queue
          </button>
        </>
      )}
    </DashboardLayout>
  );
}
