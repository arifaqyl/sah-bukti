import { useEffect, useMemo, useState } from "react";
import { DashboardLayout } from "@/components/DashboardLayout";
import { Panel, Badge, StatCard } from "@/components/sahbukti-ui";
import { currency } from "@/lib/sahbukti";
import { Plus, Loader2, Pencil, Trash2, X } from "lucide-react";
import { toast } from "sonner";

interface Ingredient {
  id: number;
  name: string;
  unit: string;
  current_stock: number;
  reorder_point: number;
  supplier?: string | null;
  notes?: string | null;
}

interface SupplierGroup {
  supplier: string;
  ingredient_count: number;
  low_stock_count: number;
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

export default function Inventory() {
  const [items, setItems] = useState<Ingredient[]>([]);
  const [suppliers, setSuppliers] = useState<SupplierGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [name, setName] = useState("");
  const [unit, setUnit] = useState("pcs");
  const [currentStock, setCurrentStock] = useState("10");
  const [reorderPoint, setReorderPoint] = useState("5");
  const [supplier, setSupplier] = useState("");
  const [notes, setNotes] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const query = currentBusinessQuery();
      const [itemRes, supplierRes] = await Promise.all([
        fetch(`/api/v1/inventory/ingredients?${query}`, {
          headers: { Accept: "application/json", ...authHeaders() },
          credentials: "include",
        }),
        fetch(`/api/v1/inventory/suppliers?${query}`, {
          headers: { Accept: "application/json", ...authHeaders() },
          credentials: "include",
        }),
      ]);
      if (!itemRes.ok) throw new Error("Failed to load inventory");
      if (!supplierRes.ok) throw new Error("Failed to load suppliers");
      setItems(await itemRes.json());
      const supplierPayload = await supplierRes.json();
      setSuppliers(supplierPayload.suppliers || []);
    } catch (err: any) {
      toast.error(err.message || "Failed to load inventory");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const lowStock = useMemo(
    () => items.filter((item) => Number(item.current_stock) <= Number(item.reorder_point)).length,
    [items],
  );

  const submitIngredient = async () => {
    if (!name.trim()) {
      toast.error("Item name is required.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetch(`/api/v1/inventory/ingredients?${currentBusinessQuery()}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(),
        },
        credentials: "include",
        body: JSON.stringify({
          business_id: 1,
          name: name.trim(),
          unit: unit.trim() || "pcs",
          current_stock: Number(currentStock),
          reorder_point: Number(reorderPoint),
          supplier: supplier.trim() || null,
          notes: notes.trim() || null,
        }),
      });
      if (!res.ok) {
        const payload = await res.json().catch(() => null);
        throw new Error(payload?.detail || "Failed to create item");
      }
      toast.success("Inventory item added");
      setShowForm(false);
      setName("");
      setUnit("pcs");
      setCurrentStock("10");
      setReorderPoint("5");
      setSupplier("");
      setNotes("");
      await load();
    } catch (err: any) {
      toast.error(err.message || "Failed to create item");
    } finally {
      setSubmitting(false);
    }
  };

  const resetForm = () => {
    setEditingId(null);
    setShowForm(false);
    setName("");
    setUnit("pcs");
    setCurrentStock("10");
    setReorderPoint("5");
    setSupplier("");
    setNotes("");
  };

  const startEdit = (item: Ingredient) => {
    setEditingId(item.id);
    setShowForm(true);
    setName(item.name || "");
    setUnit(item.unit || "pcs");
    setCurrentStock(String(item.current_stock ?? 0));
    setReorderPoint(String(item.reorder_point ?? 0));
    setSupplier(item.supplier || "");
    setNotes(item.notes || "");
  };

  const saveIngredient = async () => {
    if (editingId !== null) {
      if (!name.trim()) {
        toast.error("Item name is required.");
        return;
      }
      setSubmitting(true);
      try {
        const res = await fetch(`/api/v1/inventory/ingredients/${editingId}?${currentBusinessQuery()}`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            ...authHeaders(),
          },
          credentials: "include",
          body: JSON.stringify({
            name: name.trim(),
            unit: unit.trim() || "pcs",
            current_stock: Number(currentStock),
            reorder_point: Number(reorderPoint),
            supplier: supplier.trim() || null,
            notes: notes.trim() || null,
          }),
        });
        if (!res.ok) {
          const payload = await res.json().catch(() => null);
          throw new Error(payload?.detail || "Failed to update item");
        }
        toast.success("Inventory item updated");
        resetForm();
        await load();
      } catch (err: any) {
        toast.error(err.message || "Failed to update item");
      } finally {
        setSubmitting(false);
      }
      return;
    }
    await submitIngredient();
  };

  const removeIngredient = async (ingredientId: number) => {
    setDeletingId(ingredientId);
    try {
      const res = await fetch(`/api/v1/inventory/ingredients/${ingredientId}?${currentBusinessQuery()}`, {
        method: "DELETE",
        headers: authHeaders(),
        credentials: "include",
      });
      if (!res.ok) {
        const payload = await res.json().catch(() => null);
        throw new Error(payload?.detail || "Failed to delete item");
      }
      toast.success("Inventory item removed");
      await load();
    } catch (err: any) {
      toast.error(err.message || "Failed to delete item");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <DashboardLayout
      title="Inventory"
      subtitle="Stock pressure and supplier notes, side by side."
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
          {showForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />} {showForm ? "Close form" : "Add item"}
        </button>
      }
    >
      {showForm && (
        <Panel title={editingId !== null ? "Edit inventory item" : "Add inventory item"}>
          <div className="grid gap-4 md:grid-cols-3">
            <label className="block">
              <span className="mb-2 block text-[13px] font-semibold text-muted-foreground">Item name</span>
              <input value={name} onChange={(e) => setName(e.target.value)} className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm outline-none focus:border-accent focus:ring-4 focus:ring-accent/10" />
            </label>
            <label className="block">
              <span className="mb-2 block text-[13px] font-semibold text-muted-foreground">Unit</span>
              <input value={unit} onChange={(e) => setUnit(e.target.value)} className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm outline-none focus:border-accent focus:ring-4 focus:ring-accent/10" />
            </label>
            <label className="block">
              <span className="mb-2 block text-[13px] font-semibold text-muted-foreground">Supplier</span>
              <input value={supplier} onChange={(e) => setSupplier(e.target.value)} className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm outline-none focus:border-accent focus:ring-4 focus:ring-accent/10" />
            </label>
            <label className="block">
              <span className="mb-2 block text-[13px] font-semibold text-muted-foreground">Current stock</span>
              <input value={currentStock} onChange={(e) => setCurrentStock(e.target.value)} type="number" min="0" className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm outline-none focus:border-accent focus:ring-4 focus:ring-accent/10" />
            </label>
            <label className="block">
              <span className="mb-2 block text-[13px] font-semibold text-muted-foreground">Reorder point</span>
              <input value={reorderPoint} onChange={(e) => setReorderPoint(e.target.value)} type="number" min="0" className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm outline-none focus:border-accent focus:ring-4 focus:ring-accent/10" />
            </label>
            <label className="block md:col-span-3">
              <span className="mb-2 block text-[13px] font-semibold text-muted-foreground">Notes</span>
              <input value={notes} onChange={(e) => setNotes(e.target.value)} className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm outline-none focus:border-accent focus:ring-4 focus:ring-accent/10" />
            </label>
          </div>
          <button
            onClick={saveIngredient}
            disabled={submitting}
            className="mt-4 inline-flex items-center gap-2 rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-accent-foreground transition-transform hover:-translate-y-0.5 active:scale-[0.97] disabled:opacity-60"
          >
            {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : editingId !== null ? <Pencil className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {submitting ? "Saving..." : editingId !== null ? "Save changes" : "Save item"}
          </button>
        </Panel>
      )}

      <div className="stagger mb-6 grid grid-cols-2 gap-4 lg:grid-cols-3">
        <StatCard label="Ingredients" value={String(items.length)} />
        <StatCard label="Low stock" value={String(lowStock)} hint="Needs reordering" />
        <StatCard label="Suppliers" value={String(suppliers.length)} />
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-accent" />
        </div>
      ) : (
        <div className="grid gap-5 lg:grid-cols-[1.7fr_1fr]">
          <Panel title="Stock levels">
            <div className="space-y-3">
              {items.map((item) => {
                const tone =
                  Number(item.current_stock) <= Number(item.reorder_point)
                    ? "danger"
                    : Number(item.current_stock) <= Number(item.reorder_point) * 1.5
                      ? "warn"
                      : "success";
                const label = tone === "danger" ? "Low" : tone === "warn" ? "Watch" : "Healthy";
                return (
                  <div key={item.id} className="rounded-xl border border-border bg-card px-5 py-4">
                    <div className="flex items-center justify-between">
                      <div className="font-medium">{item.name}</div>
                      <Badge tone={tone}>{label}</Badge>
                    </div>
                    <div className="mt-3 h-2 overflow-hidden rounded-full bg-background">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${Math.min(100, (Number(item.current_stock) / Math.max(Number(item.reorder_point), 1)) * 100)}%`,
                          background: tone === "danger" ? "oklch(0.5 0.15 25)" : tone === "warn" ? "var(--clay)" : "oklch(0.5 0.09 155)",
                        }}
                      />
                    </div>
                    <div className="mt-2 flex items-center justify-between gap-3 text-xs text-muted-foreground">
                      <span>{item.current_stock} {item.unit} in stock · par {item.reorder_point}</span>
                      <div className="flex items-center gap-2">
                      <span>{item.supplier || "No supplier"}</span>
                        <button
                          onClick={() => startEdit(item)}
                          className="inline-flex items-center gap-1 rounded-full border border-border px-2.5 py-1 text-[11px] font-medium text-muted-foreground transition-colors hover:border-accent/50 hover:text-foreground"
                        >
                          <Pencil className="h-3 w-3" />
                          Edit
                        </button>
                        <button
                          onClick={() => void removeIngredient(item.id)}
                          disabled={deletingId === item.id}
                          className="inline-flex items-center gap-1 rounded-full border border-border px-2.5 py-1 text-[11px] font-medium text-muted-foreground transition-colors hover:border-red-300 hover:text-red-700 disabled:opacity-50"
                        >
                          {deletingId === item.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />}
                          Remove
                        </button>
                      </div>
                    </div>
                    {item.notes && <div className="mt-2 text-xs text-muted-foreground">{item.notes}</div>}
                  </div>
                );
              })}
              {items.length === 0 && <div className="py-10 text-center text-sm text-muted-foreground">No inventory items yet. Add one to populate low-stock monitoring.</div>}
            </div>
          </Panel>

          <Panel title="Supplier notes">
            <div className="space-y-3 text-sm">
              {suppliers.map((group) => (
                <div key={group.supplier} className="rounded-xl border border-border bg-background p-4">
                  <div className="font-medium">{group.supplier}</div>
                  <p className="mt-1 text-muted-foreground">
                    {group.ingredient_count} tracked items · {group.low_stock_count} low-stock alerts
                  </p>
                </div>
              ))}
              {suppliers.length === 0 && <div className="rounded-xl border border-border bg-background p-4 text-muted-foreground">No supplier notes yet. Add inventory items with supplier names.</div>}
            </div>
          </Panel>
        </div>
      )}
    </DashboardLayout>
  );
}
