import { useState } from "react";
import { useLocation } from "wouter";
import { Logo } from "@/components/Logo";
import { useAuth } from "@/contexts/AuthContext";
import { SHOP_TYPES, ACCENT_OPTIONS, DEFAULT_ACCENT, ShopType, applyAccent } from "@/lib/sahbukti";
import { ArrowRight, ArrowLeft, Check } from "lucide-react";
import { toast } from "sonner";

type Mode = "login" | "signup";

function Aside() {
  return (
    <aside
      className="relative hidden flex-col justify-between p-12 text-background lg:flex"
      style={{ background: "var(--foreground)" }}
    >
      <div
        className="absolute inset-0 opacity-30"
        style={{ background: "radial-gradient(circle at 80% 10%, var(--clay), transparent 55%)" }}
      />
      <div className="relative">
        <Logo size={34} />
      </div>
      <div className="relative">
        <h2 className="text-background" style={{ fontSize: "2.4rem", lineHeight: 1.12 }}>
          Proof before payment. Clean books after.
        </h2>
        <p className="mt-5 max-w-sm leading-relaxed opacity-75">
          Sah.Bukti ingests WhatsApp, CSV, receipts and payment evidence — then keeps every
          ledger mutation behind owner approval.
        </p>
        <div className="mt-10 grid grid-cols-2 gap-3">
          {[
            ["0", "auto-paid invoices"],
            ["1", "approval gate"],
            ["4", "evidence sources"],
            ["100%", "shop-scoped"],
          ].map(([v, l]) => (
            <div key={l} className="rounded-xl border border-white/10 bg-white/5 p-4">
              <div className="font-serif text-2xl" style={{ color: "var(--clay)" }}>{v}</div>
              <div className="mt-0.5 text-xs opacity-70">{l}</div>
            </div>
          ))}
        </div>
      </div>
      <p className="relative text-xs opacity-60">Built for real shop workflows. No AI slop.</p>
    </aside>
  );
}

function Field({
  label, type = "text", value, onChange, placeholder, required,
}: {
  label: string; type?: string; value: string;
  onChange: (v: string) => void; placeholder?: string; required?: boolean;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-[13px] font-semibold text-muted-foreground">{label}</span>
      <input
        type={type}
        value={value}
        required={required}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-xl border border-input bg-background px-4 py-3 text-[15px] outline-none transition-all focus:border-accent focus:bg-card focus:ring-4 focus:ring-accent/10"
      />
    </label>
  );
}

export default function Auth() {
  const [, navigate] = useLocation();
  const { signIn } = useAuth();
  const [mode, setMode] = useState<Mode>("signup");

  // login fields
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // wizard
  const [step, setStep] = useState(0);
  const [displayName, setDisplayName] = useState("");
  const [shopName, setShopName] = useState("");
  const [shopType, setShopType] = useState<ShopType | null>(null);
  const [accent, setAccent] = useState(DEFAULT_ACCENT);

  const doLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;
    signIn({ display_name: email.split("@")[0] || "Owner", business_name: "My Shop" });
    toast.success("Welcome back to Sah.Bukti");
    navigate("/dashboard");
  };

  const finish = (chosenAccent: string = accent) => {
    signIn({ display_name: displayName, business_name: shopName, shop_type: shopType!, accent: chosenAccent });
    toast.success("Workspace created — selamat datang!");
    navigate("/dashboard");
  };

  const next = () => {
    if (step === 0 && !displayName.trim()) return toast.error("Tell us your name first");
    if (step === 1 && !shopName.trim()) return toast.error("Your shop needs a name");
    if (step === 2 && !shopType) return toast.error("Pick a shop type");
    if (step < 3) { setStep(step + 1); return; }
    finish();
  };

  const STEP_LABELS = ["Your name", "Shop name", "Shop type", "Accent"];

  return (
    <div className="grid min-h-screen lg:grid-cols-[0.9fr_1.1fr]">
      <Aside />
      <main className="page-fade flex items-center justify-center bg-background px-5 py-10">
        <div className="w-full max-w-md">
          <div className="mb-8 lg:hidden"><Logo /></div>

          <div className="rounded-[1.6rem] border border-border bg-card p-8 shadow-[0_8px_28px_rgba(26,26,26,0.06)]">
            {/* tabs */}
            <div className="mb-7 flex gap-1.5 rounded-full bg-background p-1.5">
              {(["login", "signup"] as Mode[]).map((m) => (
                <button
                  key={m}
                  onClick={() => { setMode(m); setStep(0); }}
                  className={`flex-1 rounded-full py-2.5 text-sm font-semibold capitalize transition-all ${
                    mode === m ? "bg-card text-foreground shadow-sm" : "text-muted-foreground"
                  }`}
                >
                  {m === "login" ? "Log in" : "Sign up"}
                </button>
              ))}
            </div>

            {mode === "login" ? (
              <form onSubmit={doLogin} className="space-y-5">
                <div>
                  <h3 className="text-2xl">Welcome back</h3>
                  <p className="mt-1 text-sm text-muted-foreground">Log in to your Sah.Bukti workspace.</p>
                </div>
                <Field label="Email" type="email" value={email} onChange={setEmail} placeholder="owner@example.com" required />
                <Field label="Password" type="password" value={password} onChange={setPassword} placeholder="••••••••" required />
                <button type="submit" className="w-full rounded-full bg-foreground py-3.5 text-sm font-medium text-background transition-transform hover:-translate-y-0.5 active:scale-[0.98]">
                  Log in to Sah.Bukti
                </button>
                <p className="text-center text-xs text-muted-foreground">
                  Demo: any email + password works.
                </p>
              </form>
            ) : (
              <div>
                <div className="mb-6">
                  <div className="overline mb-2">Step {step + 1} of 4 · {STEP_LABELS[step]}</div>
                  <div className="flex gap-1.5">
                    {STEP_LABELS.map((_, i) => (
                      <div key={i} className="h-1.5 flex-1 overflow-hidden rounded-full bg-background">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{ width: i <= step ? "100%" : "0%", background: "var(--clay)" }}
                        />
                      </div>
                    ))}
                  </div>
                </div>

                <div className="min-h-[180px]">
                  {step === 0 && (
                    <div className="page-fade space-y-2">
                      <h3 className="text-2xl">What's your name?</h3>
                      <p className="mb-4 text-sm text-muted-foreground">So Sah.Bukti can greet you properly.</p>
                      <Field label="Your name" value={displayName} onChange={setDisplayName} placeholder="Aisyah" />
                    </div>
                  )}
                  {step === 1 && (
                    <div className="page-fade space-y-2">
                      <h3 className="text-2xl">Name your shop</h3>
                      <p className="mb-4 text-sm text-muted-foreground">This becomes your workspace.</p>
                      <Field label="Shop name" value={shopName} onChange={setShopName} placeholder="Warung Seri Pagi" />
                    </div>
                  )}
                  {step === 2 && (
                    <div className="page-fade">
                      <h3 className="text-2xl">What kind of shop?</h3>
                      <p className="mb-4 text-sm text-muted-foreground">We tune defaults to your trade.</p>
                      <div className="grid grid-cols-2 gap-2.5">
                        {SHOP_TYPES.map((t) => (
                          <button
                            key={t}
                            onClick={() => setShopType(t)}
                            className={`rounded-xl border p-3.5 text-left text-sm font-medium transition-all ${
                              shopType === t
                                ? "border-accent bg-accent/8 text-foreground"
                                : "border-border bg-background text-muted-foreground hover:border-accent/40"
                            }`}
                          >
                            {t}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  {step === 3 && (
                    <div className="page-fade">
                      <h3 className="text-2xl">Pick your accent</h3>
                      <p className="mb-4 text-sm text-muted-foreground">
                        Optional — colours your dashboard. Clay is the default, or keep it and skip.
                      </p>
                      <div className="flex flex-wrap gap-3">
                        {ACCENT_OPTIONS.map((a) => (
                          <button
                            key={a.value}
                            onClick={() => { setAccent(a.value); applyAccent(a.value); }}
                            className="flex h-12 w-12 items-center justify-center rounded-full border-2 transition-transform hover:scale-105"
                            style={{
                              background: a.value,
                              borderColor: accent === a.value ? "var(--foreground)" : "transparent",
                            }}
                            title={a.name}
                            aria-label={`Accent: ${a.name}`}
                          >
                            {accent === a.value && <Check className="h-5 w-5 text-white" />}
                          </button>
                        ))}
                      </div>
                      <div className="mt-5 flex items-center gap-2 text-sm">
                        <span
                          className="inline-block h-4 w-4 rounded-full border border-border"
                          style={{ background: accent }}
                        />
                        <span className="text-muted-foreground">
                          Selected: {ACCENT_OPTIONS.find((o) => o.value === accent)?.name ?? "Clay"}
                        </span>
                        <button
                          type="button"
                          onClick={() => { setAccent(DEFAULT_ACCENT); applyAccent(DEFAULT_ACCENT); finish(DEFAULT_ACCENT); }}
                          className="ml-auto rounded-full px-3 py-1.5 text-xs font-medium text-muted-foreground underline-offset-2 transition-colors hover:text-foreground hover:underline"
                        >
                          Skip — keep clay
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                <div className="mt-6 flex items-center gap-3">
                  {step > 0 && (
                    <button
                      onClick={() => setStep(step - 1)}
                      className="inline-flex items-center gap-1.5 rounded-full border border-border px-4 py-3 text-sm font-medium transition-colors hover:bg-secondary"
                    >
                      <ArrowLeft className="h-4 w-4" /> Back
                    </button>
                  )}
                  <button
                    onClick={next}
                    className="inline-flex flex-1 items-center justify-center gap-2 rounded-full bg-accent py-3.5 text-sm font-medium text-accent-foreground transition-transform hover:-translate-y-0.5 active:scale-[0.98]"
                  >
                    {step < 3 ? "Continue" : "Create workspace"} <ArrowRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )}
          </div>
          <p className="mt-5 text-center text-xs text-muted-foreground">
            Evidence never auto-pays. Payment proofs stay reviewable until you approve.
          </p>
        </div>
      </main>
    </div>
  );
}
