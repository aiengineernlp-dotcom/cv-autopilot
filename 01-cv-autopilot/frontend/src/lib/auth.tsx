"use client";

/**
 * Contexte d'authentification -- seul endroit qui lit/écrit le jeton JWT
 * (localStorage) et l'utilisateur courant. Les pages consomment `useAuth()`,
 * jamais `localStorage` directement.
 */
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import * as api from "./api";

const TOKEN_KEY = "cv-autopilot-token";

type AuthState = {
  token: string | null;
  user: api.User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<api.User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      setLoading(false);
      return;
    }
    api
      .me(stored)
      .then((u) => {
        setToken(stored);
        setUser(u);
      })
      .catch(() => localStorage.removeItem(TOKEN_KEY))
      .finally(() => setLoading(false));
  }, []);

  async function login(email: string, password: string) {
    const { access_token } = await api.login(email, password);
    const u = await api.me(access_token);
    localStorage.setItem(TOKEN_KEY, access_token);
    setToken(access_token);
    setUser(u);
  }

  async function signup(email: string, password: string, fullName: string) {
    await api.signup(email, password, fullName);
    await login(email, password);
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ token, user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth doit être utilisé sous AuthProvider");
  return ctx;
}
