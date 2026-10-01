"""Point d'entrée FastAPI. Assemble les Routers -- aucune logique métier ici."""
from __future__ import annotations

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import admin, auth, discovery, email_accounts, health, onboarding

app = FastAPI(title="CV Autopilot API")

# Dev uniquement : le frontend Next.js tourne sur une origine différente
# (localhost:3000) du backend (localhost:8001) -- sans ça, le navigateur
# bloque les requêtes (le CLI/curl utilisés jusqu'ici ne passaient pas par
# cette vérification, propre au navigateur). En prod, restreindre à
# l'origine réelle du frontend déployé.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(onboarding.router)
app.include_router(discovery.router)
app.include_router(admin.router)
app.include_router(email_accounts.router)
