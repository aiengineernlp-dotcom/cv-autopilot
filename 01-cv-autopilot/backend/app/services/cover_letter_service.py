"""Couche : Service -- génère une lettre de motivation adaptée à une offre
précise (2026-08-16), pas un template statique par rôle comme la Phase 1
CLI (`engine/services/letter_service.py`, remplissage de [PLACEHOLDERS]
dans `data-erman/cover-letters.md`). Même logique que
`role_adaptation_service` : un appel LLM contraint aux faits déjà présents
(profil + rôle), jamais un template figé -- la lettre doit refléter le
poste précis (titre, entreprise, description de l'offre), pas juste le
rôle générique choisi par le matching.

Fait : compose le contexte (profil, faits du rôle, texte de l'offre),
appelle le LLM, écrit le brouillon sur `applications.cover_letter_text`.
Ne fait jamais : envoyer l'email (Adapter smtp_adapter, pas encore
branché), décider quand une candidature a été envoyée (Repository/Router),
requête SQL directe (délègue aux Repositories).

Recherche 2026-08-16 (voir PROGRESSION_PHASES.md) sur ce qui fait une
bonne lettre de motivation en 2026 -- injecté dans SYSTEM_PROMPT :
accroche spécifique au poste (jamais "I am writing to express interest"),
reprendre 1-2 formulations exactes de l'offre plutôt que des synonymes
génériques, UN exemple concret plutôt que tout lister (le CV fait déjà
ça), ton naturel avec contractions (un ton 100% corporate sans
contraction se repère comme généré), ~150-250 mots, clôture avec appel à
un entretien."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.llm import call_llm
from ..models import Application
from ..repositories import application_repository, posting_repository, role_repository, user_repository

SYSTEM_PROMPT = """Tu écris une lettre de motivation en anglais professionnel, adaptée à une
offre d'emploi précise, à partir des faits réels d'un candidat. Règles non négociables :

1. Tu ne peux QUE t'appuyer sur les faits fournis (résumé du rôle, bullets d'expérience,
   compétences, projets). Jamais ajouter un outil, une technologie, une métrique ou une
   réalisation qui n'y figure pas explicitement -- même si elle semblerait plausible pour
   ce poste.
2. Le texte de l'offre (titre, entreprise, description) contient ses propres exigences et
   tâches -- ce ne sont PAS des faits sur le candidat. Ne laisse JAMAIS une exigence de
   l'offre se glisser comme si le candidat l'avait déjà fait, sous prétexte qu'elle
   ressemble à une expérience réelle du candidat. Tu peux reprendre le VOCABULAIRE de
   l'offre (mots-clés exacts) pour décrire une expérience réelle du candidat, jamais
   inventer l'expérience elle-même -- y compris en combinant une compétence générale
   réelle du candidat avec une tâche précise de l'offre pour fabriquer une affirmation
   plus spécifique que les faits ne le permettent (ex: les faits disent seulement
   "Python" comme compétence et "built dashboards" comme réalisation, l'offre mentionne
   "Python for data cleaning" -- n'écris JAMAIS "I used Python for data cleaning", le
   candidat n'a jamais dit avoir fait ça précisément ; reste à "Python" et "dashboards"
   tels que les faits les décrivent, sans ajouter la tâche précise venue de l'offre).
   Même piège avec le NIVEAU DE GRAVITÉ/CONTEXTE d'une expérience réelle, pas seulement
   une compétence ou une tâche : si les faits disent "20+ patients per shift on a
   general ward" et que l'offre vise un poste en soins intensifs (ICU), n'écris JAMAIS
   "I've monitored vital signs for critically ill patients" -- un service général n'est
   PAS un service de soins intensifs, même si "vital signs monitoring" est un vrai
   mot-clé partagé ; garde le contexte réel ("general ward", pas "critically ill"),
   n'emprunte jamais le vocabulaire de gravité/spécialisation de l'offre pour redécrire
   un contexte réel différent.
3. Si l'offre demande une compétence ou une expérience que les faits fournis ne couvrent
   pas, ignore ce point plutôt que de l'inventer -- liste l'écart dans "coverage_notes".
   N'invente jamais non plus une DÉMARCHE en cours pour combler cet écart (ex: "I'm
   actively working toward obtaining [a certification/license]", "I'm currently learning
   [technologie]") -- le candidat n'a jamais dit être en train de faire ça, c'est une
   affirmation vérifiable en entretien tout aussi inventée qu'une compétence directement
   inventée. Contourne l'écart en insistant sur les faits transférables déjà réels
   (ex: reste sur "coordination de biens, suivi de leads" sans jamais mentionner la
   licence manquante ni une quelconque intention de l'obtenir), plutôt que de le nommer
   explicitement et de fabriquer un engagement à le combler.

Structure attendue (voir contraintes de forme ci-dessous) :
- Accroche : pourquoi CE poste chez CETTE entreprise précisément -- jamais "I am writing
  to express my interest in..." ni "To Whom It May Concern". Si un nom de recruteur est
  fourni, adresse-toi à lui/elle ; sinon "Dear Hiring Team,".
- Corps (1-2 paragraphes courts) : choisis 1 ou 2 exigences centrales de l'offre, reprends
  leur formulation EXACTE (pas un synonyme), et illustre chacune avec UN exemple concret
  tiré des faits du candidat -- pas une liste exhaustive de compétences, le CV joint fait
  déjà ça.
- Clôture : appelle clairement à un entretien, remercie, signature avec nom + email +
  téléphone si fournis.

Contraintes de forme :
- 150 à 250 mots pour le corps de la lettre (hors salutation/signature).
- Ton naturel et humain, contractions autorisées (I'm, I've...) -- un ton 100% corporate
  sans une seule contraction se repère comme visiblement généré par IA, à éviter.
- Jamais de formules creuses génériques ("passionate about", "proven track record",
  "synergy", "team player" sans exemple concret derrière).

Réponds UNIQUEMENT avec un objet JSON valide respectant ce schéma :

{
  "cover_letter_text": "string -- la lettre complète, salutation + corps + clôture + signature, prête à l'envoi",
  "coverage_notes": ["string -- écarts entre l'offre et les faits du candidat, non comblés, optionnel"]
}

Pas de texte avant ou après le JSON. Pas de markdown fences."""


class CoverLetterError(RuntimeError):
    """Erreur métier (déjà envoyée, réponse LLM inexploitable...) -- jamais une
    exception technique brute."""


class CoverLetterNotFoundError(CoverLetterError):
    """Distincte pour que le Router la mappe en 404 plutôt qu'en 400."""


def _role_facts(summary: str | None, bullets, projects, skills: list) -> dict:
    return {
        "summary": summary or "",
        "experience_bullets": [b for _, row in bullets for b in row.bullets],
        "projects": [{"title": p.title, "bullets": p.bullets} for p in projects],
        "skills": skills,
    }


async def generate(db: AsyncSession, *, user_id: uuid.UUID, application_id: uuid.UUID) -> Application:
    app = await application_repository.get_owned(db, application_id=application_id, user_id=user_id)
    if app is None:
        raise CoverLetterNotFoundError("Candidature introuvable")
    if app.sent_at is not None:
        # même règle que cover_letter_text "figée au moment de l'envoi" (voir
        # models/application.py) -- une lettre déjà envoyée ne se réécrit jamais,
        # même si l'utilisateur redemande une génération par erreur.
        raise CoverLetterError("Candidature déjà envoyée -- la lettre est figée, impossible de la régénérer")

    user = await user_repository.get_by_id(db, user_id)
    profile = await user_repository.get_profile(db, user_id)

    role_facts: dict = {}
    if app.role_id is not None:
        role = await role_repository.get_role(db, role_id=app.role_id, user_id=user_id)
        if role is not None:
            bullets = await role_repository.list_role_experience_bullets(db, role.id)
            projects = await role_repository.list_role_projects(db, role.id)
            role_facts = _role_facts(role.summary, bullets, projects, role.skills)

    posting_description = ""
    if app.posting_id is not None:
        posting = await posting_repository.get_by_id(db, posting_id=app.posting_id, user_id=user_id)
        if posting is not None and posting.description:
            posting_description = posting.description

    contact = {
        "name": user.full_name if user else "",
        "email": user.email if user else "",
        "phone": profile.phone if profile else None,
    }

    user_content = (
        f"Poste visé : {app.title}\n"
        f"Entreprise : {app.company}\n"
        f"Nom du recruteur (si connu, sinon utilise 'Hiring Team') : {app.recruiter_name or ''}\n\n"
        f"Description de l'offre (peut être vide -- dans ce cas, appuie-toi seulement sur le "
        f"titre/l'entreprise, et note-le dans coverage_notes) :\n{posting_description}\n\n"
        f"Faits réels du candidat pour ce rôle (JSON) :\n{role_facts}\n\n"
        f"Coordonnées du candidat pour la signature (JSON) :\n{contact}"
    )

    result = call_llm(SYSTEM_PROMPT, user_content)
    text = result.get("cover_letter_text", "").strip()
    if not text:
        raise CoverLetterError("Réponse du modèle sans texte de lettre exploitable")

    return await application_repository.set_cover_letter(db, app, text)
