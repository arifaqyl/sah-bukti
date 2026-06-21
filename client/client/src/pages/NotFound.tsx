import { Link } from "wouter";
import { Logo } from "@/components/Logo";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
      <Logo size={40} />
      <h1 className="mt-10 font-serif text-6xl">404</h1>
      <p className="mt-3 max-w-sm text-muted-foreground">
        This page wandered off like an unlogged receipt. Let's get you back to your shop.
      </p>
      <div className="mt-8 flex gap-3">
        <Link href="/" className="rounded-full border border-border px-6 py-3 text-sm font-medium transition-colors hover:bg-secondary">
          Home
        </Link>
        <Link href="/dashboard" className="rounded-full bg-accent px-6 py-3 text-sm font-medium text-accent-foreground transition-transform hover:-translate-y-0.5 active:scale-[0.97]">
          Go to dashboard
        </Link>
      </div>
    </div>
  );
}
