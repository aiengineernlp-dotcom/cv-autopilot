# 🏭 Produits — systèmes conçus pour être vendus

> Chaque sous-dossier est un système indépendant : construit pour un usage perso d'abord,
> mais organisé dès le départ pour être vendable à quelqu'un d'autre sans réécriture.
> Stack de référence : voir `TOOLS/MA_STACK_PERSONNELLE.md` (carte "SaaS complet").

---

## Règle de structure (pour chaque produit)

```
NN-nom-produit/
├── PRODUCT.md          ← vision, cible, pricing, roadmap perso → SaaS
├── frontend/            ← Next.js + Tailwind (une fois en construction)
├── backend/              ← FastAPI + PostgreSQL/pgvector (une fois en construction)
└── data-<toi>/           ← tes données perso = "client zéro", isolées du moteur générique
```

Isoler les données perso dans `data-<toi>/` dès le début évite que le moteur soit codé
en dur autour d'un seul profil — condition nécessaire pour vendre à un deuxième client
sans tout réécrire.

---

## Liste des produits

| # | Produit | Description | Statut | Cible |
|---|---|---|---|---|
| 01 | [cv-autopilot](01-cv-autopilot/PRODUCT.md) | Envoie et suit des candidatures CV automatiquement (email direct auto, plateformes en file de validation) | 🟡 En construction — usage perso d'abord | Chercheurs d'emploi actifs sur plusieurs profils/rôles |

---

## Quand ajouter un produit ici

Toute idée de système qui répond à un besoin récurrent — le tien ou celui d'un tiers —
et qui peut tourner de façon autonome ou semi-autonome. Créer `NN-nom-produit/PRODUCT.md`
avant d'écrire la moindre ligne de code.
