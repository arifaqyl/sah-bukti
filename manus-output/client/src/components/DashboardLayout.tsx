import { ReactNode, useEffect, useState } from "react";
import { Link, useLocation } from "wouter";
import { Logo } from "@/components/Logo";
import { useAuth } from "@/contexts/AuthContext";
import { initTheme, loadThemeColor } from "@/lib/sahbukti";
import {
  LayoutDashboard,
  Inbox,
  CheckCircle2,
  FileText,
  Users,
  Boxes,
  CalendarCheck,
  Download,
  LifeBuoy,
  LogOut,
} from "lucide-react";

interface NavDef {
  href: string;
  label: string;
  icon: typeof LayoutDashboard;
}

const PRIMARY: NavDef[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/evidence", label: "Evidence", icon: Inbox },
  { href: "/review", label: "Review", icon: CheckCircle2 },
  { href: "/invoices", label: "Invoices", icon: FileText },
  { href: "/customers", label: "Customers", icon: Users },
  { href: "/inventory", label: "Inventory", icon: Boxes },
];

const SECONDARY: NavDef[] = [
  { href: "/readiness", label: "Readiness", icon: CalendarCheck },
  { href: "/export", label: "Export", icon: Download },
  { href: "/help", label: "Setup guide", icon: LifeBuoy },
];

const MOBILE: NavDef[] = [
  { href: "/dashboard", label: "Home", icon: LayoutDashboard },
  { href: "/review", label: "Review", icon: CheckCircle2 },
  { href: "/invoices", label: "Invoices", icon: FileText },
  { href: "/customers", label: "Customers", icon: Users },
  { href: "/help", label: "Guide", icon: LifeBuoy },
];

function SideItem({ item, active }: { item: NavDef; active: boolean }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      className={`flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition-colors ${
        active
          ? "bg-secondary text-foreground"
          : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"
      }`}
    >
      <Icon className={`h-[18px] w-[18px] ${active ? "text-accent" : ""}`} />
      {item.label}
    </Link>
  );
}

export function DashboardLayout({
  title,
  subtitle,
  action,
  children,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  const [location] = useLocation();
  const { user, signOut } = useAuth();
  const [themeColor, setThemeColor] = useState<string>(loadThemeColor());

  // Apply the chosen accent to --accent on every dashboard load.
  useEffect(() => {
    initTheme();
    setThemeColor(loadThemeColor());
  }, [user?.accent]);

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[264px_1fr]">
      {/* Sidebar */}
      <aside className="sticky top-0 hidden h-screen flex-col border-r border-border bg-sidebar p-4 lg:flex">
        <div className="px-2 pb-6 pt-2">
          <Logo />
          <div className="mt-3 flex items-center gap-2 px-0.5">
            <span
              className="inline-block h-3 w-3 shrink-0 rounded-full border border-border"
              style={{ background: themeColor }}
              title="Workspace accent"
              aria-label="Workspace accent colour"
            />
            <p className="truncate text-xs text-muted-foreground">
              {user?.business_name || "reviewable evidence"}
            </p>
          </div>
        </div>

        <nav className="flex flex-1 flex-col gap-1">
          {PRIMARY.map((i) => (
            <SideItem key={i.href} item={i} active={location === i.href} />
          ))}
          <div className="my-3 border-t border-border" />
          {SECONDARY.map((i) => (
            <SideItem key={i.href} item={i} active={location === i.href} />
          ))}
        </nav>

        <button
          onClick={signOut}
          className="mt-2 flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
        >
          <LogOut className="h-[18px] w-[18px]" /> Logout
        </button>
      </aside>

      {/* Main */}
      <div className="flex min-h-screen flex-col">
        <header className="sticky top-0 z-30 border-b border-border bg-background/85 backdrop-blur-md">
          <div className="flex items-center justify-between gap-4 px-5 py-4 lg:px-10">
            <div className="min-w-0">
              <h1 className="truncate text-[1.6rem]">{title}</h1>
              {subtitle && <p className="truncate text-sm text-muted-foreground">{subtitle}</p>}
            </div>
            {action}
          </div>
        </header>

        <main className="page-fade flex-1 px-5 pb-28 pt-7 lg:px-10 lg:pb-10">{children}</main>
      </div>

      {/* Mobile bottom nav */}
      <nav className="fixed inset-x-0 bottom-0 z-40 flex items-center justify-around border-t border-border bg-card/95 px-2 py-2 backdrop-blur-md lg:hidden">
        {MOBILE.map((i) => {
          const Icon = i.icon;
          const active = location === i.href;
          return (
            <Link
              key={i.href}
              href={i.href}
              className={`flex flex-col items-center gap-1 rounded-lg px-3 py-1.5 text-[10px] font-medium transition-colors ${
                active ? "text-accent" : "text-muted-foreground"
              }`}
            >
              <Icon className="h-5 w-5" />
              {i.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
