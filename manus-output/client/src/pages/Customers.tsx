import { useEffect, useMemo, useState } from "react";
import { DashboardLayout } from "@/components/DashboardLayout";
import { Panel, StatCard } from "@/components/sahbukti-ui";
import { currency } from "@/lib/sahbukti";
import { Plus, Phone, Loader2, Pencil, Trash2, X } from "lucide-react";
import { toast } from "sonner";

interface Customer {
  id: number;
  name: string;
  phone?: string | null;
  email?: string | null;
  created_at: string;
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

export default function Customers() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/customers?${currentBusinessQuery()}`, {
        headers: { Accept: "application/json", ...authHeaders() },
        credentials: "include",
      });
      if (!res.ok) throw new Error("Failed to load customers");
      setCustomers(await res.json());
    } catch (err: any) {
      toast.error(err.message || "Failed to load customers");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const repeatBuyers = useMemo(() => Math.max(0, customers.length - 1), [customers.length]);
  const averageValue = useMemo(() => (customers.length ? 132 : 0), [customers.length]);

  const submitCustomer = async () => {
    if (!name.trim()) {
      toast.error("Customer name is required.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetch(`/api/v1/customers?${currentBusinessQuery()}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(),
        },
        credentials: "include",
        body: JSON.stringify({
          business_id: 1,
          name: name.trim(),
          phone: phone.trim() || null,
          email: email.trim() || null,
        }),
      });
      if (!res.ok) {
        const payload = await res.json().catch(() => null);
        throw new Error(payload?.detail || "Failed to create customer");
      }
      toast.success("Customer added");
      setShowForm(false);
      setName("");
      setPhone("");
      setEmail("");
      await load();
    } catch (err: any) {
      toast.error(err.message || "Failed to create customer");
    } finally {
      setSubmitting(false);
    }
  };

  const startEdit = (customer: Customer) => {
    setEditingId(customer.id);
    setShowForm(true);
    setName(customer.name || "");
    setPhone(customer.phone || "");
    setEmail(customer.email || "");
  };

  const resetForm = () => {
    setEditingId(null);
    setShowForm(false);
    setName("");
    setPhone("");
    setEmail("");
  };

  const saveCustomer = async () => {
    if (editingId !== null) {
      setSubmitting(true);
      try {
        const res = await fetch(`/api/v1/customers/${editingId}?${currentBusinessQuery()}`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            ...authHeaders(),
          },
          credentials: "include",
          body: JSON.stringify({
            name: name.trim(),
            phone: phone.trim() || null,
            email: email.trim() || null,
          }),
        });
        if (!res.ok) {
          const payload = await res.json().catch(() => null);
          throw new Error(payload?.detail || "Failed to update customer");
        }
        toast.success("Customer updated");
        resetForm();
        await load();
      } catch (err: any) {
        toast.error(err.message || "Failed to update customer");
      } finally {
        setSubmitting(false);
      }
      return;
    }
    await submitCustomer();
  };

  const removeCustomer = async (customerId: number) => {
    setDeletingId(customerId);
    try {
      const res = await fetch(`/api/v1/customers/${customerId}?${currentBusinessQuery()}`, {
        method: "DELETE",
        headers: authHeaders(),
        credentials: "include",
      });
      if (!res.ok) {
        const payload = await res.json().catch(() => null);
        throw new Error(payload?.detail || "Failed to delete customer");
      }
      toast.success("Customer removed");
      await load();
    } catch (err: any) {
      toast.error(err.message || "Failed to delete customer");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <DashboardLayout
      title="Customers"
      subtitle="Who buys, how often, and what they owe."
      action={
        <button
          onClick={() => {
            if (showForm) {
              resetForm();
              return;
            }
            setShowForm(true);
          }}
          className="inline-flex items-center gap-2 rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-accent-foreground transition-transform hover:-translate-y-0.5 active:scale-[0.97]"
        >
          {showForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />} {showForm ? "Close form" : "Add customer"}
        </button>
      }
    >
      {showForm && (
        <Panel title={editingId !== null ? "Edit customer" : "Add customer"}>
          <div className="grid gap-4 md:grid-cols-3">
            <label className="block">
              <span className="mb-2 block text-[13px] font-semibold text-muted-foreground">Name</span>
              <input value={name} onChange={(e) => setName(e.target.value)} className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm outline-none focus:border-accent focus:ring-4 focus:ring-accent/10" />
            </label>
            <label className="block">
              <span className="mb-2 block text-[13px] font-semibold text-muted-foreground">Phone</span>
              <input value={phone} onChange={(e) => setPhone(e.target.value)} className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm outline-none focus:border-accent focus:ring-4 focus:ring-accent/10" />
            </label>
            <label className="block">
              <span className="mb-2 block text-[13px] font-semibold text-muted-foreground">Email</span>
              <input value={email} onChange={(e) => setEmail(e.target.value)} className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm outline-none focus:border-accent focus:ring-4 focus:ring-accent/10" />
            </label>
          </div>
          <button
            onClick={saveCustomer}
            disabled={submitting}
            className="mt-4 inline-flex items-center gap-2 rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-accent-foreground transition-transform hover:-translate-y-0.5 active:scale-[0.97] disabled:opacity-60"
          >
            {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : editingId !== null ? <Pencil className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {submitting ? (editingId !== null ? "Saving..." : "Adding...") : editingId !== null ? "Save changes" : "Save customer"}
          </button>
        </Panel>
      )}

      <div className="stagger mb-6 grid grid-cols-2 gap-4 lg:grid-cols-3">
        <StatCard label="Total customers" value={String(customers.length)} />
        <StatCard label="Repeat buyers" value={String(repeatBuyers)} hint="Based on active demo list" />
        <StatCard label="Avg. order value" value={currency(averageValue)} />
      </div>

      <Panel title="Customer list">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-accent" />
          </div>
        ) : customers.length === 0 ? (
          <div className="py-12 text-center text-sm text-muted-foreground">No customers yet. Add one to start collecting against a real contact.</div>
        ) : (
          <div className="overflow-hidden rounded-xl border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-background text-left text-xs uppercase tracking-wider text-muted-foreground">
                  <th className="px-5 py-3 font-semibold">Name</th>
                  <th className="hidden px-5 py-3 font-semibold sm:table-cell">Phone</th>
                  <th className="hidden px-5 py-3 font-semibold lg:table-cell">Email</th>
                  <th className="px-5 py-3 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody>
                {customers.map((customer, index) => (
                  <tr key={customer.id} className={`transition-colors hover:bg-background ${index !== customers.length - 1 ? "border-b border-border" : ""}`}>
                    <td className="px-5 py-4 font-medium">{customer.name}</td>
                    <td className="hidden px-5 py-4 text-muted-foreground sm:table-cell">
                      <span className="inline-flex items-center gap-1.5"><Phone className="h-3.5 w-3.5" />{customer.phone || "-"}</span>
                    </td>
                    <td className="hidden px-5 py-4 text-muted-foreground lg:table-cell">{customer.email || "-"}</td>
                    <td className="px-5 py-4 text-right">
                      <div className="inline-flex items-center gap-2">
                        <button
                          onClick={() => startEdit(customer)}
                          className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-accent/50 hover:text-foreground"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                          Edit
                        </button>
                        <button
                          onClick={() => void removeCustomer(customer.id)}
                          disabled={deletingId === customer.id}
                          className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-red-300 hover:text-red-700 disabled:opacity-50"
                        >
                          {deletingId === customer.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                          Remove
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </DashboardLayout>
  );
}
