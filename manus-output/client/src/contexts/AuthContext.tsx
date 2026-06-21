import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { SahBuktiUser, loadSession, saveSession, clearSession, initTheme } from "@/lib/sahbukti";

interface AuthState {
  user: SahBuktiUser | null;
  signIn: (user: SahBuktiUser) => void;
  signOut: () => void;
}

const AuthCtx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  // Initialize synchronously from localStorage so a returning user with a
  // valid session is NOT bounced to /auth on a hard reload.
  const [user, setUser] = useState<SahBuktiUser | null>(() => loadSession());

  useEffect(() => {
    // Apply persisted theme color (sahbukti theme key) on boot.
    initTheme();
    if (user?.accent) saveSession(user); // re-apply accent
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const signIn = (u: SahBuktiUser) => {
    saveSession(u);
    setUser(u);
  };

  const signOut = () => {
    clearSession();
    setUser(null);
  };

  return <AuthCtx.Provider value={{ user, signIn, signOut }}>{children}</AuthCtx.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
