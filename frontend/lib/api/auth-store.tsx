"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { usePathname, useRouter } from "next/navigation";
import type { Role } from "./schemas";
import {
  clearSession,
  readSession,
  writeSession,
  type StoredSession,
} from "./token";
import { login as loginRequest } from "./endpoints";

interface AuthState {
  session: StoredSession | null;
  ready: boolean;
  signIn: (username: string, password: string) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

const PUBLIC_ROUTES = new Set(["/login"]);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<StoredSession | null>(null);
  const [ready, setReady] = useState(false);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    setSession(readSession());
    setReady(true);
  }, []);

  // Route guard: kick unauthenticated users to /login (except public routes).
  useEffect(() => {
    if (!ready) return;
    if (!session && !PUBLIC_ROUTES.has(pathname)) {
      router.replace("/login");
    }
  }, [ready, session, pathname, router]);

  const signIn = useCallback(
    async (username: string, password: string) => {
      const res = await loginRequest(username, password);
      const next: StoredSession = {
        token: res.access_token,
        role: res.role,
        username,
      };
      writeSession(next);
      setSession(next);
      router.replace("/reports");
    },
    [router]
  );

  const signOut = useCallback(() => {
    clearSession();
    setSession(null);
    router.replace("/login");
  }, [router]);

  const value = useMemo<AuthState>(
    () => ({ session, ready, signIn, signOut }),
    [session, ready, signIn, signOut]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}

export function useRole(): Role | null {
  const { session } = useAuth();
  return (session?.role as Role) || null;
}
