"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { Button, Card, ErrorText, Input, Label } from "@/components/ui";

export default function SignupPage() {
  const { signup } = useAuth();
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await signup(email, password, fullName);
      router.push("/onboarding");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Inscription impossible");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex flex-1 items-center justify-center p-6">
      <Card className="w-full max-w-sm">
        <h1 className="mb-1 font-[family-name:var(--font-display)] text-2xl font-semibold text-text">
          Créer ton compte
        </h1>
        <p className="mb-6 text-sm text-text-soft">
          Ensuite : upload de ton CV, et le système prend le relais.
        </p>

        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <div>
            <Label>Nom complet</Label>
            <Input required value={fullName} onChange={(e) => setFullName(e.target.value)} />
          </div>
          <div>
            <Label>Email</Label>
            <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <Label>Mot de passe (8 caractères minimum)</Label>
            <Input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <ErrorText>{error}</ErrorText>
          <Button type="submit" disabled={submitting}>
            {submitting ? "Création…" : "Créer mon compte"}
          </Button>
          <p className="text-center text-xs text-text-faint">
            En créant un compte, tu acceptes la{" "}
            <Link href="/confidentialite" className="underline">
              politique de confidentialité
            </Link>
            .
          </p>
        </form>

        <p className="mt-5 text-sm text-text-soft">
          Déjà un compte ?{" "}
          <Link href="/login" className="font-semibold">
            Connecte-toi
          </Link>
        </p>
      </Card>
    </main>
  );
}
