/* ============================================================
 * Sah.Bukti — Setup guide / mini tutorial
 * "Paper & Ink" anti-slop build. Warm paper, clay accent (--accent),
 * Fraunces display + DM Sans body. Calm, handcrafted, step-driven.
 * ============================================================ */
import { DashboardLayout } from "@/components/DashboardLayout";
import { Panel, Badge } from "@/components/sahbukti-ui";
import { Link } from "wouter";
import { useState } from "react";
import { toast } from "sonner";
import {
  Check,
  MessageCircle,
  Inbox,
  CheckCircle2,
  FileText,
  Users,
  Boxes,
  CalendarCheck,
  Download,
  ChevronDown,
  Smartphone,
  QrCode,
  ClipboardPaste,
  ShieldCheck,
} from "lucide-react";

/* ---------- WhatsApp connect steps ---------- */
const WA_STEPS = [
  {
    icon: Smartphone,
    t: "Use private owner demo mode",
    d: "The public site stays safe. For private demos, the owner can run the connected WhatsApp agent separately and keep the public app read-only for visitors.",
  },
  {
    icon: QrCode,
    t: "Keep live linking off the public site",
    d: "QR linking is hidden here by default. That prevents strangers from seeing or touching your real WhatsApp session after you post the public URL.",
  },
  {
    icon: ClipboardPaste,
    t: "Paste a message for the product demo",
    d: "For public walkthroughs, paste an order or payment message into Evidence. Sah.Bukti turns it into a pending invoice or reviewable proof using the same backend flow.",
  },
  {
    icon: ShieldCheck,
    t: "Nothing posts without you",
    d: "Every extracted order or payment lands in Review first. Your ledger only changes after you approve. Evidence never auto-pays.",
  },
];

/* ---------- Feature tour ---------- */
type Tour = {
  key: string;
  label: string;
  icon: typeof Inbox;
  href: string;
  blurb: string;
  steps: string[];
};

const TOURS: Tour[] = [
  {
    key: "evidence",
    label: "Evidence",
    icon: Inbox,
    href: "/evidence",
    blurb: "Where raw shop chatter becomes structured records.",
    steps: [
      "Connect WhatsApp or paste a chat / CSV export.",
      "Sah.Bukti reads each message and detects menu orders, amounts, and payment intent.",
      "Detected items queue up for review — nothing touches your books yet.",
    ],
  },
  {
    key: "review",
    label: "Review",
    icon: CheckCircle2,
    href: "/review",
    blurb: "Your single approval gate. The heart of Sah.Bukti.",
    steps: [
      "Open a pending proof to see the original message and the matched amount.",
      "Tap Approve to post it to the ledger, or Reject to send it back.",
      "Approved proofs instantly update invoices, customers, and readiness.",
    ],
  },
  {
    key: "invoices",
    label: "Invoices",
    icon: FileText,
    href: "/invoices",
    blurb: "Clean, accountant-ready records of every sale.",
    steps: [
      "Create an invoice manually, or let an approved proof generate one.",
      "Track status: Paid, Unpaid, Partial, or Overdue at a glance.",
      "Open any invoice for a full evidence trail back to the original message.",
    ],
  },
  {
    key: "customers",
    label: "Customers",
    icon: Users,
    href: "/customers",
    blurb: "Know who buys, how often, and what they owe.",
    steps: [
      "Add the people you sell to most, or let evidence create them for you.",
      "See lifetime spend and outstanding balance per customer.",
      "Filter to find regulars or chase overdue balances.",
    ],
  },
  {
    key: "inventory",
    label: "Inventory",
    icon: Boxes,
    href: "/inventory",
    blurb: "Light stock notes — no barcode scanner required.",
    steps: [
      "List the items you sell and a reorder threshold.",
      "Low-stock items surface on your dashboard automatically.",
      "Adjust counts as evidence is approved or stock arrives.",
    ],
  },
  {
    key: "readiness",
    label: "Readiness",
    icon: CalendarCheck,
    href: "/readiness",
    blurb: "How close you are to a clean month-end handoff.",
    steps: [
      "A single percentage shows what's reviewed vs. still pending.",
      "Work the checklist down: clear the review queue, match payments.",
      "Hit a green month and your export is ready in one click.",
    ],
  },
  {
    key: "export",
    label: "Export",
    icon: Download,
    href: "/export",
    blurb: "Hand a tidy package to your accountant.",
    steps: [
      "Pick a month once readiness looks healthy.",
      "Generate a CSV or JSON package of reviewed records.",
      "Send it to your accountant — every line traces back to evidence.",
    ],
  },
];

/* ---------- Checklist ---------- */
const CHECKLIST = [
  { t: "Create your shop", d: "Name your workspace and pick an accent. Done at signup." },
  { t: "Connect WhatsApp", d: "Link the shop number or paste your first chat into Evidence." },
  { t: "Add your first customer", d: "Add someone you sell to often in Customers." },
  { t: "Review a payment proof", d: "Approve your first proof in Review to update the ledger." },
  { t: "Check readiness", d: "See how close you are to a clean month-end." },
  { t: "Export for your accountant", d: "Generate a CSV / JSON package when the month closes." },
];

/* ---------- FAQ ---------- */
const FAQ = [
  {
    q: "Will Sah.Bukti send messages or pay anything automatically?",
    a: "It can send focused operational replies like acknowledgements, reminders, and receipt messages. It never auto-pays and it never mutates your ledger without approval.",
  },
  {
    q: "Do I need to connect WhatsApp to use it?",
    a: "No — connecting is the fastest path, but you can paste a chat or CSV export in the Evidence screen and get the same structured records.",
  },
  {
    q: "Is my chat data shared with anyone?",
    a: "Your evidence stays scoped to your shop workspace. In this build the backend stores records in your Sah.Bukti workspace, and approvals remain the control point before any financial state changes.",
  },
  {
    q: "What if Sah.Bukti reads an amount wrong?",
    a: "That's exactly what Review is for. You see the original message beside the matched amount and can correct or reject before anything is recorded.",
  },
];

function FaqItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-xl border border-border bg-background">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-4 px-4 py-3.5 text-left"
      >
        <span className="font-medium">{q}</span>
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200 ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && <p className="px-4 pb-4 text-sm leading-relaxed text-muted-foreground">{a}</p>}
    </div>
  );
}

export default function Help() {
  const [done, setDone] = useState<number[]>([0]);
  const [activeTour, setActiveTour] = useState<string>(TOURS[0].key);
  const [waLoading, setWaLoading] = useState(false);
  const [waState, setWaState] = useState<any | null>(null);
  const [waQr, setWaQr] = useState<any | null>(null);
  const [demoLoading, setDemoLoading] = useState(false);
  const tour = TOURS.find((t) => t.key === activeTour)!;
  const TourIcon = tour.icon;

  const toggle = (i: number) =>
    setDone((d) => (d.includes(i) ? d.filter((x) => x !== i) : [...d, i]));

  const progress = Math.round((done.length / CHECKLIST.length) * 100);

  const checkWhatsApp = async () => {
    setWaLoading(true);
    try {
      const [sessionRes, qrRes] = await Promise.all([
        fetch("/api/v1/whatsapp/session?demo=1"),
        fetch("/api/v1/whatsapp/session/qr?demo=1"),
      ]);
      const session = await sessionRes.json();
      const qr = await qrRes.json();
      setWaState(session);
      setWaQr(qr);
      if ((session.engine?.state || "").toUpperCase() === "CONNECTED") {
        toast.success(`WhatsApp connected: ${session.me?.id || session.name}`);
      } else if (qr?.ok) {
        toast.success("QR code ready to scan.");
      } else {
        toast.error(qr?.detail || "WhatsApp session is not ready.");
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to check WhatsApp");
    } finally {
      setWaLoading(false);
    }
  };

  const seedDemo = async () => {
    setDemoLoading(true);
    try {
      const response = await fetch("/api/v1/demo/seed?demo=1", { method: "POST" });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail || `Demo seed failed (${response.status})`);
      }
      toast.success("Demo data loaded. Dashboard and Review are now populated.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Demo seed failed");
    } finally {
      setDemoLoading(false);
    }
  };

  return (
    <DashboardLayout
      title="Setup guide"
      subtitle="A five-minute tour: connect WhatsApp, then learn every screen."
    >
      <div className="grid gap-6">
        {/* ---- Connect WhatsApp ---- */}
        <Panel
          title="Connect WhatsApp"
          aside={<Badge tone="accent">Start here</Badge>}
        >
          <p className="-mt-2 mb-6 max-w-2xl text-sm leading-relaxed text-muted-foreground">
            Sah.Bukti can run a private WhatsApp assistant for the owner, but the public app demo stays safe by
            default. For public walkthroughs, use pasted messages and seeded data to show the same review flow.
          </p>

          <div className="grid gap-4 md:grid-cols-2">
            {WA_STEPS.map((s, i) => {
              const Icon = s.icon;
              return (
                <div
                  key={s.t}
                  className="flex gap-4 rounded-2xl border border-border bg-background p-5"
                >
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[var(--clay-soft)]">
                    <Icon className="h-5 w-5 text-accent" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-serif text-lg leading-none text-accent">{i + 1}</span>
                      <span className="font-medium">{s.t}</span>
                    </div>
                    <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{s.d}</p>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-6 flex flex-col items-start gap-3 rounded-2xl border border-dashed border-border bg-[var(--clay-soft)]/40 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <MessageCircle className="h-5 w-5 text-accent" />
              <div>
                <div className="font-medium">Ready to link the shop phone?</div>
                <div className="text-sm text-muted-foreground">
                  Private live demos can stay connected outside this public surface.
                </div>
              </div>
            </div>
            <div className="flex shrink-0 gap-2.5">
              <button
                onClick={checkWhatsApp}
                className="rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-white transition-transform active:scale-[0.97]"
              >
                {waLoading ? "Checking..." : "Check private connector status"}
              </button>
              <button
                onClick={seedDemo}
                className="rounded-full border border-border bg-card px-5 py-2.5 text-sm font-medium transition-colors hover:border-accent/50"
              >
                {demoLoading ? "Loading demo..." : "Load demo data"}
              </button>
              <Link
                href="/evidence"
                className="rounded-full border border-border bg-card px-5 py-2.5 text-sm font-medium transition-colors hover:border-accent/50"
              >
                Paste a chat
              </Link>
            </div>
          </div>
          {(waState || waQr) && (
            <div className="mt-4 rounded-2xl border border-border bg-background p-5">
              <div className="font-medium">WhatsApp link status</div>
              <div className="mt-1 text-sm text-muted-foreground">
                Session: {waState?.name || "default"} · Status: {waState?.status || waState?.engine?.state || "unknown"}
              </div>
              {waQr?.ok && waQr?.data && (
                <img
                  src={`data:${waQr.mimetype || "image/png"};base64,${waQr.data}`}
                  alt="WhatsApp QR"
                  className="mt-4 w-full max-w-[280px] rounded-2xl border border-border bg-white p-3"
                />
              )}
              {!waQr?.ok && (
                <div className="mt-3 text-sm text-muted-foreground">
                  {waQr?.connected ? "Private WhatsApp session already connected." : waQr?.detail}
                </div>
              )}
            </div>
          )}
        </Panel>

        {/* ---- Feature tour ---- */}
        <Panel title="Tour every screen">
          <div className="-mt-1 mb-5 flex flex-wrap gap-2">
            {TOURS.map((t) => {
              const Icon = t.icon;
              const active = t.key === activeTour;
              return (
                <button
                  key={t.key}
                  onClick={() => setActiveTour(t.key)}
                  className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                    active
                      ? "bg-accent text-white"
                      : "border border-border bg-card text-muted-foreground hover:border-accent/50 hover:text-foreground"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {t.label}
                </button>
              );
            })}
          </div>

          <div className="grid gap-6 rounded-2xl border border-border bg-background p-6 md:grid-cols-[1fr_1.4fr]">
            <div>
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--clay-soft)]">
                <TourIcon className="h-6 w-6 text-accent" />
              </div>
              <h4 className="mt-4 font-serif text-2xl">{tour.label}</h4>
              <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{tour.blurb}</p>
              <Link
                href={tour.href}
                className="mt-5 inline-flex rounded-full border border-border bg-card px-4 py-2 text-sm font-medium transition-colors hover:border-accent/50"
              >
                Open {tour.label} →
              </Link>
            </div>
            <ol className="space-y-3">
              {tour.steps.map((step, i) => (
                <li key={i} className="flex gap-3.5">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-accent/30 font-serif text-sm text-accent">
                    {i + 1}
                  </span>
                  <span className="pt-0.5 text-sm leading-relaxed text-foreground">{step}</span>
                </li>
              ))}
            </ol>
          </div>
        </Panel>

        {/* ---- Checklist + FAQ ---- */}
        <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <Panel
            title="Your getting-started checklist"
            aside={<span className="text-sm font-medium text-muted-foreground">{progress}% done</span>}
          >
            <div className="mb-5 h-1.5 w-full overflow-hidden rounded-full bg-secondary">
              <div
                className="h-full rounded-full bg-accent transition-[width] duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="space-y-2.5">
              {CHECKLIST.map((s, i) => {
                const checked = done.includes(i);
                return (
                  <button
                    key={s.t}
                    onClick={() => toggle(i)}
                    className="flex w-full items-start gap-4 rounded-xl border border-border bg-card p-4 text-left transition-colors hover:border-accent/50"
                  >
                    <span
                      className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 transition-colors"
                      style={{
                        background: checked ? "var(--accent)" : "transparent",
                        borderColor: checked ? "var(--accent)" : "var(--border)",
                      }}
                    >
                      {checked && <Check className="h-3.5 w-3.5 text-white" />}
                    </span>
                    <div>
                      <div className={`font-medium ${checked ? "text-muted-foreground line-through" : ""}`}>
                        {i + 1}. {s.t}
                      </div>
                      <div className="mt-0.5 text-sm text-muted-foreground">{s.d}</div>
                    </div>
                  </button>
                );
              })}
            </div>
          </Panel>

          <Panel title="Common questions">
            <div className="space-y-2.5">
              {FAQ.map((f) => (
                <FaqItem key={f.q} q={f.q} a={f.a} />
              ))}
            </div>
            <div className="mt-5 rounded-xl border border-border bg-background p-4 text-sm">
              <div className="font-medium">Still stuck?</div>
              <div className="mt-0.5 text-muted-foreground">
                Reply to any Sah.Bukti WhatsApp message and a human will help.
              </div>
            </div>
          </Panel>
        </div>
      </div>
    </DashboardLayout>
  );
}
