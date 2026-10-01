"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    router.replace(user ? "/onboarding" : "/login");
  }, [loading, user, router]);

  return <p className="p-10 text-sm text-text-faint">Chargement…</p>;
}
