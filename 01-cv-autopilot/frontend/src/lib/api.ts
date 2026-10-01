/**
 * Client API -- seul fichier autorisé à parler au backend FastAPI
 * (voir ../../backend/README.md pour les endpoints). Les composants
 * n'appellent jamais `fetch` directement, ils passent par ces fonctions.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8001";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit & { token?: string | null } = {},
): Promise<T> {
  const { token, headers, ...rest } = options;
  const res = await fetch(`${API_URL}${path}`, {
    ...rest,
    headers: {
      ...(!(rest.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new ApiError(res.status, detail?.detail ?? `Erreur ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  const contentType = res.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) return res.json() as Promise<T>;
  return undefined as T;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export type User = {
  id: string;
  email: string;
  full_name: string;
  plan: string;
};

export function signup(email: string, password: string, fullName: string) {
  return request<User>("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
}

export function login(email: string, password: string) {
  return request<{ access_token: string; token_type: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function me(token: string) {
  return request<User>("/auth/me", { token });
}

// ---------------------------------------------------------------------------
// Onboarding
// ---------------------------------------------------------------------------

export type CvUpload = {
  id: string;
  file_name: string;
  status: string;
  uploaded_at: string;
};

export type Conflict = {
  field: string;
  candidates: { value: string; source_document: string }[];
  resolved: string | null;
};

// Le contenu exact d'un profil extrait/fusionné suit le schéma des 4 briques
// (voir ../../prototypes/*/output/RESULTS.md) -- volontairement peu typé ici,
// c'est un JSON éditable par l'utilisateur en relecture, pas une forme figée.
export type ExtractedProfile = Record<string, unknown>;

export type Draft = {
  id: string;
  raw_extraction: ExtractedProfile;
  reviewed_extraction: ExtractedProfile | null;
  conflicts: Conflict[];
  status: "pending_review" | "confirmed" | "discarded";
};

export type Role = {
  id: string;
  name: string;
  summary: string | null;
  skills: { category: string; items: string[] }[];
  keywords: string[];
  status: string;
  coverage_notes: string[];
};

export function uploadCv(token: string, file: File) {
  const form = new FormData();
  form.append("file", file);
  return request<CvUpload>("/onboarding/cv-uploads", { method: "POST", token, body: form });
}

export function listCvUploads(token: string) {
  return request<CvUpload[]>("/onboarding/cv-uploads", { token });
}

export function deleteCvUpload(token: string, uploadId: string) {
  return request<void>(`/onboarding/cv-uploads/${uploadId}`, { method: "DELETE", token });
}

// Vide les CV uploadés + le draft (actif ou confirmé) pour repartir de zéro
// à l'étape 1-2. Ne touche jamais aux rôles déjà créés (voir
// backend/app/services/onboarding_service.py::reset_profile).
export function resetProfile(token: string) {
  return request<void>("/onboarding/profile", { method: "DELETE", token });
}

export function mergeUploads(token: string) {
  return request<Draft>("/onboarding/merge", { method: "POST", token });
}

export function getDraft(token: string) {
  return request<Draft>("/onboarding/draft", { token });
}

export function reviewDraft(token: string, reviewedExtraction: ExtractedProfile) {
  return request<Draft>("/onboarding/draft", {
    method: "PATCH",
    token,
    body: JSON.stringify({ reviewed_extraction: reviewedExtraction }),
  });
}

export function confirmDraft(token: string) {
  return request<Draft>("/onboarding/draft/confirm", { method: "POST", token });
}

export function createRole(token: string, name: string) {
  return request<Role>("/onboarding/roles", {
    method: "POST",
    token,
    body: JSON.stringify({ name }),
  });
}

// Adaptation par offre précise (2026-08-15) -- description est le texte
// complet d'une offre (collé par l'utilisateur, ou repris de /discovery),
// pas un simple nom de rôle générique.
export function createRoleFromPosting(token: string, title: string, company: string, description: string) {
  return request<Role>("/onboarding/roles/from-posting", {
    method: "POST",
    token,
    body: JSON.stringify({ title, company: company.trim() || null, description }),
  });
}

export function listRoles(token: string) {
  return request<Role[]>("/onboarding/roles", { token });
}

// Suppression ciblée d'un rôle -- contrairement à resetProfile, celle-ci
// EST destructive pour le rôle visé (et son CV généré).
export function deleteRole(token: string, roleId: string) {
  return request<void>(`/onboarding/roles/${roleId}`, { method: "DELETE", token });
}

export function generateCv(token: string, roleId: string) {
  return request<{ version: number; download_url: string }>(
    `/onboarding/roles/${roleId}/generate-cv`,
    { method: "POST", token },
  );
}

export function cvDownloadUrl(roleId: string) {
  return `${API_URL}/onboarding/roles/${roleId}/cv`;
}

// ---------------------------------------------------------------------------
// Comptes email (2026-08-16) -- pour la découverte par alertes et l'auto-envoi
// canal email, depuis la propre boîte de l'utilisateur (jamais un domaine partagé).
// ---------------------------------------------------------------------------

export type EmailAccount = {
  id: string;
  label: string;
  imap_host: string;
  imap_port: number;
  smtp_host: string;
  smtp_port: number;
  username: string;
  created_at: string;
};

export function connectEmailAccount(
  token: string,
  account: { label: string; imap_host: string; imap_port: number; smtp_host: string; smtp_port: number; username: string; password: string },
) {
  return request<EmailAccount>("/email-accounts", { method: "POST", token, body: JSON.stringify(account) });
}

export function listEmailAccounts(token: string) {
  return request<EmailAccount[]>("/email-accounts", { token });
}

export function deleteEmailAccount(token: string, accountId: string) {
  return request<void>(`/email-accounts/${accountId}`, { method: "DELETE", token });
}

// ---------------------------------------------------------------------------
// Découverte automatique
// ---------------------------------------------------------------------------

export type DiscoverySource = {
  id: string;
  type: "ats_greenhouse" | "ats_lever" | "imap";
  label: string;
  status: string;
  last_run_at: string | null;
  // Deux formes possibles cote backend (discovery_service.run) : un passage
  // reussi ecrit {found, new, queued} ; une erreur (API tierce injoignable,
  // board_token invalide...) ecrit {error} a la place -- jamais les deux a
  // la fois. Les distinguer explicitement plutot que de lire .found a
  // l'aveugle (ce qui affichait des nombres vides sur une source en erreur,
  // bug trouve le 2026-08-15).
  last_run_summary: { found: number; new: number; queued: number } | { error: string } | null;
};

export type DiscoveryRunResult = {
  sources_checked: number;
  postings_found: number;
  new_postings: number;
  queued: number;
  errors: string[];
};

export type ApplicationStatus =
  | "queued"
  | "sent"
  | "viewed"
  | "contacted"
  | "interview_scheduled"
  | "offer_received"
  | "rejected";

export type Candidacy = {
  id: string;
  company: string;
  title: string;
  channel: string;
  status: ApplicationStatus;
  match_score: number | null;
  notes: string | null;
  posting_url: string | null;
  cover_letter_text: string | null;
  sent_at: string | null;
  created_at: string;
};

export type KnownCompany = {
  label: string;
  type: "ats_greenhouse" | "ats_lever";
  board_token: string;
};

export function listKnownCompanies(token: string) {
  return request<KnownCompany[]>("/discovery/known-companies", { token });
}

export function addDiscoverySource(token: string, type: "ats_greenhouse" | "ats_lever", label: string, boardToken: string) {
  return request<DiscoverySource>("/discovery/sources", {
    method: "POST",
    token,
    body: JSON.stringify({ type, label, board_token: boardToken }),
  });
}

// Découverte par alertes email (2026-08-16) -- crée la source associée à un
// compte déjà connecté (voir connectEmailAccount ci-dessus).
export function addEmailAlertSource(token: string, emailAccountId: string) {
  return request<DiscoverySource>("/discovery/sources/email-alerts", {
    method: "POST",
    token,
    body: JSON.stringify({ email_account_id: emailAccountId }),
  });
}

export function listDiscoverySources(token: string) {
  return request<DiscoverySource[]>("/discovery/sources", { token });
}

export function runDiscovery(token: string) {
  return request<DiscoveryRunResult>("/discovery/run", { method: "POST", token });
}

export function listCandidacies(token: string) {
  return request<Candidacy[]>("/discovery/candidacies", { token });
}

// Rend trackable (lettre, envoi, suivi de statut) un rôle créé depuis une
// offre collée (2026-08-16) -- voir createRoleFromPosting ci-dessus, qui ne
// crée que le rôle/CV, jamais la candidature elle-même.
export function createCandidacyFromPosting(
  token: string,
  payload: { role_id: string; company: string; title: string; description: string; url?: string | null },
) {
  return request<Candidacy>("/discovery/candidacies/from-posting", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export function updateCandidacyStatus(token: string, candidacyId: string, status: ApplicationStatus) {
  return request<Candidacy>(`/discovery/candidacies/${candidacyId}`, {
    method: "PATCH",
    token,
    body: JSON.stringify({ status }),
  });
}

// Lettre de motivation adaptée à l'offre précise (2026-08-16) -- régénérable
// tant que la candidature n'est pas envoyée (voir cover_letter_service.py).
export function generateCoverLetter(token: string, candidacyId: string) {
  return request<Candidacy>(`/discovery/candidacies/${candidacyId}/cover-letter`, {
    method: "POST",
    token,
  });
}

// Édition manuelle après génération (2026-08-16) -- la lettre générée par
// l'IA est un premier jet, pas un texte figé.
export function updateCoverLetter(token: string, candidacyId: string, coverLetterText: string) {
  return request<Candidacy>(`/discovery/candidacies/${candidacyId}/cover-letter`, {
    method: "PATCH",
    token,
    body: JSON.stringify({ cover_letter_text: coverLetterText }),
  });
}

// Envoi réel canal email (2026-08-16) -- confirm=false (défaut) ne renvoie
// qu'un aperçu exact, aucune connexion SMTP, rien écrit en base ; confirm=true
// envoie réellement (voir application_send_service.py).
export type SendPreview = {
  sender: string;
  to: string;
  subject: string;
  text: string;
  attachment: string | null;
};

export type SendResult = {
  dry_run: boolean;
  preview: SendPreview | null;
  application: Candidacy | null;
};

export function sendApplication(
  token: string,
  candidacyId: string,
  payload: { email_account_id: string; recruiter_email: string; recruiter_name: string | null; confirm: boolean },
) {
  return request<SendResult>(`/discovery/candidacies/${candidacyId}/send`, {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}
