"""Étape 2/2 -- fixtures de test "10 postes" (2026-08-16, voir
PROGRESSION_PHASES.md). Pour chacune des 10 personas : login réel,
création du rôle depuis l'offre collée (POST /onboarding/roles/from-posting,
vrai LLM), génération du CV (vrai), création d'une candidature en base
(posting+application -- pas d'endpoint public pour ça côté "coller une
offre", donc SQL direct), génération de la lettre (vrai LLM), aperçu
d'envoi (dry-run, vrai). Écrit un rapport JSON pour inspection manuelle des
lettres (repérer une éventuelle contamination offre->lettre, voir
cover_letter_service.py pour les deux bugs déjà trouvés et corrigés ainsi).
Suppose backend + Postgres locaux déjà lancés. Nécessite `requests` et
`asyncpg` (déjà présents dans requirements.txt).

Lancer depuis backend/ : `source .venv/bin/activate && python3 scripts/personas/2_run_persona_pipeline.py`
Rapport écrit dans scripts/personas/persona_report.json (non commité, voir .gitignore)."""
import asyncio
import json
import uuid
from pathlib import Path

import asyncpg
import requests

PERSONAS_FILE = Path(__file__).parent / "personas.json"
REPORT_FILE = Path(__file__).parent / "persona_report.json"
API = "http://127.0.0.1:8001"
DB_DSN = "postgresql://localhost/cv_autopilot_dev"


async def main():
    personas = json.load(open(PERSONAS_FILE))
    conn = await asyncpg.connect(DB_DSN)
    report = []

    for p in personas:
        entry = {"key": p["key"], "email": p["email"]}
        login = requests.post(f"{API}/auth/login", json={"email": p["email"], "password": p["password"]}, timeout=60)
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        role_resp = requests.post(
            f"{API}/onboarding/roles/from-posting", headers=headers,
            json={"title": p["posting"]["title"], "company": p["posting"]["company"], "description": p["posting"]["description"]},
            timeout=60,
        )
        if role_resp.status_code != 201:
            entry["error"] = f"role: {role_resp.status_code} {role_resp.text[:200]}"
            report.append(entry)
            print(p["key"], "-> ECHEC role", role_resp.status_code)
            continue
        role = role_resp.json()
        role_id = role["id"]
        entry["role_id"] = role_id
        entry["role_name"] = role["name"]
        entry["coverage_notes"] = role.get("coverage_notes")

        cv_resp = requests.post(f"{API}/onboarding/roles/{role_id}/generate-cv", headers=headers, timeout=60)
        entry["cv_status"] = cv_resp.status_code

        user_id = await conn.fetchval("select id from users where email = $1", p["email"])
        posting_id = await conn.fetchval(
            """insert into postings (id, user_id, source, external_id, company, title, location, url, description)
               values (gen_random_uuid(), $1, 'manual_test', $2, $3, $4, 'UAE', $5, $6) returning id""",
            user_id, f"persona-{p['key']}", p["posting"]["company"], p["posting"]["title"],
            f"https://example.com/jobs/{p['key']}", p["posting"]["description"],
        )
        application_id = await conn.fetchval(
            """insert into applications (id, user_id, posting_id, role_id, company, title, channel, status, match_score, notes)
               values (gen_random_uuid(), $1, $2, $3, $4, $5, 'platform', 'queued', 6, 'Persona de test -- 10 postes 2026-08-16')
               returning id""",
            user_id, posting_id, uuid.UUID(role_id), p["posting"]["company"], p["posting"]["title"],
        )
        entry["application_id"] = str(application_id)

        letter_resp = requests.post(f"{API}/discovery/candidacies/{application_id}/cover-letter", headers=headers, timeout=60)
        if letter_resp.status_code != 200:
            entry["error"] = f"letter: {letter_resp.status_code} {letter_resp.text[:200]}"
            report.append(entry)
            print(p["key"], "-> ECHEC lettre", letter_resp.status_code)
            continue
        entry["cover_letter_text"] = letter_resp.json()["cover_letter_text"]

        preview_resp = requests.post(
            f"{API}/discovery/candidacies/{application_id}/send", headers=headers,
            json={"email_account_id": "00000000-0000-0000-0000-000000000000", "recruiter_email": "test@example.com", "recruiter_name": None, "confirm": False},
            timeout=60,
        )
        # 404 "compte email introuvable" attendu (aucun compte email connecté pour ces
        # personas) -- prouve juste que le pipeline arrive jusque-là sans planter avant.
        entry["send_preview_status"] = preview_resp.status_code

        report.append(entry)
        print(p["key"], "-> OK, rôle:", role["name"])

    await conn.close()
    json.dump(report, open(REPORT_FILE, "w"), indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())
