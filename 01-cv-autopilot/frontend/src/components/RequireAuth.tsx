"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

/** Redirige vers /login si aucun utilisateur n'est chargé -- posé une fois
 * en tête des pages qui exigent une session, pas répété page par page. */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading || !user) {
    return <p className="p-10 text-sm text-text-faint">Chargement…</p>;
  }

  return <>{children}</>;
}
