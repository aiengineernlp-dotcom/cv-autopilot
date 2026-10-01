"""Couche : UI (+ Parser pour la lecture du texte d'offre brut).

Fait : parse les arguments de la ligne de commande, lit le texte d'offre fourni par
l'utilisateur, appelle les Services (application_service, cv_generation_service),
affiche le résultat.
Ne fait jamais : lire/écrire roles.json, cover-letters.md, tracker-candidatures.md,
profile.json ou le dossier queue/ directement (Repositories), parler à Resend
directement (Adapter) — tout passe par un Service.

Exemples :

    # dry-run (rien n'est envoyé, juste un aperçu)
    python -m engine.cli apply --client data-erman \\
        --company "Acme Corp" --title "Data Analyst" \\
        --description-file offre.txt --recruiter-email hr@acme.com

    # envoi réel (canal email direct uniquement)
    python -m engine.cli apply --client data-erman \\
        --company "Acme Corp" --title "Data Analyst" \\
        --description-file offre.txt --recruiter-email hr@acme.com --send

    # candidature "plateforme" (LinkedIn/Indeed) -> jamais auto-envoyée,
    # juste préparée dans queue/ pour validation manuelle
    python -m engine.cli apply --client data-erman \\
        --company "Acme Corp" --title "Data Analyst" \\
        --description-file offre.txt --channel platform

    python -m engine.cli list-roles --client data-erman

    python -m engine.cli generate-cv ml-ai-engineer --client data-erman

    # relances J+7 dues aujourd'hui (dry-run par défaut) — à brancher sur un cron
    python -m engine.cli run-followups --client data-erman --send
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv optionnel : sans lui, l'env doit être déjà exporté

from . import config
from .repositories import roles_repository
from .services import application_service, cv_generation_service, discovery_service, followup_service


def _read_description(args) -> str:
    if args.description_file:
        return Path(args.description_file).read_text(encoding="utf-8")
    if args.description:
        return args.description
    print("Erreur : fournis --description ou --description-file", file=sys.stderr)
    sys.exit(1)


def cmd_list_roles(args):
    client = config.load_client(args.client)
    for r in roles_repository.load_roles(client):
        cv_flag = "✅ CV prêt" if r.cv_path else "❌ CV manquant"
        note = f" — {r.notes}" if r.notes else ""
        print(f"{r.id:22} {r.name:38} lettre#{r.cover_letter_number:<3} {cv_flag}{note}")


def cmd_apply(args):
    client = config.load_client(args.client)
    description = _read_description(args)

    try:
        result = application_service.process(
            client,
            company=args.company,
            title=args.title,
            description=description,
            channel=args.channel,
            country=args.country,
            recruiter_email=args.recruiter_email,
            recruiter_name=args.recruiter_name,
            role_id=args.role_id,
            from_email=args.from_email,
            send=args.send,
            force=args.force,
            notes=args.notes,
        )
    except application_service.ApplicationError as e:
        print(f"⚠️  {e}", file=sys.stderr)
        sys.exit(1)

    label = "forcé" if result.forced_role else f"score {result.match_score}"
    print(f"Rôle : {result.role.name} ({label})")

    if result.unresolved_placeholders:
        print(f"⚠️  Placeholders non résolus : {', '.join(result.unresolved_placeholders)}")
        if args.send:
            print("   → envoi réel bloqué, resté en dry-run. Complète avec --recruiter-name ou édite la lettre.")

    if result.mailer_result is not None:
        print(json.dumps(result.mailer_result, indent=2, ensure_ascii=False))
    if result.queued_to is not None:
        print(f"Préparé dans {result.queued_to} — à valider et envoyer toi-même sur la plateforme.")

    print("Loggé dans tracker-candidatures.md.")


def cmd_generate_cv(args):
    client = config.load_client(args.client)
    try:
        out_path = cv_generation_service.generate(client, args.role_id)
    except cv_generation_service.CvGenerationError as e:
        print(f"⚠️  {e}", file=sys.stderr)
        sys.exit(1)
    print(f"CV généré : {out_path}")
    print("roles.json mis à jour (status: cv_disponible).")


def cmd_run_followups(args):
    client = config.load_client(args.client)
    results = followup_service.run(client, send=args.send)

    if not results:
        print("Aucune relance due aujourd'hui.")
        return

    for r in results:
        if r.skipped_reason:
            print(f"⏭️  {r.entreprise} — {r.poste} : ignoré ({r.skipped_reason})")
        else:
            statut = "📤 envoyée" if r.sent else "🟡 dry-run"
            print(f"{statut} — {r.entreprise} ({r.poste}) → {r.to}")

    sent_count = sum(1 for r in results if r.sent)
    print(f"\n{sent_count}/{len(results)} relance(s) envoyée(s) réellement." if args.send else
          f"\n{len(results)} relance(s) due(s) — dry-run, ajoute --send pour envoyer réellement.")


def _print_discovery_results(results, empty_message: str):
    if not results:
        print(empty_message)
        return

    matched = [r for r in results if r.queued_to]
    skipped = [r for r in results if not r.queued_to]

    for r in matched:
        print(f"✅ {r.posting.company} — {r.posting.title} (rôle : {r.role_name}, score {r.score}) → {r.queued_to}")

    if skipped:
        by_company: dict[str, int] = {}
        for r in skipped:
            by_company[r.posting.company] = by_company.get(r.posting.company, 0) + 1
        summary = ", ".join(f"{n} chez {c}" for c, n in by_company.items())
        print(f"\n⏭️  {len(skipped)} offre(s) écartée(s) — {summary}")

    print(f"\n{len(matched)} candidature(s) préparée(s) dans queue/ — à valider et envoyer toi-même.")


def cmd_run_discovery(args):
    client = config.load_client(args.client)
    results = discovery_service.run(client, min_score=args.min_score, max_results=args.max_results)
    _print_discovery_results(results, "Watchlist vide, ou aucune nouvelle offre depuis le dernier passage.")


def cmd_run_gmail_discovery(args):
    client = config.load_client(args.client)
    results = discovery_service.run_from_gmail(client, min_score=args.min_score, max_results=args.max_results)
    _print_discovery_results(results, "Aucun compte Gmail configuré, ou aucune nouvelle alerte depuis le dernier passage.")


def cmd_run_imap_discovery(args):
    client = config.load_client(args.client)
    results = discovery_service.run_from_imap(client, min_score=args.min_score, max_results=args.max_results)
    _print_discovery_results(results, "Aucun compte IMAP configuré, ou aucune nouvelle alerte depuis le dernier passage.")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cv-autopilot")
    sub = p.add_subparsers(dest="command", required=True)

    lr = sub.add_parser("list-roles", help="Liste les rôles configurés pour un client")
    lr.add_argument("--client", default="data-erman")
    lr.set_defaults(func=cmd_list_roles)

    ap = sub.add_parser("apply", help="Traite une candidature : matche, prépare, envoie/queue, logue")
    ap.add_argument("--client", default="data-erman")
    ap.add_argument("--company", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--description", help="Texte de l'offre (ou utilise --description-file)")
    ap.add_argument("--description-file")
    ap.add_argument("--recruiter-email", help="Requis pour --channel email")
    ap.add_argument("--recruiter-name")
    ap.add_argument("--country", default="UAE", choices=["UAE", "Canada"])
    ap.add_argument("--channel", default="email", choices=["email", "platform"])
    ap.add_argument("--role-id", help="Force un rôle précis au lieu du matching automatique")
    ap.add_argument("--from-email", default=None)
    ap.add_argument("--send", action="store_true", help="Envoie réellement (canal email). Sans ça : dry-run.")
    ap.add_argument("--force", action="store_true", help="Continue même sans CV généré pour ce rôle")
    ap.add_argument("--notes", default="")
    ap.set_defaults(func=cmd_apply)

    gc = sub.add_parser("generate-cv", help="Génère le CV .docx d'un rôle et met à jour roles.json")
    gc.add_argument("role_id")
    gc.add_argument("--client", default="data-erman")
    gc.set_defaults(func=cmd_generate_cv)

    rf = sub.add_parser("run-followups", help="Envoie les relances J+7 dues aujourd'hui (dry-run par défaut)")
    rf.add_argument("--client", default="data-erman")
    rf.add_argument("--send", action="store_true", help="Envoie réellement. Sans ça : dry-run.")
    rf.set_defaults(func=cmd_run_followups)

    rd = sub.add_parser("run-discovery", help="Cherche des offres sur la watchlist (ATS publics), prépare les meilleures pour validation")
    rd.add_argument("--client", default="data-erman")
    rd.add_argument("--min-score", type=int, default=3)
    rd.add_argument("--max-results", type=int, default=10)
    rd.set_defaults(func=cmd_run_discovery)

    red = sub.add_parser("run-gmail-discovery", help="Cherche des offres dans les alertes Indeed et LinkedIn reçues sur un compte Gmail, prépare les meilleures pour validation")
    red.add_argument("--client", default="data-erman")
    red.add_argument("--min-score", type=int, default=3)
    red.add_argument("--max-results", type=int, default=10)
    red.set_defaults(func=cmd_run_gmail_discovery)

    rid = sub.add_parser("run-imap-discovery", help="Cherche des offres dans les alertes Indeed et LinkedIn reçues sur une boîte mail IMAP (n'importe quel hébergeur), prépare les meilleures pour validation")
    rid.add_argument("--client", default="data-erman")
    rid.add_argument("--min-score", type=int, default=3)
    rid.add_argument("--max-results", type=int, default=10)
    rid.set_defaults(func=cmd_run_imap_discovery)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "apply" and args.channel == "email" and not args.recruiter_email:
        parser.error("--recruiter-email est requis pour --channel email")

    args.func(args)


if __name__ == "__main__":
    main()
