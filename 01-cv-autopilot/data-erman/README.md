# 🎯 Career System — Erman Tagaintchuem

> Système complet de recherche d'emploi. Tout est ici — prompts, CVs, cover letters, tracking, LinkedIn.
> **Une seule règle** : quand tu changes d'entreprise, tu mets à jour `profile.json` et tu relances `node generate-cvs.js`.

---

## 📁 Structure du repo

```
career-prompts/
├── README.md                     ← ce fichier — point d'entrée
├── profile.json                  ← SOURCE UNIQUE — toutes tes infos personnelles
├── mapping-syllabus.md           ← quels modules étudier pour quel rôle
├── roadmap.md                    ← stratégie 12 mois, phases, certifications
├── cover-letters.md              ← 14 templates de lettre de motivation
├── tracker-candidatures.md       ← suivi de toutes tes candidatures
├── linkedin-guide.md             ← guide complet pour synchroniser LinkedIn
├── 00-CV/                        ← tous les cv
├── 01-maintenant/                ← postuler MAINTENANT
│   ├── seo-geo.md
│   ├── wordpress-web.md
│   ├── m365-sharepoint.md
│   ├── healthtech-consultant.md
│   ├── african-market.md
│   └── ai-trainer-labeler.md
│
├── 02-dans-6-mois/               ← postuler juin–sep 2026
│   ├── technical-writer.md
│   ├── ai-automation-workflow.md
│   ├── data-analyst.md
│   ├── solutions-consultant.md
│   └── edtech-specialist.md
│
└── 03-apres-formation/           ← postuler oct 2026+
    ├── product-manager.md
    ├── ml-ai-engineer.md
    └── startup-cofounder.md
```

---

## ⚡ Utilisation rapide

### Trouver un emploi dans un domaine
1. Ouvre le fichier du domaine (ex: `01-maintenant/seo-geo.md`)
2. Copie le bloc `PROMPT`
3. Colle dans **Manus / ChatGPT / Claude**
4. Note les résultats dans la section `RÉSULTATS` du fichier

### Postuler à une offre
1. Télécharge le CV correspondant (`Erman-Tagaintchuem-[role]-UAE.docx` ou `Canada.docx`)
2. Ouvre `cover-letters.md`, copie le template du rôle
3. Remplace les `[CROCHETS]` en 2 minutes
4. Enregistre la candidature dans `tracker-candidatures.md`

### Mettre à jour tes infos (nouvelle entreprise, nouveau projet)
1. Ouvre `profile.json`
2. Modifie ce qui a changé (nouvelle expérience en position 0 du tableau)
3. Relance : `node generate-cvs.js` → 28 CVs régénérés automatiquement

---

## 🗂️ Les 14 rôles couverts

| # | Rôle | Statut | CV UAE | CV Canada |
|---|---|---|---|---|
| 01 | SEO / GEO Specialist | ✅ Maintenant | ✓ | ✓ |
| 02 | WordPress / Web Manager | ✅ Maintenant | ✓ | ✓ |
| 03 | Microsoft 365 / SharePoint Admin | ✅ Maintenant | ✓ | ✓ |
| 04 | HealthTech Consultant | ✅ Maintenant | ✓ | ✓ |
| 05 | African Market Specialist | ✅ Maintenant | ✓ | ✓ |
| 06 | AI Trainer / Data Labeler | ✅ Maintenant | ✓ | ✓ |
| 07 | Technical Writer | 🟡 Juin 2026 | ✓ | ✓ |
| 08 | AI Automation / Workflow | 🟡 Sep 2026 | ✓ | ✓ |
| 09 | Data Analyst | 🟡 Juin 2026 | ✓ | ✓ |
| 10 | Solutions Consultant | 🟡 Août 2026 | ✓ | ✓ |
| 11 | EdTech Specialist | 🟡 Juin 2026 | ✓ | ✓ |
| 12 | Product Manager | 🔴 Sep 2026+ | ✓ | ✓ |
| 13 | ML / AI Engineer | 🔴 Oct 2026+ | ✓ | ✓ |
| 14 | Startup Co-founder | 🟢 Toujours | ✓ | ✓ |

---

## 📚 Documents de référence

| Fichier | Utilité |
|---|---|
| `profile.json` | Source unique — modifier pour régénérer les CVs |
| `mapping-syllabus.md` | Modules à maîtriser avant chaque rôle |
| `roadmap.md` | Phases, revenus cibles, certifications |
| `cover-letters.md` | 14 templates — remplir les crochets en 2 min |
| `tracker-candidatures.md` | Suivi de toutes les candidatures + relances |
| `linkedin-guide.md` | Titre, About, expériences, post épinglé |

---

## 🔄 Quand mettre à jour

| Événement | Action |
|---|---|
| Nouveau travail | Mettre à jour `profile.json` → relancer `generate-cvs.js` |
| Nouveau projet GitHub | Ajouter dans `profile.json` → relancer |
| Nouvelle certification | Ajouter dans `profile.json` → relancer |
| Fin d'une candidature | Mettre à jour `tracker-candidatures.md` |
| Modules terminés | Déplacer les rôles de `02-dans-6-mois` vers `01-maintenant` |

---

*Créé : Juin 2026 | Profil : Erman Willian Tagaintchuem | Abu Dhabi, UAE*
