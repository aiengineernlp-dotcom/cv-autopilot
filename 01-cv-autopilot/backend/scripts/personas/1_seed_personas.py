"""Étape 1/2 -- fixtures de test "10 postes" (2026-08-16, voir
PROGRESSION_PHASES.md). Fast-forward le profil de chaque compte vers
l'état "confirmé", en appelant le VRAI code de service (draft_repository +
onboarding_service.confirm_draft) -- pas une insertion SQL à la main --
pour que experiences/profiles soient peuplées exactement comme un vrai
onboarding le ferait, sans repayer les appels LLM d'extraction déjà
validés ailleurs. Suppose que les 10 comptes existent déjà (signup +
entrée beta_invites) -- voir README.md dans ce dossier.

Lancer depuis backend/ : `source .venv/bin/activate && python3 scripts/personas/1_seed_personas.py`"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select  # noqa: E402

from app.db import async_session  # noqa: E402
from app.models import User  # noqa: E402
from app.repositories import draft_repository  # noqa: E402
from app.services import onboarding_service  # noqa: E402

PERSONAS_FILE = Path(__file__).parent / "personas.json"


async def main():
    personas = json.load(open(PERSONAS_FILE))
    async with async_session() as db:
        for p in personas:
            result = await db.execute(select(User).where(User.email == p["email"]))
            user = result.scalar_one_or_none()
            if user is None:
                print(f"{p['key']}: utilisateur introuvable, skip")
                continue

            await draft_repository.upsert_draft(
                db, user_id=user.id, raw_extraction=p["extraction"], conflicts=[], source_upload_ids=[],
            )
            await onboarding_service.confirm_draft(db, user_id=user.id)
            print(f"{p['key']}: profil confirmé pour {user.email}")


if __name__ == "__main__":
    asyncio.run(main())
