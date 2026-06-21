import { ReactNode } from "react";

type Tone = "neutral" | "success" | "warn" | "danger" | "accent";

const TONE_CLASS: Record<Tone, string> = {
  neutral: "bg-secondary text-muted-foreground",
  success: "text-[oklch(0.42_0.09_155)]",
  warn: "text-[oklch(0.52_0.11_75)]",
  danger: "text-[oklch(0.5_0.15_25)]",
  accent: "text-accent",
};

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: Tone }) {
  const styles: Record<Tone, React.CSSProperties> = {
    neutral: {},
    success: { background: "oklch(0.93 0.05 155)" },
    warn: { background: "oklch(0.94 0.06 80)" },
    danger: { background: "oklch(0.93 0.05 25)" },
    accent: { background: "var(--clay-soft)" },
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-wide ${TONE_CLASS[tone]}`}
      style={styles[tone]}
    >
      {children}
    </span>
  );
}

export function StatCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-6 transition-transform hover:-translate-y-0.5">
      <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="mt-2 font-serif text-3xl font-medium text-foreground">{value}</div>
      {hint && <div className="mt-1 text-xs text-muted-foreground">{hint}</div>}
    </div>
  );
}

export function Panel({ title, children, aside }: { title?: string; children: ReactNode; aside?: ReactNode }) {
  return (
    <section className="rounded-[1.5rem] border border-border bg-card p-6">
      {title && (
        <div className="mb-5 flex items-center justify-between">
          <h3 className="text-xl">{title}</h3>
          {aside}
        </div>
      )}
      {children}
    </section>
  );
}

export function EmptyState({
  title,
  text,
  icon,
}: {
  title: string;
  text: string;
  icon?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-background/40 px-6 py-16 text-center">
      {icon && <div className="mb-4 text-muted-foreground opacity-60">{icon}</div>}
      <h3 className="text-xl">{title}</h3>
      <p className="mt-2 max-w-sm text-sm text-muted-foreground">{text}</p>
    </div>
  );
}

export function ListRow({
  title,
  subtitle,
  amount,
  badge,
  onClick,
  trailing,
}: {
  title: string;
  subtitle: string;
  amount?: string;
  badge?: ReactNode;
  onClick?: () => void;
  trailing?: ReactNode;
}) {
  return (
    <div
      onClick={onClick}
      className="flex items-center justify-between gap-4 rounded-xl border border-border bg-card px-5 py-4 transition-all hover:-translate-y-0.5 hover:border-accent/50 hover:shadow-[0_6px_18px_rgba(26,26,26,0.05)]"
    >
      <div className="min-w-0">
        <div className="truncate font-medium text-foreground">{title}</div>
        <div className="mt-0.5 truncate text-[13px] text-muted-foreground">{subtitle}</div>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1.5">
        {badge}
        {amount && <div className="font-serif text-[15px] text-foreground">{amount}</div>}
        {trailing}
      </div>
    </div>
  );
}
