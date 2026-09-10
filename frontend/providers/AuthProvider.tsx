"use client";

import { createContext, useCallback, useEffect, useMemo, useState } from "react";
import { fetchCurrentUser, loginUser, logoutUser, registerUser, type AuthUser } from "@/lib/auth";

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<AuthUser>;
  register: (name: string, email: string, password: string) => Promise<AuthUser>;
  logout: () => Promise<void>;
  /** Clears local auth state without calling the backend — for when a
   * request already told us the session is gone (e.g. a 401 mid-stream). */
  clearSession: () => void;
  refresh: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    const current = await fetchCurrentUser();
    setUser(current);
    setIsLoading(false);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(async (email: string, password: string) => {
    const loggedIn = await loginUser(email, password);
    setUser(loggedIn);
    return loggedIn;
  }, []);

  const register = useCallback(async (name: string, email: string, password: string) => {
    const created = await registerUser(name, email, password);
    setUser(created);
    return created;
  }, []);

  const logout = useCallback(async () => {
    await logoutUser();
    setUser(null);
  }, []);

  const clearSession = useCallback(() => setUser(null), []);

  const value = useMemo(
    () => ({ user, isLoading, login, register, logout, clearSession, refresh }),
    [user, isLoading, login, register, logout, clearSession, refresh]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
