"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { Button, Card, ErrorText, Input, Label } from "@/components/ui";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(email, password);
      router.push("/onboarding");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Connexion impossible");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex flex-1 items-center justify-center p-6">
      <Card className="w-full max-w-sm">
        <h1 className="mb-1 font-[family-name:var(--font-display)] text-2xl font-semibold text-text">
          CV Autopilot
        </h1>
        <p className="mb-6 text-sm text-text-soft">Connecte-toi pour continuer.</p>

        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <div>
            <Label>Email</Label>
            <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <Label>Mot de passe</Label>
            <Input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <ErrorText>{error}</ErrorText>
          <Button type="submit" disabled={submitting}>
            {submitting ? "Connexion…" : "Se connecter"}
          </Button>
        </form>

        <p className="mt-5 text-sm text-text-soft">
          Pas encore de compte ?{" "}
          <Link href="/signup" className="font-semibold">
            Inscris-toi
          </Link>
        </p>
      </Card>
    </main>
  );
}
