"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { RequireAuth } from "@/components/RequireAuth";
import * as api from "@/lib/api";
import { ApiError } from "@/lib/api";
import { Button, Card, ErrorText, Input, Label, SectionLabel, StatusPill } from "@/components/ui";

// Vocabulaire repris de app/models/enums.py::ApplicationStatus -- même
// ordre que le cycle de vie réel d'une candidature (queued -> ... ->
// rejected), pas alphabétique, pour que le menu déroulant suive le sens
// naturel de progression.
const STATUS_LABELS: Record<api.ApplicationStatus, string> = {
  queued: "En file (pas encore postulé)",
  sent: "Envoyée",
  viewed: "Vue par le recruteur",
  contacted: "Recruteur a répondu",
  interview_scheduled: "Entretien prévu",
  offer_received: "Offre reçue",
  rejected: "Refusée",
};

function DiscoveryFlow() {
  const { token, logout } = useAuth();
  const [sources, setSources] = useState<api.DiscoverySource[]>([]);
  const [candidacies, setCandidacies] = useState<api.Candidacy[]>([]);
  const [emailAccounts, setEmailAccounts] = useState<api.EmailAccount[]>([]);
  const [showEmailAccountForm, setShowEmailAccountForm] = useState(false);
  const [emailLabel, setEmailLabel] = useState("");
  const [imapHost, setImapHost] = useState("");
  const [imapPort, setImapPort] = useState("993");
  const [smtpHost, setSmtpHost] = useState("");
  const [smtpPort, setSmtpPort] = useState("465");
  const [emailUsername, setEmailUsername] = useState("");
  const [emailPassword, setEmailPassword] = useState("");
  const [knownCompanies, setKnownCompanies] = useState<api.KnownCompany[]>([]);
  const [companySearch, setCompanySearch] = useState("");
  const [showManualForm, setShowManualForm] = useState(false);
  const [label, setLabel] = useState("");
  const [boardToken, setBoardToken] = useState("");
  const [type, setType] = useState<"ats_greenhouse" | "ats_lever">("ats_greenhouse");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [lastRun, setLastRun] = useState<api.DiscoveryRunResult | null>(null);

  // Lettre de motivation + envoi réel (2026-08-16) -- un seul panneau ouvert
  // à la fois (comme le formulaire "connecter un compte email" ci-dessus),
  // pas une carte par candidature en permanence : la liste peut être longue.
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [sendRecruiterEmail, setSendRecruiterEmail] = useState("");
  const [sendRecruiterName, setSendRecruiterName] = useState("");
  const [sendEmailAccountId, setSendEmailAccountId] = useState("");
  const [sendPreview, setSendPreview] = useState<api.SendPreview | null>(null);
  // Brouillon éditable de la lettre (2026-08-16) -- la génération IA est un
  // premier jet, pas un texte figé ; synchronisé avec candidacy.cover_letter_text
  // à l'ouverture/régénération, divergent ensuite tant que non enregistré.
  const [letterDraft, setLetterDraft] = useState("");

  useEffect(() => {
    if (!token) return;
    api.listDiscoverySources(token).then(setSources).catch(() => {});
    api.listCandidacies(token).then(setCandidacies).catch(() => {});
    api.listKnownCompanies(token).then(setKnownCompanies).catch(() => {});
    api.listEmailAccounts(token).then(setEmailAccounts).catch(() => {});
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

  async function onAddSource() {
    if (!token || !label.trim() || !boardToken.trim()) return;
    const source = await run("add-source", () => api.addDiscoverySource(token, type, label.trim(), boardToken.trim()));
    if (source) {
      setSources((prev) => [...prev, source]);
      setLabel("");
      setBoardToken("");
    }
  }

  // Comptes email (2026-08-16) -- pour la découverte par alertes et
  // l'auto-envoi canal email, depuis la propre boîte de l'utilisateur.
  // Le mot de passe ne transite qu'une fois vers le serveur (jamais
  // renvoyé, jamais stocké en clair) -- voir email_account_service.connect,
  // qui vérifie la connexion IMAP avant tout enregistrement.
  async function onConnectEmailAccount() {
    if (!token || !emailLabel.trim() || !imapHost.trim() || !smtpHost.trim() || !emailUsername.trim() || !emailPassword) return;
    const account = await run("connect-email", () =>
      api.connectEmailAccount(token, {
        label: emailLabel.trim(),
        imap_host: imapHost.trim(),
        imap_port: Number(imapPort) || 993,
        smtp_host: smtpHost.trim(),
        smtp_port: Number(smtpPort) || 465,
        username: emailUsername.trim(),
        password: emailPassword,
      }),
    );
    if (account) {
      setEmailAccounts((prev) => [...prev, account]);
      setEmailLabel("");
      setImapHost("");
      setSmtpHost("");
      setEmailUsername("");
      setEmailPassword("");
      setShowEmailAccountForm(false);

      // Crée tout de suite la source de découverte associée (2026-08-16) --
      // sans ça, connecter un compte ne servait à rien de concret : aucune
      // alerte Indeed/LinkedIn n'était jamais cherchée dedans (voir
      // PROGRESSION_PHASES.md, "frontend pas branché"). N'empêche pas la
      // connexion si la création de la source échoue -- le compte reste
      // utilisable pour l'envoi même sans découverte.
      try {
        const source = await api.addEmailAlertSource(token, account.id);
        setSources((prev) => [...prev, source]);
      } catch {
        // silencieux -- le compte est bien connecté, seule la découverte
        // par alertes n'a pas pu démarrer ; pas une erreur bloquante à
        // afficher à ce stade.
      }
    }
  }

  async function onDeleteEmailAccount(accountId: string) {
    if (!token) return;
    if (!window.confirm("Déconnecter ce compte email ? Il ne sera plus utilisé pour la découverte ou l'envoi.")) return;
    setError("");
    setBusy(`delete-email-${accountId}`);
    try {
      await api.deleteEmailAccount(token, accountId);
      setEmailAccounts((prev) => prev.filter((a) => a.id !== accountId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Une erreur est survenue");
    } finally {
      setBusy(null);
    }
  }

  // Ajout en un clic depuis la liste connue (2026-08-15) -- résout "je ne
  // sais pas si c'est Greenhouse ou Lever, ni le board token" : l'utilisateur
  // choisit juste un nom, le reste est déjà rempli côté serveur (voir
  // backend/app/data/known_companies.py). Le formulaire manuel reste
  // disponible pour toute entreprise absente de la liste.
  async function onAddKnownCompany(company: api.KnownCompany) {
    if (!token) return;
    const source = await run(`add-known-${company.board_token}`, () =>
      api.addDiscoverySource(token, company.type, company.label, company.board_token),
    );
    if (source) {
      setSources((prev) => [...prev, source]);
      setCompanySearch("");
    }
  }

  async function onUpdateStatus(candidacyId: string, newStatus: api.ApplicationStatus) {
    if (!token) return;
    setError("");
    setBusy(`status-${candidacyId}`);
    try {
      await api.updateCandidacyStatus(token, candidacyId, newStatus);
      setCandidacies((prev) => prev.map((c) => (c.id === candidacyId ? { ...c, status: newStatus } : c)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Une erreur est survenue");
    } finally {
      setBusy(null);
    }
  }

  function onToggleExpand(candidacy: api.Candidacy) {
    if (expandedId === candidacy.id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(candidacy.id);
    setSendRecruiterEmail(candidacy.notes?.match(/\S+@\S+/)?.[0] ?? "");
    setSendRecruiterName("");
    setSendEmailAccountId(emailAccounts[0]?.id ?? "");
    setSendPreview(null);
    setLetterDraft(candidacy.cover_letter_text ?? "");
  }

  async function onGenerateCoverLetter(candidacyId: string) {
    if (!token) return;
    const updated = await run(`cover-letter-${candidacyId}`, () => api.generateCoverLetter(token, candidacyId));
    if (updated) {
      setCandidacies((prev) => prev.map((c) => (c.id === candidacyId ? updated : c)));
      setLetterDraft(updated.cover_letter_text ?? "");
    }
  }

  async function onSaveCoverLetter(candidacyId: string) {
    if (!token || !letterDraft.trim()) return;
    const updated = await run(`cover-letter-save-${candidacyId}`, () => api.updateCoverLetter(token, candidacyId, letterDraft));
    if (updated) {
      setCandidacies((prev) => prev.map((c) => (c.id === candidacyId ? updated : c)));
    }
  }

  async function onPreviewSend(candidacyId: string) {
    if (!token || !sendRecruiterEmail.trim() || !sendEmailAccountId) return;
    const result = await run(`send-preview-${candidacyId}`, () =>
      api.sendApplication(token, candidacyId, {
        email_account_id: sendEmailAccountId,
        recruiter_email: sendRecruiterEmail.trim(),
        recruiter_name: sendRecruiterName.trim() || null,
        confirm: false,
      }),
    );
    if (result) setSendPreview(result.preview);
  }

  async function onConfirmSend(candidacyId: string) {
    if (!token || !sendRecruiterEmail.trim() || !sendEmailAccountId) return;
    if (!window.confirm(`Envoyer réellement cette candidature à ${sendRecruiterEmail.trim()} ? Cette action est irréversible.`)) return;
    const result = await run(`send-confirm-${candidacyId}`, () =>
      api.sendApplication(token, candidacyId, {
        email_account_id: sendEmailAccountId,
        recruiter_email: sendRecruiterEmail.trim(),
        recruiter_name: sendRecruiterName.trim() || null,
        confirm: true,
      }),
    );
    if (result?.application) {
      setCandidacies((prev) => prev.map((c) => (c.id === candidacyId ? result.application! : c)));
      setExpandedId(null);
      setSendPreview(null);
    }
  }

  async function onRun() {
    if (!token) return;
    const result = await run("run", () => api.runDiscovery(token));
    if (result) {
      setLastRun(result);
      const [freshSources, freshCandidacies] = await Promise.all([
        api.listDiscoverySources(token),
        api.listCandidacies(token),
      ]);
      setSources(freshSources);
      setCandidacies(freshCandidacies);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <header className="mb-10 flex items-center justify-between border-b border-border pb-6">
        <div>
          <span className="font-mono text-xs uppercase tracking-wide text-accent">CV Autopilot</span>
          <h1 className="font-[family-name:var(--font-display)] text-3xl font-semibold text-text">
            Recherche automatique
          </h1>
        </div>
        <div className="flex gap-3">
          <Link href="/onboarding">
            <Button variant="ghost">Mes CV</Button>
          </Link>
          <Button variant="ghost" onClick={logout}>
            Déconnexion
          </Button>
        </div>
      </header>

      <ErrorText>{error}</ErrorText>

      <section className="mb-12">
        <SectionLabel
          index="Boîte mail"
          title="Ton compte email"
          description="Connecté depuis ta propre boîte -- jamais un domaine partagé. Utilisé pour repérer les alertes d'offres (LinkedIn/Indeed) et, plus tard, pour candidater directement depuis ton adresse."
        />
        <Card className="flex flex-col gap-4">
          {emailAccounts.map((a) => (
            <div key={a.id} className="flex items-center justify-between text-sm">
              <div>
                <span className="font-semibold text-text">{a.label}</span>{" "}
                <span className="ml-2 text-text-faint">{a.username}</span>
              </div>
              <button
                type="button"
                onClick={() => onDeleteEmailAccount(a.id)}
                disabled={busy === `delete-email-${a.id}`}
                aria-label={`Déconnecter ${a.label}`}
                title="Déconnecter ce compte"
                className="text-text-faint hover:text-critical disabled:opacity-50"
              >
                ✕
              </button>
            </div>
          ))}

          <button
            type="button"
            onClick={() => setShowEmailAccountForm((v) => !v)}
            className="self-start text-xs text-text-faint underline underline-offset-2 hover:text-accent"
          >
            {showEmailAccountForm ? "Masquer" : "+ Connecter un compte email"}
          </button>

          {showEmailAccountForm && (
            <div className="flex flex-col gap-3">
              <div>
                <Label>Nom (pour toi -- ex: &quot;Mon email principal&quot;)</Label>
                <Input value={emailLabel} onChange={(e) => setEmailLabel(e.target.value)} placeholder="Mon email principal" />
              </div>
              <div>
                <Label>Adresse email</Label>
                <Input value={emailUsername} onChange={(e) => setEmailUsername(e.target.value)} placeholder="toi@exemple.com" />
              </div>
              <div className="flex gap-3">
                <div className="flex-1">
                  <Label>Serveur IMAP (réception)</Label>
                  <Input value={imapHost} onChange={(e) => setImapHost(e.target.value)} placeholder="imap.exemple.com" />
                </div>
                <div className="w-24">
                  <Label>Port</Label>
                  <Input value={imapPort} onChange={(e) => setImapPort(e.target.value)} placeholder="993" />
                </div>
              </div>
              <div className="flex gap-3">
                <div className="flex-1">
                  <Label>Serveur SMTP (envoi)</Label>
                  <Input value={smtpHost} onChange={(e) => setSmtpHost(e.target.value)} placeholder="smtp.exemple.com" />
                </div>
                <div className="w-24">
                  <Label>Port</Label>
                  <Input value={smtpPort} onChange={(e) => setSmtpPort(e.target.value)} placeholder="465" />
                </div>
              </div>
              <div>
                <Label>Mot de passe (idéalement un mot de passe d&apos;application, pas ton mot de passe principal)</Label>
                <Input type="password" value={emailPassword} onChange={(e) => setEmailPassword(e.target.value)} />
              </div>
              <Button
                onClick={onConnectEmailAccount}
                disabled={
                  busy === "connect-email" ||
                  !emailLabel.trim() ||
                  !imapHost.trim() ||
                  !smtpHost.trim() ||
                  !emailUsername.trim() ||
                  !emailPassword
                }
              >
                {busy === "connect-email" ? "Vérification de la connexion…" : "Connecter"}
              </Button>
            </div>
          )}
        </Card>
      </section>

      <section className="mb-12">
        <SectionLabel
          index="Sources"
          title="Entreprises à surveiller"
          description="API publiques Greenhouse/Lever + alertes Indeed/LinkedIn depuis ta boîte mail -- jamais de scraping direct."
        />
        <Card className="flex flex-col gap-4">
          {sources.map((s) => (
            <div key={s.id} className="flex items-center justify-between text-sm">
              <div>
                <span className="font-semibold text-text">{s.label}</span>{" "}
                <span className="ml-2 font-mono text-xs text-text-faint">{s.type}</span>
                {s.last_run_summary && "error" in s.last_run_summary && (
                  <p className="text-xs text-critical">dernier passage en erreur : {s.last_run_summary.error}</p>
                )}
                {s.last_run_summary && !("error" in s.last_run_summary) && (
                  <p className="text-xs text-text-faint">
                    dernier passage : {s.last_run_summary.found} offre(s) examinée(s), {s.last_run_summary.new}{" "}
                    nouvelle(s), {s.last_run_summary.queued} mise(s) en file
                    {s.last_run_summary.new === 0 && s.last_run_summary.found > 0 && " (toutes déjà vues avant)"}
                  </p>
                )}
              </div>
              <StatusPill tone={s.status === "active" ? "ok" : "warn"}>{s.status}</StatusPill>
            </div>
          ))}

          <div>
            <Label>Cherche une entreprise par nom</Label>
            <Input
              placeholder="ex : Stripe, Anthropic, Palantir…"
              value={companySearch}
              onChange={(e) => setCompanySearch(e.target.value)}
            />
            {companySearch.trim() && (() => {
              const matches = knownCompanies.filter((c) =>
                c.label.toLowerCase().includes(companySearch.trim().toLowerCase()),
              );
              const availableMatches = matches.filter(
                (c) => !sources.some((s) => s.label.toLowerCase() === c.label.toLowerCase()),
              );
              return (
                <div className="mt-2 flex flex-col gap-1.5">
                  {availableMatches.slice(0, 6).map((c) => (
                    <button
                      key={c.board_token}
                      type="button"
                      onClick={() => onAddKnownCompany(c)}
                      disabled={busy === `add-known-${c.board_token}`}
                      className="flex items-center justify-between rounded-lg border border-border bg-panel px-3 py-2 text-left text-sm text-text hover:border-accent disabled:opacity-50"
                    >
                      <span>{c.label}</span>
                      <span className="text-xs text-accent">
                        {busy === `add-known-${c.board_token}` ? "Ajout…" : "+ Ajouter"}
                      </span>
                    </button>
                  ))}
                  {availableMatches.length === 0 && matches.length > 0 && (
                    <p className="text-xs text-text-faint">Déjà dans tes sources surveillées.</p>
                  )}
                  {matches.length === 0 && (
                    <p className="text-xs text-text-faint">
                      Pas dans notre liste de départ -- ajoute-la manuellement ci-dessous.
                    </p>
                  )}
                </div>
              );
            })()}
          </div>

          <button
            type="button"
            onClick={() => setShowManualForm((v) => !v)}
            className="self-start text-xs text-text-faint underline underline-offset-2 hover:text-accent"
          >
            {showManualForm ? "Masquer l'ajout manuel" : "Je connais déjà le board token -- ajouter manuellement"}
          </button>

          {showManualForm && (
            <div className="flex flex-wrap gap-3">
              <select
                value={type}
                onChange={(e) => setType(e.target.value as "ats_greenhouse" | "ats_lever")}
                className="rounded-lg border border-border bg-panel px-3 py-2 text-sm text-text"
              >
                <option value="ats_greenhouse">Greenhouse</option>
                <option value="ats_lever">Lever</option>
              </select>
              <Input placeholder="Nom (ex : Stripe)" value={label} onChange={(e) => setLabel(e.target.value)} className="max-w-[180px]" />
              <Input
                placeholder="board token (ex : stripe)"
                value={boardToken}
                onChange={(e) => setBoardToken(e.target.value)}
                className="max-w-[180px]"
              />
              <Button onClick={onAddSource} disabled={busy === "add-source"}>
                {busy === "add-source" ? "Ajout…" : "Ajouter"}
              </Button>
            </div>
          )}
        </Card>
      </section>

      <section className="mb-12">
        <SectionLabel
          index="Action"
          title="Lancer la recherche"
          description="Cherche sur toutes les sources actives, compare aux rôles confirmés."
        />
        <Card className="flex flex-col gap-3">
          <Button onClick={onRun} disabled={busy === "run" || sources.length === 0}>
            {busy === "run" ? "Recherche en cours…" : "Chercher des offres maintenant"}
          </Button>
          {lastRun && (
            <p className="text-sm text-text-soft">
              {lastRun.sources_checked} source(s) · {lastRun.postings_found} offre(s) examinée(s) ·{" "}
              {lastRun.new_postings} nouvelle(s) · <strong>{lastRun.queued} candidature(s) préparée(s)</strong>
              {lastRun.errors.length > 0 && (
                <span className="mt-2 block text-critical">{lastRun.errors.join(" · ")}</span>
              )}
            </p>
          )}
        </Card>
      </section>

      <section>
        <SectionLabel
          index="Résultat"
          title="Candidatures trouvées"
          description="Canal plateforme -- jamais d'envoi automatique, à valider toi-même sur le lien d'origine."
        />
        <Card className="flex flex-col gap-3">
          {candidacies.length === 0 && <p className="text-sm text-text-faint">Rien pour l&rsquo;instant.</p>}
          {candidacies.map((c) => (
            <div key={c.id} className="flex flex-col gap-2 rounded-lg border border-border p-3 text-sm">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <span className="font-semibold text-text">{c.company}</span>{" "}
                  <span className="ml-2 text-text-soft">{c.title}</span>
                  {c.posting_url && (
                    <>
                      {" "}
                      <a
                        href={c.posting_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="ml-2 text-xs text-accent underline underline-offset-2"
                      >
                        Voir l&apos;offre ↗
                      </a>
                    </>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-text-faint">score {c.match_score}</span>
                  <select
                    value={c.status}
                    onChange={(e) => onUpdateStatus(c.id, e.target.value as api.ApplicationStatus)}
                    disabled={busy === `status-${c.id}`}
                    className="rounded-lg border border-border bg-panel px-2 py-1 text-xs text-text outline-none focus:border-accent disabled:opacity-50"
                  >
                    {Object.entries(STATUS_LABELS).map(([value, statusLabel]) => (
                      <option key={value} value={value}>
                        {statusLabel}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {c.sent_at ? (
                <p className="text-xs text-success">
                  ✅ Envoyée par email le {new Date(c.sent_at).toLocaleDateString()} -- lettre figée, plus modifiable.
                </p>
              ) : (
                <button
                  type="button"
                  onClick={() => onToggleExpand(c)}
                  className="self-start text-xs text-text-faint underline underline-offset-2 hover:text-accent"
                >
                  {expandedId === c.id ? "Masquer" : c.cover_letter_text ? "Lettre & envoi" : "Rédiger la lettre & envoyer"}
                </button>
              )}

              {expandedId === c.id && !c.sent_at && (
                <div className="flex flex-col gap-3 border-t border-border pt-3">
                  <div>
                    <div className="mb-1 flex items-center justify-between">
                      <Label>Lettre de motivation -- adaptée à cette offre précise</Label>
                      <button
                        type="button"
                        onClick={() => onGenerateCoverLetter(c.id)}
                        disabled={busy === `cover-letter-${c.id}`}
                        className="text-xs text-accent underline underline-offset-2 disabled:opacity-50"
                      >
                        {busy === `cover-letter-${c.id}`
                          ? "Génération…"
                          : c.cover_letter_text
                            ? "Régénérer"
                            : "Générer la lettre"}
                      </button>
                    </div>
                    {c.cover_letter_text ? (
                      <>
                        <textarea
                          value={letterDraft}
                          onChange={(e) => setLetterDraft(e.target.value)}
                          rows={8}
                          className="w-full rounded-lg border border-border bg-panel px-3 py-2 text-xs text-text-soft outline-none focus:border-accent"
                        />
                        {letterDraft !== c.cover_letter_text && (
                          <div className="mt-1.5 flex items-center gap-2">
                            <Button
                              variant="ghost"
                              onClick={() => onSaveCoverLetter(c.id)}
                              disabled={busy === `cover-letter-save-${c.id}` || !letterDraft.trim()}
                            >
                              {busy === `cover-letter-save-${c.id}` ? "Enregistrement…" : "Enregistrer les modifications"}
                            </Button>
                            <span className="text-xs text-text-faint">Non enregistré</span>
                          </div>
                        )}
                      </>
                    ) : (
                      <p className="text-xs text-text-faint">Pas encore générée.</p>
                    )}
                  </div>

                  {c.cover_letter_text && (
                    <div className="flex flex-col gap-3 border-t border-border pt-3">
                      <p className="text-xs text-text-faint">
                        Envoi direct par email -- tu dois fournir l&apos;adresse du recruteur toi-même, jamais devinée
                        automatiquement.
                      </p>
                      <div>
                        <Label>Email du recruteur</Label>
                        <Input
                          value={sendRecruiterEmail}
                          onChange={(e) => setSendRecruiterEmail(e.target.value)}
                          placeholder="recruteur@entreprise.com"
                        />
                      </div>
                      <div>
                        <Label>Nom du recruteur (optionnel)</Label>
                        <Input value={sendRecruiterName} onChange={(e) => setSendRecruiterName(e.target.value)} placeholder="Jane Doe" />
                      </div>
                      <div>
                        <Label>Envoyer depuis</Label>
                        {emailAccounts.length === 0 ? (
                          <p className="text-xs text-critical">Connecte d&apos;abord un compte email (section ci-dessus).</p>
                        ) : (
                          <select
                            value={sendEmailAccountId}
                            onChange={(e) => setSendEmailAccountId(e.target.value)}
                            className="w-full rounded-lg border border-border bg-panel px-3 py-2 text-sm text-text outline-none focus:border-accent"
                          >
                            {emailAccounts.map((a) => (
                              <option key={a.id} value={a.id}>
                                {a.label} ({a.username})
                              </option>
                            ))}
                          </select>
                        )}
                      </div>

                      {sendPreview && (
                        <div className="rounded-lg border border-accent/40 bg-panel p-3 text-xs">
                          <p className="mb-1 text-text-faint">
                            Aperçu -- de <strong>{sendPreview.sender}</strong> à <strong>{sendPreview.to}</strong>
                          </p>
                          <p className="mb-1 font-semibold text-text">{sendPreview.subject}</p>
                          <p className="whitespace-pre-wrap text-text-soft">{sendPreview.text}</p>
                          {sendPreview.attachment && (
                            <p className="mt-1 text-text-faint">📎 {sendPreview.attachment}</p>
                          )}
                        </div>
                      )}

                      <div className="flex gap-3">
                        <Button
                          variant="ghost"
                          onClick={() => onPreviewSend(c.id)}
                          disabled={
                            busy === `send-preview-${c.id}` || !sendRecruiterEmail.trim() || !sendEmailAccountId
                          }
                        >
                          {busy === `send-preview-${c.id}` ? "Aperçu…" : "Aperçu"}
                        </Button>
                        <Button
                          onClick={() => onConfirmSend(c.id)}
                          disabled={
                            busy === `send-confirm-${c.id}` || !sendPreview || !sendRecruiterEmail.trim() || !sendEmailAccountId
                          }
                        >
                          {busy === `send-confirm-${c.id}` ? "Envoi…" : "Confirmer l'envoi réel"}
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </Card>
      </section>
    </main>
  );
}

export default function DiscoveryPage() {
  return (
    <RequireAuth>
      <DiscoveryFlow />
    </RequireAuth>
  );
}
