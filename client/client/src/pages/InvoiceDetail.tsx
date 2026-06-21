import { Link, useParams } from "wouter";
import { useEffect, useMemo, useState } from "react";
import { DashboardLayout } from "@/components/DashboardLayout";
import { Panel, Badge } from "@/components/sahbukti-ui";
import { currency } from "@/lib/sahbukti";
import { ArrowLeft, Download, Loader2 } from "lucide-react";
import { toast } from "sonner";

interface InvoiceDetailRecord {
  id: number;
  invoice_number: string;
  customer_name: string;
  total: number;
  subtotal: number;
  tax: number;
  payment_status: string;
  payment_method: string;
  due_date?: string | null;
  created_at: string;
  items: Array<{ name: string; quantity?: number; qty?: number; unit_price?: number; price?: number }>;
  pending_proof_count?: number;
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

export default function InvoiceDetail() {
  const params = useParams();
  const id = params.id || "";
  const [invoice, setInvoice] = useState<InvoiceDetailRecord | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const res = await fetch(`/api/v1/invoices/${id}?${currentBusinessQuery()}`, {
          headers: { Accept: "application/json", ...authHeaders() },
          credentials: "include",
        });
        if (!res.ok) {
          throw new Error("Failed to load invoice");
        }
        setInvoice(await res.json());
      } catch (err: any) {
        toast.error(err.message || "Failed to load invoice");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  const lines = useMemo(() => invoice?.items || [], [invoice]);
  const subtotal = invoice?.subtotal ?? lines.reduce((sum, line) => sum + Number(line.quantity ?? line.qty ?? 0) * Number(line.unit_price ?? line.price ?? 0), 0);
  const statusTone =
    invoice?.payment_status === "paid"
      ? "success"
      : invoice?.payment_status === "overdue"
        ? "danger"
        : invoice?.payment_status === "partial"
          ? "accent"
          : "warn";
  const statusLabel = invoice?.payment_status === "pending" ? "Unpaid" : invoice?.payment_status || "Loading";

  return (
    <DashboardLayout
      title={invoice ? `Invoice ${invoice.invoice_number}` : `Invoice ${id}`}
      subtitle={invoice ? `Customer: ${invoice.customer_name} · Issued ${new Date(invoice.created_at).toLocaleDateString("en-MY")}` : "Loading invoice"}
      action={<Badge tone={statusTone}>{statusLabel}</Badge>}
    >
      <Link href="/invoices" className="mb-5 inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> Back to invoices
      </Link>

      {loading || !invoice ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-accent" />
        </div>
      ) : (
        <div className="grid gap-5 lg:grid-cols-[1.6fr_1fr]">
          <Panel title="Line items">
            <div className="overflow-hidden rounded-xl border border-border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-background text-left text-xs uppercase tracking-wider text-muted-foreground">
                    <th className="px-5 py-3 font-semibold">Item</th>
                    <th className="px-5 py-3 font-semibold">Qty</th>
                    <th className="px-5 py-3 text-right font-semibold">Price</th>
                    <th className="px-5 py-3 text-right font-semibold">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {lines.map((line, index) => {
                    const qty = Number(line.quantity ?? line.qty ?? 0);
                    const price = Number(line.unit_price ?? line.price ?? 0);
                    return (
                      <tr key={`${line.name}-${index}`} className={index !== lines.length - 1 ? "border-b border-border" : ""}>
                        <td className="px-5 py-3.5 font-medium">{line.name}</td>
                        <td className="px-5 py-3.5 text-muted-foreground">{qty}</td>
                        <td className="px-5 py-3.5 text-right text-muted-foreground">{currency(price)}</td>
                        <td className="px-5 py-3.5 text-right font-serif">{currency(qty * price)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Panel>

          <div className="space-y-5">
            <Panel title="Summary">
              <div className="space-y-2.5 text-sm">
                <div className="flex justify-between"><span className="text-muted-foreground">Subtotal</span><span className="font-serif">{currency(subtotal)}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Tax</span><span className="font-serif">{currency(invoice.tax || 0)}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Method</span><span>{invoice.payment_method}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Proofs waiting</span><span>{Number(invoice.pending_proof_count || 0)}</span></div>
                {invoice.due_date && <div className="flex justify-between"><span className="text-muted-foreground">Due date</span><span>{invoice.due_date}</span></div>}
                <div className="mt-2 flex justify-between border-t border-border pt-3 text-base"><span className="font-medium">Total</span><span className="font-serif text-xl">{currency(invoice.total)}</span></div>
              </div>
            </Panel>
            <Panel title="Actions">
              <div className="flex flex-col gap-3">
                <a
                  href={`/api/v1/invoices/${invoice.id}/receipt?${currentBusinessQuery()}`}
                  className="inline-flex items-center justify-center gap-2 rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-accent-foreground transition-transform hover:-translate-y-0.5 active:scale-[0.97]"
                >
                  <Download className="h-4 w-4" />
                  Download receipt PDF
                </a>
                <Link href="/review" className="inline-flex items-center justify-center gap-2 rounded-full border border-border px-5 py-2.5 text-sm font-medium transition-colors hover:bg-secondary">
                  Review payment proofs
                </Link>
              </div>
            </Panel>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
