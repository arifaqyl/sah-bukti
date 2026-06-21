import { Link } from "wouter";
import { Logo } from "@/components/Logo";
import {
  ArrowRight,
  ShieldCheck,
  MessagesSquare,
  ReceiptText,
  Boxes,
  FileCheck2,
  Sparkles,
} from "lucide-react";

function Nav() {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-md">
      <div className="container flex h-[72px] items-center justify-between">
        <Logo />
        <nav className="hidden items-center gap-7 text-sm font-medium text-muted-foreground md:flex">
          <a href="#workflow" className="transition-colors hover:text-foreground">Workflow</a>
          <a href="#how" className="transition-colors hover:text-foreground">How it works</a>
          <a href="#who" className="transition-colors hover:text-foreground">Who it's for</a>
        </nav>
        <div className="flex items-center gap-2.5">
          <Link href="/auth" className="hidden rounded-full border border-border px-4 py-2 text-sm font-medium transition-colors hover:bg-secondary sm:inline-flex">
            Log in
          </Link>
          <Link href="/auth" className="inline-flex items-center gap-2 rounded-full bg-foreground px-4 py-2 text-sm font-medium text-background transition-transform hover:-translate-y-0.5 active:scale-[0.97]">
            Start free
          </Link>
        </div>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="container grid items-center gap-12 py-16 md:grid-cols-[1.15fr_0.85fr] md:py-24">
      <div className="stagger max-w-xl">
        <div className="overline mb-4 inline-flex items-center gap-2">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-accent" />
          Proof before payment. Clean books after.
        </div>
        <h1 className="text-[clamp(2.5rem,5.5vw,4rem)]">
          Proof before payment.{" "}
          <span className="text-accent">Clean books after.</span>
        </h1>
        <p className="mt-6 max-w-lg text-lg leading-relaxed text-muted-foreground">
          Sah.Bukti turns WhatsApp order messages and payment confirmations into reviewable invoices and proofs,
          then keeps your ledger locked until the owner approves what is true.
        </p>
        <div className="mt-9 flex flex-wrap gap-3">
          <Link href="/auth" className="inline-flex items-center gap-2 rounded-full bg-accent px-7 py-3.5 text-base font-medium text-accent-foreground transition-transform hover:-translate-y-0.5 active:scale-[0.97]">
            Create your shop <ArrowRight className="h-4 w-4" />
          </Link>
          <a href="#how" className="inline-flex items-center gap-2 rounded-full border border-border px-7 py-3.5 text-base font-medium transition-colors hover:bg-secondary">
            See how it works
          </a>
        </div>
        <div className="mt-8 flex items-center gap-2 text-sm text-muted-foreground">
          <ShieldCheck className="h-4 w-4 text-accent" />
          Evidence never auto-pays. Proofs stay reviewable until you approve.
        </div>
      </div>

      <div className="flex justify-center md:justify-end">
        <div className="float relative">
          <div
            className="absolute -inset-8 -z-10 rounded-[3rem] opacity-60 blur-2xl"
            style={{ background: "radial-gradient(circle at 50% 40%, var(--clay-soft), transparent 70%)" }}
          />
          <div className="w-[280px] rounded-[2.2rem] border border-border bg-card p-5 shadow-[0_20px_60px_rgba(26,26,26,0.18)] sm:w-[320px]">
            <div className="rounded-[1.6rem] border border-border bg-background p-4">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Review Queue</div>
                  <div className="mt-1 font-serif text-xl text-foreground">2 proofs waiting</div>
                </div>
                <div className="rounded-full bg-accent px-3 py-1 text-xs font-medium text-accent-foreground">
                  Owner gate
                </div>
              </div>
              <div className="space-y-3">
                <div className="rounded-2xl border border-border bg-card p-3">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-foreground">INV-CUR1</span>
                    <span className="font-serif text-foreground">RM45.00</span>
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">Customer said “dah bayar” after ordering</div>
                  <div className="mt-3 inline-flex rounded-full bg-[var(--clay-soft)] px-2.5 py-1 text-[11px] font-medium text-foreground">
                    Needs review
                  </div>
                </div>
                <div className="rounded-2xl border border-border bg-card p-3">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-foreground">INV-CUR2</span>
                    <span className="font-serif text-foreground">RM62.50</span>
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">Order message parsed into a pending invoice</div>
                  <div className="mt-3 inline-flex rounded-full border border-border px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
                    Awaiting owner approval
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

const STATS = [
  { value: "0", label: "Auto-paid invoices" },
  { value: "1", label: "Approval gate" },
  { value: "2", label: "Core intake lanes" },
  { value: "8", label: "Ops screens" },
];

function StatStrip() {
  return (
    <section className="container">
      <div className="stagger grid grid-cols-2 gap-3 sm:grid-cols-4">
        {STATS.map((s) => (
          <div key={s.label} className="rounded-2xl border border-border bg-card p-6 text-center transition-transform hover:-translate-y-1">
            <div className="font-serif text-4xl font-medium text-foreground">{s.value}</div>
            <div className="mt-1 text-xs uppercase tracking-wider text-muted-foreground">{s.label}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

const BENTO = [
  { span: "sm:col-span-2", tag: "Workflow", icon: MessagesSquare, title: "Evidence → Review → Ledger", body: "Sah.Bukti shows the full journey from messy WhatsApp input to a trusted financial state your accountant can read." },
  { span: "", tag: "Founder mode", icon: Sparkles, title: "Setup in minutes", body: "Sign up, name your shop, add your first customer." },
  { span: "", tag: "Control", icon: ShieldCheck, title: "No silent payments", body: "Proofs wait for approval before anything changes." },
  { span: "sm:col-span-2", tag: "Month-end", icon: FileCheck2, title: "Ready for handoff", body: "Readiness and export summarise what actually happened this month, in one place." },
  { span: "sm:col-span-2", tag: "Ops memory", icon: Boxes, title: "Notes that matter", body: "Supplier habits and ingredients live right beside your stock levels." },
];

function Bento() {
  return (
    <section id="workflow" className="container py-20">
      <div className="mb-10 max-w-2xl">
        <div className="overline mb-3">Built like a product, not a form</div>
        <h2 className="text-[clamp(1.75rem,3.5vw,2.5rem)]">Every screen has a job. Every action has a next step.</h2>
      </div>
      <div className="stagger grid grid-cols-1 gap-4 sm:grid-cols-4">
        {BENTO.map((b) => {
          const Icon = b.icon;
          return (
            <div key={b.title} className={`flex flex-col justify-between rounded-[1.4rem] border border-border bg-card p-6 transition-transform hover:-translate-y-1 ${b.span}`}>
              <div className="mb-8 flex h-10 w-10 items-center justify-center rounded-xl" style={{ background: "var(--clay-soft)" }}>
                <Icon className="h-5 w-5 text-accent" />
              </div>
              <div>
                <div className="overline mb-1.5">{b.tag}</div>
                <h3 className="text-xl">{b.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{b.body}</p>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

const STEPS = [
  { n: "1", t: "Capture the chat", d: "WhatsApp order and payment messages become reviewable records." },
  { n: "2", t: "Review before truth", d: "Payment proofs stay pending until you approve amount and reference." },
  { n: "3", t: "Run the shop", d: "Track customers, invoices, ingredients, supplier notes and stock." },
  { n: "4", t: "Hand off month-end", d: "Readiness and export show what is actually ready for the accountant." },
];

function Steps() {
  return (
    <section id="how" className="border-y border-border bg-card/60">
      <div className="container py-20">
        <div className="mb-10 max-w-2xl">
        <div className="overline mb-3">How it works</div>
          <h2 className="text-[clamp(1.75rem,3.5vw,2.5rem)]">Proof first. Ledger second.</h2>
        </div>
        <div className="stagger grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s) => (
            <div key={s.n} className="rounded-2xl border border-border bg-background p-6">
              <ReceiptText className="mb-5 h-5 w-5 text-muted-foreground" />
              <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-full font-serif text-base font-medium text-accent-foreground" style={{ background: "var(--clay)" }}>
                {s.n}
              </div>
              <h3 className="text-lg">{s.t}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{s.d}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function SplitPanels() {
  return (
    <section id="who" className="container grid gap-5 py-20 md:grid-cols-2">
      <div className="rounded-[1.6rem] border border-border bg-card p-8">
        <h3 className="text-2xl">Who Sah.Bukti is for</h3>
        <ul className="mt-5 space-y-3 text-[15px] text-muted-foreground">
          {[
            "Malaysian micro-SMEs running orders in WhatsApp",
            "Shops juggling WhatsApp orders, QR, cash and transfers",
            "Owners who need clean books without an accounting degree",
          ].map((li) => (
            <li key={li} className="flex items-start gap-3">
              <FileCheck2 className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
              {li}
            </li>
          ))}
        </ul>
      </div>
      <div
        className="flex flex-col justify-between rounded-[1.6rem] border border-border p-8 text-background"
        style={{ background: "var(--foreground)" }}
      >
        <div>
          <h3 className="text-2xl text-background">What you avoid</h3>
          <p className="mt-3 text-[15px] leading-relaxed opacity-80">
            No CSV exports that silently overwrite each other. No payment that posts before you say so.
            No month-end scramble guessing what was real.
          </p>
        </div>
        <div className="mt-8 inline-flex items-center gap-2 text-sm opacity-70">
          <ShieldCheck className="h-4 w-4" /> One approval gate. Always.
        </div>
      </div>
    </section>
  );
}

function CTABand() {
  return (
    <section className="container pb-24">
      <div
        className="relative overflow-hidden rounded-[2rem] border border-border bg-card px-8 py-16 text-center"
      >
        <div
          className="absolute inset-0 -z-10 opacity-70"
          style={{ background: "radial-gradient(circle at 50% 0%, var(--clay-soft), transparent 65%)" }}
        />
        <div className="overline mb-3">Ready when you are</div>
        <h2 className="mx-auto max-w-xl text-[clamp(1.75rem,4vw,2.75rem)]">
          Proof before payment. Clean books after.
        </h2>
        <p className="mx-auto mt-4 max-w-md text-muted-foreground">
          Free to start. Bring your WhatsApp chaos — leave with reviewed records.
        </p>
        <Link href="/auth" className="mt-8 inline-flex items-center gap-2 rounded-full bg-accent px-8 py-4 text-base font-medium text-accent-foreground transition-transform hover:-translate-y-0.5 active:scale-[0.97]">
          Create your shop <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-border">
      <div className="container flex flex-col items-center justify-between gap-4 py-8 sm:flex-row">
        <Logo size={26} />
        <p className="text-sm text-muted-foreground">Built for real shop workflows. No AI slop.</p>
        <p className="text-xs text-muted-foreground">© {new Date().getFullYear()} Sah.Bukti</p>
      </div>
    </footer>
  );
}

export default function Landing() {
  return (
    <div className="page-fade min-h-screen">
      <Nav />
      <Hero />
      <StatStrip />
      <Bento />
      <Steps />
      <SplitPanels />
      <CTABand />
      <Footer />
    </div>
  );
}
