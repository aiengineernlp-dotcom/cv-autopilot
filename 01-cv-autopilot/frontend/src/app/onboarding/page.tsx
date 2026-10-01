"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { RequireAuth } from "@/components/RequireAuth";
import * as api from "@/lib/api";
import { ApiError } from "@/lib/api";
import { Button, Card, ErrorText, Input, Label, SectionLabel, StatusPill } from "@/components/ui";

const MAX_UPLOADS = 3; // même plafond que le backend (docs/DATA_MODEL.md, décision du 2026-08-15)

// Résolution d'un chemin de conflit ("contact.email", "experiences[1].date_range")
// dans le profil relu -- format imposé au LLM de fusion (voir
// backend/app/services/cv_merge_service.py, règles "conflicts" du prompt,
// 2026-08-15). N'écrit jamais si le chemin ne se résout pas dans le JSON
// courant -- retombe silencieusement sur l'édition manuelle plutôt que de
// corrompre une valeur au hasard.
function parseConflictPath(path: string): (string | number)[] | null {
  const segments: (string | number)[] = [];
  for (const part of path.split(".")) {
    const match = part.match(/^([^[\]]+)((?:\[\d+\])*)$/);
    if (!match) return null;
    segments.push(match[1]);
    for (const idx of match[2].matchAll(/\[(\d+)\]/g)) segments.push(Number(idx[1]));
  }
  return segments;
}

function getAtConflictPath(obj: unknown, path: string): unknown {
  const segments = parseConflictPath(path);
  if (!segments) return undefined;
  let cur: unknown = obj;
  for (const seg of segments) {
    if (cur === null || typeof cur !== "object") return undefined;
    cur = (cur as Record<string | number, unknown>)[seg];
  }
  return cur;
}

function setAtConflictPath(obj: unknown, path: string, value: string): boolean {
  const segments = parseConflictPath(path);
  if (!segments || segments.length === 0) return false;
  let cur: unknown = obj;
  for (let i = 0; i < segments.length - 1; i++) {
    const seg = segments[i];
    if (cur === null || typeof cur !== "object" || !(seg in (cur as object))) return false;
    cur = (cur as Record<string | number, unknown>)[seg];
  }
  const last = segments[segments.length - 1];
  if (cur === null || typeof cur !== "object" || !(last in (cur as object))) return false;
  (cur as Record<string | number, unknown>)[last] = value;
  return true;
}

function OnboardingFlow() {
  const { token, user, logout } = useAuth();

  const [uploads, setUploads] = useState<api.CvUpload[]>([]);
  const [draft, setDraft] = useState<api.Draft | null>(null);
  const [roles, setRoles] = useState<api.Role[]>([]);
  const [reviewText, setReviewText] = useState("");
  const [newRoleName, setNewRoleName] = useState("");
  const [showGenericRoleForm, setShowGenericRoleForm] = useState(false);
  const [postingTitle, setPostingTitle] = useState("");
  const [postingCompany, setPostingCompany] = useState("");
  const [postingDescription, setPostingDescription] = useState("");
  // Rôle -> candidature créée pour lui (2026-08-16) -- seuls les rôles créés
  // depuis une offre précise en ont une (voir onCreateRoleFromPosting), pas
  // ceux créés par nom générique.
  const [candidacyByRole, setCandidacyByRole] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string | null>(null); // nom de l'action en cours, pour désactiver le bon bouton

  useEffect(() => {
    if (!token) return;
    api.listCvUploads(token).then(setUploads).catch(() => {});
    api
      .getDraft(token)
      .then((d) => {
        setDraft(d);
        setReviewText(JSON.stringify(d.reviewed_extraction ?? d.raw_extraction, null, 2));
      })
      .catch(() => {});
    api.listRoles(token).then(setRoles).catch(() => {});
  }, [token]);

  async function run<T>(name: string, fn: () => Promise<T>): Promise<T | undefined> {
    setError("");
    setBusy(name);
    try {
      return await fn();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Une erreur est survenue");
      return undefined;
    } finally {
      setBusy(null);
    }
  }

  async function onUpload(file: File) {
    if (!token) return;
    const upload = await run("upload", () => api.uploadCv(token, file));
    if (upload) setUploads((prev) => [...prev, upload]);
  }

  async function onDeleteUpload(uploadId: string) {
    if (!token) return;
    // deleteCvUpload ne renvoie rien (204) -- même valeur "undefined" en cas
    // de succès ou d'erreur via run(), donc on ne peut pas s'y fier ici.
    // On gère le succès/échec directement plutôt que par la valeur de retour.
    setError("");
    setBusy(`delete-${uploadId}`);
    try {
      await api.deleteCvUpload(token, uploadId);
      setUploads((prev) => prev.filter((u) => u.id !== uploadId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Une erreur est survenue");
    } finally {
      setBusy(null);
    }
  }

  async function onResetProfile() {
    if (!token) return;
    if (
      !window.confirm(
        "Réinitialiser ton profil ? Tes CV uploadés et ta relecture seront effacés. Les rôles déjà créés ne sont pas touchés.",
      )
    ) {
      return;
    }
    // resetProfile renvoie void (204) -- même raison que onDeleteUpload,
    // on gère succès/échec directement plutôt que via run().
    setError("");
    setBusy("reset-profile");
    try {
      await api.resetProfile(token);
      setUploads([]);
      setDraft(null);
      setReviewText("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Une erreur est survenue");
    } finally {
      setBusy(null);
    }
  }

  async function onDeleteRole(roleId: string, roleName: string) {
    if (!token) return;
    if (!window.confirm(`Supprimer le rôle "${roleName}" ? Son CV généré sera aussi effacé. Cette action est définitive.`)) {
      return;
    }
    setError("");
    setBusy(`delete-role-${roleId}`);
    try {
      await api.deleteRole(token, roleId);
      setRoles((prev) => prev.filter((r) => r.id !== roleId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Une erreur est survenue");
    } finally {
      setBusy(null);
    }
  }

  async function onMerge() {
    if (!token) return;
    const d = await run("merge", () => api.mergeUploads(token));
    if (d) {
      setDraft(d);
      setReviewText(JSON.stringify(d.raw_extraction, null, 2));
    }
  }

  function applyConflictValue(field: string, value: string) {
    let parsed: unknown;
    try {
      parsed = JSON.parse(reviewText);
    } catch {
      setError("Le JSON de relecture n'est pas valide -- corrige la syntaxe avant d'appliquer une valeur.");
      return;
    }
    if (!setAtConflictPath(parsed, field, value)) {
      setError(`Impossible d'appliquer automatiquement "${field}" -- corrige-le à la main dans le JSON ci-dessous.`);
      return;
    }
    setError("");
    setReviewText(JSON.stringify(parsed, null, 2));
  }

  function isConflictResolved(field: string, candidates: { value: string }[]): boolean {
    try {
      const current = getAtConflictPath(JSON.parse(reviewText), field);
      return candidates.some((c) => c.value === current);
    } catch {
      return false;
    }
  }

  // Un seul bouton pour "relire" + "confirmer" -- avant, deux boutons
  // séparés ("Soumettre ma relecture" puis "Confirmer mon profil")
  // obligeaient à deux clics successifs sans lien visible entre eux,
  // incohérent avec le reste du parcours (une action = un bouton = un
  // résultat visible). Signalé par l'utilisateur (2026-08-15) : après avoir
  // cliqué un candidat de désaccord, aucune suite claire. Soumet toujours
  // le JSON courant (que ce soit via les boutons de désaccord ou une
  // édition manuelle) puis confirme dans la foulée.
  async function onConfirm() {
    if (!token) return;
    let parsed: api.ExtractedProfile;
    try {
      parsed = JSON.parse(reviewText);
    } catch {
      setError("Le JSON de relecture n'est pas valide -- corrige la syntaxe avant de continuer.");
      return;
    }
    const d = await run("confirm", async () => {
      await api.reviewDraft(token, parsed);
      return api.confirmDraft(token);
    });
    if (d) setDraft(d);
  }

  async function onCreateRole() {
    if (!token || !newRoleName.trim()) return;
    const role = await run("create-role", () => api.createRole(token, newRoleName.trim()));
    if (role) {
      setRoles((prev) => [...prev, role]);
      setNewRoleName("");
    }
  }

  // Adaptation par offre précise (2026-08-15) -- option principale de
  // l'Étape 3, devant la création par nom générique. Génère aussi le CV
  // dans la foulée (pas juste le rôle) pour tenir la promesse "colle une
  // offre, obtiens un CV prêt" en une seule action -- deux appels API
  // enchaînés sous un seul indicateur "busy" continu (pas deux run()
  // séparés, qui laisseraient une bascule courte du bouton entre les deux).
  async function onCreateRoleFromPosting() {
    if (!token || !postingTitle.trim() || !postingDescription.trim()) return;
    setError("");
    setBusy("create-role-posting");
    const title = postingTitle.trim();
    const company = postingCompany.trim();
    const description = postingDescription.trim();
    try {
      const role = await api.createRoleFromPosting(token, title, company, description);
      setRoles((prev) => [...prev, role]);
      setPostingTitle("");
      setPostingCompany("");
      setPostingDescription("");

      await api.generateCv(token, role.id);
      setRoles((prev) => prev.map((r) => (r.id === role.id ? { ...r, status: "cv_ready" } : r)));

      // Rend la candidature trackable (lettre, envoi, suivi) dans la foulée
      // (2026-08-16) -- sans ça, ce rôle n'avait nulle part où accrocher une
      // lettre (trouvé en testant 10 postes, voir backend/scripts/personas/).
      // Échec silencieux : le CV reste le livrable principal de cette action,
      // ne bloque jamais dessus si la candidature ne peut pas être créée.
      try {
        const candidacy = await api.createCandidacyFromPosting(token, {
          role_id: role.id, company: company || "Entreprise non précisée", title, description,
        });
        setCandidacyByRole((prev) => ({ ...prev, [role.id]: candidacy.id }));
      } catch {
        // silencieux, voir commentaire ci-dessus
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Une erreur est survenue");
    } finally {
      setBusy(null);
    }
  }

  async function onGenerateCv(roleId: string) {
    if (!token) return;
    await run(`generate-${roleId}`, () => api.generateCv(token, roleId));
    setRoles((prev) => prev.map((r) => (r.id === roleId ? { ...r, status: "cv_ready" } : r)));
  }

  async function onDownloadCv(roleId: string, roleName: string) {
    if (!token) return;
    await run(`download-${roleId}`, async () => {
      const res = await fetch(api.cvDownloadUrl(roleId), { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) throw new ApiError(res.status, "Téléchargement impossible");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `CV_${roleName.replace(/\s+/g, "_")}.docx`;
      a.click();
      URL.revokeObjectURL(url);
    });
  }

  const canUploadMore = uploads.length < MAX_UPLOADS;
  // Fusionner reste possible à tout moment tant qu'il y a au moins un CV
  // extrait -- y compris après une première confirmation (met à jour le
  // profil). Bug trouvé le 2026-08-15 : la condition excluait justement ce
  // cas (`draft.status !== "confirmed"` devient faux une fois confirmé),
  // rendant le bouton "Mettre à jour mon profil" visible mais grisé en
  // permanence -- l'affichage avait été corrigé, pas cette condition.
  const canMerge = uploads.some((u) => u.status === "extracted");
  const draftConfirmed = draft?.status === "confirmed";
  // Confirmer soumet toujours la relecture courante juste avant (voir
  // onConfirm) -- plus besoin de vérifier un `reviewed_extraction` déjà
  // enregistré côté serveur, seule la présence d'un draft à relire compte.
  const canConfirm = draft && draft.status === "pending_review";
  const resolvedConflictsCount = draft ? draft.conflicts.filter((c) => isConflictResolved(c.field, c.candidates)).length : 0;

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <header className="mb-10 flex items-center justify-between border-b border-border pb-6">
        <div>
          <span className="font-mono text-xs uppercase tracking-wide text-accent">CV Autopilot</span>
          <h1 className="font-[family-name:var(--font-display)] text-3xl font-semibold text-text">
            Bienvenue, {user?.full_name}
          </h1>
        </div>
        <div className="flex gap-3">
          {roles.length > 0 && (
            <Link href="/discovery">
              <Button variant="ghost">Recherche automatique</Button>
            </Link>
          )}
          <Button variant="ghost" onClick={logout}>
            Déconnexion
          </Button>
        </div>
      </header>

      <ErrorText>{error}</ErrorText>

      {/* Étape 1 -- Upload */}
      <section className="mb-12">
        <div className="flex items-baseline justify-between gap-3.5">
          <SectionLabel
            index="Étape 1"
            title="Dépose ton CV"
            description={`Jusqu'à ${MAX_UPLOADS} CV existants -- ${uploads.length}/${MAX_UPLOADS} uploadé(s).`}
          />
          {(uploads.length > 0 || draft) && (
            <button
              type="button"
              onClick={onResetProfile}
              disabled={busy === "reset-profile"}
              className="flex-none text-xs font-medium text-text-faint hover:text-critical disabled:opacity-50"
            >
              {busy === "reset-profile" ? "Réinitialisation…" : "Réinitialiser mon profil"}
            </button>
          )}
        </div>
        <Card className="flex flex-col gap-3">
          {uploads.map((u) => (
            <div key={u.id} className="flex items-center justify-between text-sm">
              <span className="text-text">{u.file_name}</span>
              <div className="flex items-center gap-2">
                <StatusPill tone={u.status === "extracted" ? "ok" : "neutral"}>{u.status}</StatusPill>
                <button
                  type="button"
                  onClick={() => onDeleteUpload(u.id)}
                  disabled={busy === `delete-${u.id}`}
                  aria-label={`Retirer ${u.file_name}`}
                  title="Retirer ce CV"
                  className="text-text-faint hover:text-critical disabled:opacity-50"
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
          {canUploadMore && (
            <label className="cursor-pointer rounded-lg border border-dashed border-border px-4 py-3 text-center text-sm text-text-soft hover:border-accent">
              {busy === "upload" ? "Extraction en cours…" : "+ Ajouter un CV (.docx)"}
              <input
                type="file"
                accept=".docx,.txt"
                className="hidden"
                disabled={busy === "upload"}
                onChange={(e) => e.target.files?.[0] && onUpload(e.target.files[0])}
              />
            </label>
          )}
        </Card>
      </section>

      {/* Étape 2 -- Fusion + relecture */}
      <section className="mb-12">
        <SectionLabel
          index="Étape 2"
          title="Relis ce qu'on a compris"
          description="Rien n'est utilisé pour générer un CV avant ta validation."
        />
        <Card className="flex flex-col gap-4">
          {(!draft || draftConfirmed) && (
            <Button onClick={onMerge} disabled={!canMerge || busy === "merge"}>
              {busy === "merge"
                ? "Fusion en cours…"
                : draftConfirmed
                  ? "Mettre à jour mon profil (nouveau CV ajouté)"
                  : "Fusionner mes CV"}
            </Button>
          )}

          {draft && (
            <>
              {draft.conflicts.length > 0 && (
                <div className="rounded-lg bg-warning-soft p-3 text-sm text-warning">
                  <p className="mb-3 font-semibold">
                    {resolvedConflictsCount}/{draft.conflicts.length} désaccord(s) résolu(s) — clique une valeur pour
                    l&apos;appliquer dans le JSON ci-dessous, ou corrige-le à la main.
                  </p>
                  <ul className="space-y-3">
                    {draft.conflicts.map((c, i) => {
                      let currentValue: unknown;
                      let resolvable = true;
                      try {
                        currentValue = getAtConflictPath(JSON.parse(reviewText), c.field);
                      } catch {
                        resolvable = false;
                      }
                      return (
                        <li key={i}>
                          <div className="mb-1 font-mono text-xs">{c.field}</div>
                          {resolvable ? (
                            <div className="flex flex-wrap gap-2">
                              {c.candidates.map((cand, ci) => {
                                const active = currentValue === cand.value;
                                return (
                                  <button
                                    key={ci}
                                    type="button"
                                    onClick={() => applyConflictValue(c.field, cand.value)}
                                    disabled={draftConfirmed}
                                    className={`rounded-lg border px-2.5 py-1.5 text-left text-xs transition disabled:cursor-not-allowed disabled:opacity-50 ${
                                      active
                                        ? "border-success bg-success-soft text-success"
                                        : "border-border bg-panel text-text hover:border-accent"
                                    }`}
                                  >
                                    {active ? "✓ " : ""}
                                    &quot;{cand.value}&quot;{" "}
                                    <span className="text-text-faint">({cand.source_document})</span>
                                  </button>
                                );
                              })}
                            </div>
                          ) : (
                            <p>
                              {c.candidates.map((cand) => `"${cand.value}" (${cand.source_document})`).join(" vs ")}
                            </p>
                          )}
                        </li>
                      );
                    })}
                  </ul>

                  {!draftConfirmed && (
                    <div className="mt-4 flex items-center gap-3 border-t border-warning/30 pt-3">
                      <Button onClick={onConfirm} disabled={!canConfirm || busy === "confirm"}>
                        {busy === "confirm" ? "Confirmation…" : "Confirmer mon profil"}
                      </Button>
                      <span className="text-xs">
                        {resolvedConflictsCount === draft.conflicts.length
                          ? "Tous les désaccords sont résolus -- valide dès que tu es prêt."
                          : "Tu peux confirmer même sans avoir tout résolu ci-dessus."}
                      </span>
                    </div>
                  )}
                </div>
              )}

              <div>
                <Label>Profil extrait (modifiable)</Label>
                <textarea
                  value={reviewText}
                  onChange={(e) => setReviewText(e.target.value)}
                  disabled={draftConfirmed}
                  rows={16}
                  className="w-full rounded-lg border border-border bg-panel-2 p-3 font-mono text-xs text-text outline-none focus:border-accent disabled:opacity-70"
                />
              </div>

              {!draftConfirmed && (
                <div className="flex items-center gap-3">
                  <Button onClick={onConfirm} disabled={!canConfirm || busy === "confirm"}>
                    {busy === "confirm" ? "Confirmation…" : "Confirmer mon profil"}
                  </Button>
                  {draft.conflicts.length > 0 && resolvedConflictsCount < draft.conflicts.length && (
                    <span className="text-xs text-text-faint">
                      Encore {draft.conflicts.length - resolvedConflictsCount} désaccord(s) non résolu(s) ci-dessus --
                      tu peux confirmer quand même, ou les résoudre d&apos;abord.
                    </span>
                  )}
                </div>
              )}
              {draftConfirmed && <StatusPill tone="ok">Profil confirmé</StatusPill>}
            </>
          )}
        </Card>
      </section>

      {/* Étape 3 -- Rôles ciblés */}
      {draftConfirmed && (
        <section className="mb-12">
          <SectionLabel
            index="Étape 3"
            title="Colle une offre, obtiens ton CV"
            description="Colle le titre et la description d'une offre trouvée n'importe où -- ton CV est adapté et prêt à télécharger en quelques secondes, jamais un fait inventé."
          />
          <Card className="flex flex-col gap-4">
            <div className="flex flex-col gap-3">
              <div>
                <Label>Titre du poste</Label>
                <Input
                  placeholder="ex : Housekeeping Attendant"
                  value={postingTitle}
                  onChange={(e) => setPostingTitle(e.target.value)}
                />
              </div>
              <div>
                <Label>Entreprise (optionnel)</Label>
                <Input
                  placeholder="ex : Emirates Palace Hotel"
                  value={postingCompany}
                  onChange={(e) => setPostingCompany(e.target.value)}
                />
              </div>
              <div>
                <Label>Description de l&apos;offre (colle le texte complet)</Label>
                <textarea
                  placeholder="Colle ici le texte de l'offre -- responsabilités, exigences..."
                  value={postingDescription}
                  onChange={(e) => setPostingDescription(e.target.value)}
                  rows={6}
                  className="w-full rounded-lg border border-border bg-panel p-3 text-sm text-text outline-none focus:border-accent"
                />
              </div>
              <Button
                onClick={onCreateRoleFromPosting}
                disabled={busy === "create-role-posting" || !postingTitle.trim() || !postingDescription.trim()}
              >
                {busy === "create-role-posting" ? "Génération du CV…" : "Générer mon CV pour cette offre"}
              </Button>
            </div>

            <button
              type="button"
              onClick={() => setShowGenericRoleForm((v) => !v)}
              className="self-start text-xs text-text-faint underline underline-offset-2 hover:text-accent"
            >
              {showGenericRoleForm
                ? "Masquer"
                : "Ou crée un CV générique par type de poste (pas lié à une offre précise)"}
            </button>

            {showGenericRoleForm && (
              <div className="flex gap-3">
                <Input
                  placeholder="ex : ML / AI Engineer"
                  value={newRoleName}
                  onChange={(e) => setNewRoleName(e.target.value)}
                />
                <Button onClick={onCreateRole} disabled={busy === "create-role" || !newRoleName.trim()}>
                  {busy === "create-role" ? "Génération…" : "Ajouter"}
                </Button>
              </div>
            )}

            {roles.map((role) => (
              <div key={role.id} className="rounded-lg border border-border p-4">
                <div className="mb-2 flex items-center justify-between">
                  <span className="font-semibold text-text">{role.name}</span>
                  <div className="flex items-center gap-2">
                    <StatusPill tone={role.status === "cv_ready" ? "ok" : "neutral"}>{role.status}</StatusPill>
                    <button
                      type="button"
                      onClick={() => onDeleteRole(role.id, role.name)}
                      disabled={busy === `delete-role-${role.id}`}
                      aria-label={`Supprimer le rôle ${role.name}`}
                      title="Supprimer ce rôle"
                      className="text-text-faint hover:text-critical disabled:opacity-50"
                    >
                      ✕
                    </button>
                  </div>
                </div>
                {role.summary && <p className="mb-2 text-sm text-text-soft">{role.summary}</p>}
                {role.keywords.length > 0 && (
                  <div className="mb-3 flex flex-wrap gap-1.5">
                    {role.keywords.map((k) => (
                      <span key={k} className="rounded-full border border-border px-2 py-0.5 text-xs text-text-faint">
                        {k}
                      </span>
                    ))}
                  </div>
                )}
                {role.coverage_notes.length > 0 && (
                  <details className="mb-3 text-xs text-text-faint">
                    <summary className="cursor-pointer">Écarts détectés ({role.coverage_notes.length})</summary>
                    <ul className="mt-1 list-disc space-y-1 pl-4">
                      {role.coverage_notes.map((n, i) => (
                        <li key={i}>{n}</li>
                      ))}
                    </ul>
                  </details>
                )}
                <div className="flex gap-3">
                  <Button
                    variant="ghost"
                    onClick={() => onGenerateCv(role.id)}
                    disabled={busy === `generate-${role.id}`}
                  >
                    {busy === `generate-${role.id}` ? "Génération…" : "Générer le CV"}
                  </Button>
                  {role.status === "cv_ready" && (
                    <Button onClick={() => onDownloadCv(role.id, role.name)} disabled={busy === `download-${role.id}`}>
                      {busy === `download-${role.id}` ? "Téléchargement…" : "Télécharger"}
                    </Button>
                  )}
                  {candidacyByRole[role.id] && (
                    <Link href="/discovery" className="self-center text-xs text-accent underline underline-offset-2">
                      Suivre cette candidature (lettre, envoi) →
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </Card>
        </section>
      )}
    </main>
  );
}

export default function OnboardingPage() {
  return (
    <RequireAuth>
      <OnboardingFlow />
    </RequireAuth>
  );
}
