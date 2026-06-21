// ============================================================
// Sah.Bukti — Shared constants, types, and mock auth store
// Anti-slop "Paper & Ink" build. Frontend-only permanent site.
// ============================================================

export type ShopType =
  | "Food & Beverage"
  | "Retail & Grocery"
  | "Services"
  | "Online / Dropship";

export const SHOP_TYPES: ShopType[] = [
  "Food & Beverage",
  "Retail & Grocery",
  "Services",
  "Online / Dropship",
];

export const ACCENT_OPTIONS = [
  { name: "Clay", value: "#C75B39" },
  { name: "Green", value: "#3F6B4F" },
  { name: "Blue", value: "#2F6F95" },
  { name: "Amber", value: "#C18A22" },
  { name: "Rose", value: "#B14A63" },
  { name: "Teal", value: "#2E7D78" },
  { name: "Mist", value: "#6F8F8B" },
  { name: "Slate", value: "#52606D" },
];

// Default accent (clay/terracotta) used when the user skips the picker.
export const DEFAULT_ACCENT = ACCENT_OPTIONS[0].value;

// Dedicated client-side theme color store, per the addendum spec.
const THEME_COLOR_KEY = "sahbukti_theme_color";

export function saveThemeColor(hex: string) {
  try {
    localStorage.setItem(THEME_COLOR_KEY, hex);
  } catch {
    /* ignore */
  }
}

export function loadThemeColor(): string {
  try {
    return localStorage.getItem(THEME_COLOR_KEY) || DEFAULT_ACCENT;
  } catch {
    return DEFAULT_ACCENT;
  }
}

export interface SahBuktiUser {
  display_name: string;
  business_name: string;
  shop_type?: ShopType;
  accent?: string;
}

const STORAGE_KEY = "sahbukti_session_v1";

export function loadSession(): SahBuktiUser | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as SahBuktiUser) : null;
  } catch {
    return null;
  }
}

export function saveSession(user: SahBuktiUser) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
  if (user.accent) {
    // Persist the standalone theme color and apply it live.
    saveThemeColor(user.accent);
    applyAccent(user.accent);
  }
}

export function clearSession() {
  localStorage.removeItem(STORAGE_KEY);
  document.documentElement.style.removeProperty("--clay");
  document.documentElement.style.removeProperty("--accent");
  document.documentElement.style.removeProperty("--ring");
  document.documentElement.style.removeProperty("--sidebar-primary");
}

export function applyAccent(hex: string) {
  document.documentElement.style.setProperty("--clay", hex);
  document.documentElement.style.setProperty("--accent", hex);
  document.documentElement.style.setProperty("--ring", hex);
  document.documentElement.style.setProperty("--sidebar-primary", hex);
}

// Apply the persisted theme color (or clay default) to the dashboard shell
// CSS custom property --accent on load. Safe to call on every mount.
export function initTheme() {
  applyAccent(loadThemeColor());
}

export function currency(n: number) {
  return "RM " + n.toLocaleString("en-MY", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
