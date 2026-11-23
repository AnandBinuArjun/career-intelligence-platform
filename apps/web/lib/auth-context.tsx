"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { apiFetch, clearStoredSession, getStoredToken, setStoredSession } from "./api";

export interface AuthUser {
  id: string;
  email: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    const token = getStoredToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await apiFetch<AuthUser>("/auth/me");
      setUser(me);
    } catch {
      clearStoredSession();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    const token = getStoredToken();
    if (!token) {
      Promise.resolve().then(() => {
        if (active) {
          setUser(null);
          setLoading(false);
        }
      });
      return () => {
        active = false;
      };
    }
    apiFetch<AuthUser>("/auth/me")
      .then((me) => {
        if (active) setUser(me);
      })
      .catch(() => {
        clearStoredSession();
        if (active) setUser(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await apiFetch<{
      access_token: string;
      csrf_token?: string | null;
    }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setStoredSession(tokens.access_token, tokens.csrf_token);
    const me = await apiFetch<AuthUser>("/auth/me");
    setUser(me);
  }, []);

  const register = useCallback(
    async (email: string, password: string, fullName?: string) => {
      await apiFetch<AuthUser>("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          email,
          password,
          full_name: fullName?.trim() || undefined,
        }),
      });
      await login(email, password);
    },
    [login]
  );

  const logout = useCallback(async () => {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } catch {
      // ignore network/session errors on sign-out
    } finally {
      clearStoredSession();
      setUser(null);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
}
