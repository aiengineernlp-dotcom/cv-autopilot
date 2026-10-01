"""Couche : donnée de référence statique -- liste de départ d'entreprises
connues pour la découverte automatique (2026-08-15).

Problème résolu : l'utilisateur doit normalement connaître par avance le
nom exact d'une entreprise, savoir si son ATS est Greenhouse ou Lever, et
connaître son "board token" technique -- une vraie barrière pour quelqu'un
qui ne vise pas d'entreprises précises mais cherche par poste/profil
(signalé par l'utilisateur : "le plus souvent on ne connaît pas le nom
des entreprises"). Cette liste laisse choisir par nom, le reste est
pré-rempli.

Chaque entrée a été vérifiée en réel contre l'API publique correspondante
(`curl https://boards-api.greenhouse.io/v1/boards/{token}/jobs` ou
`https://api.lever.co/v0/postings/{token}`) le 2026-08-15 -- 200 OK et au
moins un poste ouvert au moment du test. Pas une garantie permanente (une
entreprise peut fermer son board), juste un point de départ honnête,
jamais deviné à l'aveugle. Ne remplace pas l'ajout manuel (toujours
possible pour toute entreprise absente d'ici) -- volontairement non
exhaustif, à étendre au fil du temps plutôt que d'inventer une couverture
large qui ne serait pas vérifiée.

Ne fait jamais : appeler un Adapter (cette liste est statique, la
vérification a été faite manuellement avant de l'écrire, pas à chaque
lecture)."""
from __future__ import annotations

KNOWN_COMPANIES: list[dict[str, str]] = [
    # Greenhouse -- triées par nom affiché
    {"label": "Affirm", "type": "ats_greenhouse", "board_token": "affirm"},
    {"label": "Airbnb", "type": "ats_greenhouse", "board_token": "airbnb"},
    {"label": "Anthropic", "type": "ats_greenhouse", "board_token": "anthropic"},
    {"label": "Asana", "type": "ats_greenhouse", "board_token": "asana"},
    {"label": "Attentive", "type": "ats_greenhouse", "board_token": "attentive"},
    {"label": "Brex", "type": "ats_greenhouse", "board_token": "brex"},
    {"label": "Cloudflare", "type": "ats_greenhouse", "board_token": "cloudflare"},
    {"label": "Coinbase", "type": "ats_greenhouse", "board_token": "coinbase"},
    {"label": "Databricks", "type": "ats_greenhouse", "board_token": "databricks"},
    {"label": "Datadog", "type": "ats_greenhouse", "board_token": "datadog"},
    {"label": "Discord", "type": "ats_greenhouse", "board_token": "discord"},
    {"label": "Doximity", "type": "ats_greenhouse", "board_token": "doximity"},
    {"label": "Dropbox", "type": "ats_greenhouse", "board_token": "dropbox"},
    {"label": "Elastic", "type": "ats_greenhouse", "board_token": "elastic"},
    {"label": "Figma", "type": "ats_greenhouse", "board_token": "figma"},
    {"label": "GitLab", "type": "ats_greenhouse", "board_token": "gitlab"},
    {"label": "Instacart", "type": "ats_greenhouse", "board_token": "instacart"},
    {"label": "JFrog", "type": "ats_greenhouse", "board_token": "jfrog"},
    {"label": "Lyft", "type": "ats_greenhouse", "board_token": "lyft"},
    {"label": "MongoDB", "type": "ats_greenhouse", "board_token": "mongodb"},
    {"label": "New Relic", "type": "ats_greenhouse", "board_token": "newrelic"},
    {"label": "PagerDuty", "type": "ats_greenhouse", "board_token": "pagerduty"},
    {"label": "Pinterest", "type": "ats_greenhouse", "board_token": "pinterest"},
    {"label": "Reddit", "type": "ats_greenhouse", "board_token": "reddit"},
    {"label": "Robinhood", "type": "ats_greenhouse", "board_token": "robinhood"},
    {"label": "Roblox", "type": "ats_greenhouse", "board_token": "roblox"},
    {"label": "Scale AI", "type": "ats_greenhouse", "board_token": "scaleai"},
    {"label": "Squarespace", "type": "ats_greenhouse", "board_token": "squarespace"},
    {"label": "Stripe", "type": "ats_greenhouse", "board_token": "stripe"},
    {"label": "Twilio", "type": "ats_greenhouse", "board_token": "twilio"},
    {"label": "Webflow", "type": "ats_greenhouse", "board_token": "webflow"},
    {"label": "Zscaler", "type": "ats_greenhouse", "board_token": "zscaler"},
    # Lever
    {"label": "Palantir", "type": "ats_lever", "board_token": "palantir"},
    {"label": "Rigetti Computing", "type": "ats_lever", "board_token": "rigetti"},
    {"label": "Spotify", "type": "ats_lever", "board_token": "spotify"},
    {"label": "Wealthfront", "type": "ats_lever", "board_token": "wealthfront"},
]
