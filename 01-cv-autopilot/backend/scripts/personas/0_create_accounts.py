"""Étape 0/2 -- fixtures de test "10 postes" (2026-08-16, voir
PROGRESSION_PHASES.md). Ajoute les 10 emails à `beta_invites` (la bêta est
sur invitation, voir BETA_INVITE_ONLY dans .env) puis appelle le vrai
POST /auth/signup pour chacun -- de vrais comptes, pas des lignes insérées
à la main. Idempotent : relancer ne casse rien si les comptes existent déjà
(signup échoue silencieusement avec un 409 déjà géré).

Suppose backend + Postgres locaux déjà lancés.
Lancer depuis backend/ : `source .venv/bin/activate && python3 scripts/personas/0_create_accounts.py`"""
import asyncio
import json
from pathlib import Path

import asyncpg
import requests

PERSONAS_FILE = Path(__file__).parent / "personas.json"
API = "http://127.0.0.1:8001"
DB_DSN = "postgresql://localhost/cv_autopilot_dev"


async def main():
    personas = json.load(open(PERSONAS_FILE))
    conn = await asyncpg.connect(DB_DSN)

    for p in personas:
        await conn.execute(
            "insert into beta_invites (id, email, invited_by) values (gen_random_uuid(), $1, 'test-fixture') "
            "on conflict (email) do nothing",
            p["email"],
        )
    await conn.close()

    for p in personas:
        resp = requests.post(
            f"{API}/auth/signup", json={"email": p["email"], "password": p["password"], "full_name": p["full_name"]}, timeout=30,
        )
        status = "créé" if resp.status_code == 201 else f"déjà existant ou erreur ({resp.status_code})"
        print(f"{p['key']} ({p['email']}) -> {status}")


if __name__ == "__main__":
    asyncio.run(main())
