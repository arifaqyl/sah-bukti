import { useEffect, useMemo, useState } from "react";
import { useLocation } from "wouter";
import { DashboardLayout } from "@/components/DashboardLayout";
import { ListRow, Badge, Panel } from "@/components/sahbukti-ui";
import { currency } from "@/lib/sahbukti";
import { Plus, Loader2, Download, Trash2 } from "lucide-react";
import { toast } from "sonner";

interface Invoice {
  id: number;
  invoice_number: string;
  customer_id: number;
  customer_name: string;
  total: number;
  payment_status: string;
  created_at: string;
  pending_proof_count?: number;
}

interface Customer {
  id: number;
  name: string;
  phone?: string | null;
}

const FILTERS = ["all", "pending", "paid", "overdue", "partial"];

const STATUS_MAP: Record<string, { label: string; tone: "warn" | "success" | "danger" | "accent" }> = {
  pending: { label: "Unpaid", tone: "warn" },
  paid: { label: "Paid", tone: "success" },
  overdue: { label: "Overdue", tone: "danger" },
  partial: { label: "Partial", tone: "accent" },
};

function currentBusinessQuery() {
  const token = localStorage.getItem("kede_token");
  const businessId = localStorage.getItem("kede_business_id");
  return token && businessId ? `business_id=${encodeURIComponent(businessId)}` : "demo=1";
}

function authHeaders() {
  const token = localStorage.getItem("kede_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export default function Invoices() {
  const [, navigate] = useLocation();
  const [filter, setFilter] = useState("all");
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [customerName, setCustomerName] = useState("");
  const [customerPhone, setCustomerPhone] = useState("");
  const [invoiceNumber, setInvoiceNumber] = useState(`INV-${Date.now().toString().slice(-6)}`);
  const [itemName, setItemName] = useState("WhatsApp order");
  const [quantity, setQuantity] = useState("1");
  const [unitPrice, setUnitPrice] = useState("45.00");
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const query = currentBusinessQuery();
      const [invoiceRes, customerRes] = await Promise.all([
        fetch(`/api/v1/invoices?${query}`, {
          headers: { Accept: "application/json", ...authHeaders() },
          credentials: "include",
        }),
        fetch(`/api/v1/customers?${query}`, {
          headers: { Accept: "application/json", ...authHeaders() },
          credentials: "include",
        }),
      ]);
      if (!invoiceRes.ok) throw new Error("Failed to load invoices");
      if (!customerRes.ok) throw new Error("Failed to load customers");
      setInvoices(await invoiceRes.json());
      setCustomers(await customerRes.json());
    } catch (err: any) {
      toast.error(err.message || "Failed to load invoices");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const rows = useMemo(
    () => (filter === "all" ? invoices : invoices.filter((d) => d.payment_status === filter)),
    [filter, invoices],
  );

  const totalDraftAmount = Number(quantity || 0) * Number(unitPrice || 0);

  const submitInvoice = async () => {
    if (!customerName.trim() || !invoiceNumber.trim() || !itemName.trim() || totalDraftAmount <= 0) {
      toast.error("Fill customer, invoice, item, quantity, and price first.");
      return;
    }

    setSubmitting(true);
    try {
      const query = currentBusinessQuery();
      const headers = {
        "Content-Type": "application/json",
        ...authHeaders(),
      };

      let customer = customers.find((entry) => entry.name.toLowerCase() === customerName.trim().toLowerCase());
      if (!customer) {
        const customerRes = await fetch(`/api/v1/customers?${query}`, {
          method: "POST",
          headers,
          credentials: "include",
          body: JSON.stringify({
            business_id: 1,
            name: customerName.trim(),
            phone: customerPhone.trim() || null,
          }),
        });
        if (!customerRes.ok) {
          const payload = await customerRes.json().catch(() => null);
          throw new Error(payload?.detail || "Failed to create customer");
        }
        customer = await customerRes.json();
      }

      const qty = Number(quantity);
      const price = Number(unitPrice);
      const invoiceRes = await fetch(`/api/v1/invoices?${query}`, {
        method: "POST",
        headers,
        credentials: "include",
        body: JSON.stringify({
          business_id: 1,
          customer_id: customer.id,
          invoice_number: invoiceNumber.trim(),
          items: [{ name: itemName.trim(), quantity: qty, unit_price: price }],
          subtotal: qty * price,
          tax: 0,
          total: qty * price,
          payment_method: "pending",
          payment_status: "pending",
          due_date: new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10),
        }),
      });
      if (!invoiceRes.ok) {
        const payload = await invoiceRes.json().catch(() => null);
        throw new Error(payload?.detail || "Failed to create invoice");
      }
      const invoice = await invoiceRes.json();
      toast.success(`Invoice ${invoice.invoice_number} created`);
      setShowForm(false);
      setCustomerName("");
      setCustomerPhone("");
      setInvoiceNumber(`INV-${Date.now().toString().slice(-6)}`);
      setItemName("WhatsApp order");
      setQuantity("1");
      setUnitPrice("45.00");
      await load();
      navigate(`/invoices/${invoice.id}`);
    } catch (err: any) {
      toast.error(err.message || "Failed to create invoice");
    } finally {
      setSubmitting(false);
    }
  };

  const deleteInvoice = async (invoiceId: number) => {
    setDeletingId(invoiceId);
    try {
      const res = await fetch(`/api/v1/invoices/${invoiceId}?${currentBusinessQuery()}`, {
        method: "DELETE",
        headers: authHeaders(),
        credentials: "include",
      });
      if (!res.ok) {
        const payload = await res.json().catch(() => null);
        throw new Error(payload?.detail || "Failed to delete invoice");
      }
      toast.success("Invoice removed");
      await load();
    } catch (err: any) {
      toast.error(err.message || "Failed to delete invoice");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <DashboardLayout
      title="Invoices"
      subtitle="All invoices live here. Review only shows invoices that already have payment proofs waiting."
      action={
        <button
          onClick={() => setShowForm((value) => !value)}
          className="inline-flex items-center gap-2 rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-accent-foreground transition-transform hover:-translate-y-0.5 active:scale-[0.97]"
        >
          <Plus className="h-4 w-4" /> {showForm ? "Close form" : "New invoice"}
        </button>
      }
    >
      {showForm && (
        <Panel title="Create invoice">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block">
              <span className="mb-2 block text-[13px] font-semibold text-muted-foreground">Customer name</span>
              <input
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm outline-none focus:border-accent focus:ring-4 focus:ring-accent/10"
                placeholder="Ali Bin Abu"
              />
            </label>
            <label className="block">
              <span className="mb-2 block text-[13px] font-semibold text-muted-foreground">Phone</span>
              <input
                value={customerPhone}
                onChange={(e) => setCustomerPhone(e.target.value)}
                className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm outline-none focus:border-accent focus:ring-4 focus:ring-accent/10"
                placeholder="60123456789"
              />
            </label>
            <label className="block">
              <span className="mb-2 block text-[13px] font-semibold text-muted-foreground">Invoice number</span>
              <input
                value={invoiceNumber}
                onChange={(e) => setInvoiceNumber(e.target.value)}
                className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm outline-none focus:border-accent focus:ring-4 focus:ring-accent/10"
              />
            </label>
            <label className="block">
              <span className="mb-2 block text-[13px] font-semibold text-muted-foreground">Item</span>
              <input
                value={itemName}
                onChange={(e) => setItemName(e.target.value)}
                className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm outline-none focus:border-accent focus:ring-4 focus:ring-accent/10"
              />
            </label>
            <label className="block">
              <span className="mb-2 block text-[13px] font-semibold text-muted-foreground">Quantity</span>
              <input
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                type="number"
                min="1"
                className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm outline-none focus:border-accent focus:ring-4 focus:ring-accent/10"
              />
            </label>
            <label className="block">
              <span className="mb-2 block text-[13px] font-semibold text-muted-foreground">Unit price (RM)</span>
              <input
                value={unitPrice}
                onChange={(e) => setUnitPrice(e.target.value)}
                type="number"
                min="0"
                step="0.01"
                className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm outline-none focus:border-accent focus:ring-4 focus:ring-accent/10"
              />
            </label>
          </div>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <div className="text-sm text-muted-foreground">
              Draft total: <span className="font-medium text-foreground">{currency(totalDraftAmount || 0)}</span>
            </div>
            <button
              onClick={submitInvoice}
              disabled={submitting}
              className="inline-flex items-center gap-2 rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-accent-foreground transition-transform hover:-translate-y-0.5 active:scale-[0.97] disabled:opacity-60"
            >
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              {submitting ? "Creating..." : "Create invoice"}
            </button>
          </div>
        </Panel>
      )}

      <div className="mb-5 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`rounded-full border px-4 py-1.5 text-sm font-medium transition-colors ${
              filter === f ? "border-accent bg-accent/8 text-foreground" : "border-border text-muted-foreground hover:bg-secondary"
            }`}
          >
            {f === "all" ? "All" : STATUS_MAP[f]?.label || f}
          </button>
        ))}
      </div>

      <Panel>
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-accent" />
          </div>
        ) : rows.length === 0 ? (
          <div className="py-12 text-center text-sm text-muted-foreground">No invoices yet. Create your first invoice to get started.</div>
        ) : (
          <div className="space-y-3">
            {rows.map((r) => {
              const status = STATUS_MAP[r.payment_status] || { label: r.payment_status, tone: "accent" as const };
              return (
                <ListRow
                  key={r.id}
                  title={r.invoice_number}
                  subtitle={`Customer: ${r.customer_name || "Unknown"}${Number(r.pending_proof_count || 0) > 0 ? " · Proof waiting in Review" : ""}`}
                  amount={currency(r.total)}
                  badge={<Badge tone={status.tone}>{status.label}</Badge>}
                  onClick={() => navigate(`/invoices/${r.id}`)}
                  trailing={
                    <div className="flex items-center gap-2">
                      <a
                        href={`/api/v1/invoices/${r.id}/receipt?${currentBusinessQuery()}`}
                        onClick={(event) => event.stopPropagation()}
                        className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-accent/40 hover:text-foreground"
                      >
                        <Download className="h-3.5 w-3.5" />
                        PDF
                      </a>
                      <button
                        onClick={(event) => {
                          event.stopPropagation();
                          void deleteInvoice(r.id);
                        }}
                        disabled={deletingId === r.id}
                        className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-red-300 hover:text-red-700 disabled:opacity-50"
                      >
                        {deletingId === r.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                        Remove
                      </button>
                    </div>
                  }
                />
              );
            })}
          </div>
        )}
      </Panel>
    </DashboardLayout>
  );
}
