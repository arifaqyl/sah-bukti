import { useState } from "react";
import { DashboardLayout } from "@/components/DashboardLayout";
import { Panel } from "@/components/sahbukti-ui";
import { useAuth } from "@/contexts/AuthContext";
import { ACCENT_OPTIONS, SHOP_TYPES, ShopType, applyAccent } from "@/lib/sahbukti";
import { Check } from "lucide-react";
import { toast } from "sonner";

export default function Profile() {
  const { user, signIn } = useAuth();
  const [displayName, setDisplayName] = useState(user?.display_name || "");
  const [shopName, setShopName] = useState(user?.business_name || "");
  const [shopType, setShopType] = useState<ShopType>(user?.shop_type || SHOP_TYPES[0]);
  const [accent, setAccent] = useState(user?.accent || ACCENT_OPTIONS[0].value);

  const save = () => {
    signIn({ display_name: displayName, business_name: shopName, shop_type: shopType, accent });
    toast.success("Workspace updated");
  };

  return (
    <DashboardLayout title="Workspace settings" subtitle="Update how Sah.Bukti greets you and looks.">
      <div className="grid max-w-3xl gap-5">
        <Panel title="Details">
          <div className="grid gap-5 sm:grid-cols-2">
            <label className="block">
              <span className="mb-2 block text-[13px] font-semibold text-muted-foreground">Your name</span>
              <input
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm outline-none transition-all focus:border-accent focus:ring-4 focus:ring-accent/10"
              />
            </label>
            <label className="block">
              <span className="mb-2 block text-[13px] font-semibold text-muted-foreground">Shop name</span>
              <input
                value={shopName}
                onChange={(e) => setShopName(e.target.value)}
                className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm outline-none transition-all focus:border-accent focus:ring-4 focus:ring-accent/10"
              />
            </label>
          </div>
          <div className="mt-5">
            <span className="mb-2 block text-[13px] font-semibold text-muted-foreground">Shop type</span>
            <div className="flex flex-wrap gap-2.5">
              {SHOP_TYPES.map((t) => (
                <button
                  key={t}
                  onClick={() => setShopType(t)}
                  className={`rounded-xl border px-4 py-2.5 text-sm font-medium transition-all ${
                    shopType === t ? "border-accent bg-accent/8 text-foreground" : "border-border bg-background text-muted-foreground hover:border-accent/40"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
        </Panel>

        <Panel title="Accent color">
          <p className="mb-4 text-sm text-muted-foreground">Sets the live accent across your whole workspace.</p>
          <div className="flex flex-wrap gap-3">
            {ACCENT_OPTIONS.map((a) => (
              <button
                key={a.value}
                onClick={() => { setAccent(a.value); applyAccent(a.value); }}
                className="flex h-12 w-12 items-center justify-center rounded-full border-2 transition-transform hover:scale-105"
                style={{ background: a.value, borderColor: accent === a.value ? "var(--foreground)" : "transparent" }}
                title={a.name}
              >
                {accent === a.value && <Check className="h-5 w-5 text-white" />}
              </button>
            ))}
          </div>
        </Panel>

        <div>
          <button
            onClick={save}
            className="inline-flex items-center gap-2 rounded-full bg-foreground px-7 py-3 text-sm font-medium text-background transition-transform hover:-translate-y-0.5 active:scale-[0.98]"
          >
            Save changes
          </button>
        </div>
      </div>
    </DashboardLayout>
  );
}
