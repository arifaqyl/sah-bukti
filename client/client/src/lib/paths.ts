/** App base path from Vite (e.g. `/` locally, `/sahbukti/` in production). */
export const APP_BASE = import.meta.env.BASE_URL.replace(/\/$/, "");

export const API_BASE = `${APP_BASE}/api/v1`.replace(/\/{2,}/g, "/");

export function appPath(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${APP_BASE}${normalized}` || normalized;
}
