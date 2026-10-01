# 🔍 Prompt — Recherche d'entreprises pour la watchlist CV Autopilot

**Statut** : à lancer dans Manus (ou ChatGPT/Claude avec recherche web)
**Objectif** : trouver des entreprises à ajouter dans `discovery_watchlist.json`

---

## PROMPT

```
Act as a job market researcher. I am Erman, bilingual (French/English),
based in Abu Dhabi UAE, open to: UAE-based roles, remote worldwide, or
relocation — with a specific interest in francophone Africa (Cameroon,
Senegal, Côte d'Ivoire...), Sub-Saharan Africa broadly (Kenya, Nigeria,
South Africa...), and France/Belgium, in addition to the Gulf. My profile
spans: Data Analyst, Data Engineer, Data Scientist, ML/AI Engineer, SEO/GEO
Specialist, WordPress/Web Manager, Microsoft 365 Admin, AI
Automation/Workflow Engineer.

Do NOT limit results to UAE or US companies only — actively search for
companies based in or hiring for Africa and francophone Europe too.

Goal: find companies that (a) hire for these kinds of roles, AND (b) use
Greenhouse (careers page contains "greenhouse.io") or Lever (careers page
contains "lever.co") as their public applicant tracking system — this is
a hard requirement, not optional. Companies using only LinkedIn/Indeed/
Workday/their own custom form don't work for this.

Search public forums and communities for real, current recommendations —
not generic job board listings. Specifically check:
- Reddit: r/dubai, r/UAE, r/datascience, r/cscareerquestions, r/forhire
- Blind (teamblind.com) — threads about UAE tech jobs, remote hiring
- Quora — "which companies hire remote data/AI roles"
- Hacker News "Who's Hiring" monthly threads (news.ycombinator.com)
- Glassdoor / Comparably discussion sections

For each company you find, give me exactly this, one block per company:
1. Company name
2. Careers page URL (must contain "greenhouse.io" or "lever.co")
3. Board token/slug (the part of the URL right after greenhouse.io/ or
   lever.co/ — e.g. for jobs.lever.co/palantir, the token is "palantir")
4. Why it's relevant (role types currently open, location)
5. Source (which forum/thread led you to it)

Give me at least 15 companies, spread across these regions — don't cluster
them all in one place:
1. UAE / Gulf (Dubai, Abu Dhabi)
2. Sub-Saharan Africa (Kenya, Nigeria, South Africa, and francophone Africa
   specifically: Cameroon, Senegal, Côte d'Ivoire, DRC...)
3. France / Belgium
4. Remote-friendly international companies open to relocation or visa
   sponsorship, regardless of HQ location

Bonus relevance (not required): HealthTech, AI/ML, EdTech, or companies
explicitly serving African markets.

Exclude: companies with no active data/tech/AI-adjacent openings right now.
```

---

## Une fois les résultats reçus

1. Colle le résultat brut de Manus dans `RESULTATS_RECHERCHE_ENTREPRISES.md`,
   section "À vérifier".
2. Vérifie chaque token avant de l'activer — colle dans un terminal :
   ```bash
   curl -s "https://boards-api.greenhouse.io/v1/boards/<token>/jobs" | head -c 200
   # ou pour Lever :
   curl -s "https://api.lever.co/v0/postings/<token>?mode=json" | head -c 200
   ```
   Si ça renvoie une erreur ou `{"ok":false,...}`, le token est faux — Manus se
   trompe parfois sur l'URL exacte.
3. Ajoute chaque entreprise valide dans `discovery_watchlist.json` :
   ```json
   { "provider": "greenhouse", "board_token": "...", "company_display_name": "..." }
   ```
   ou `"provider": "lever"` selon le cas, puis teste :
   ```bash
   python -m engine.cli run-discovery --client data-erman
   ```

Historique des entreprises déjà trouvées et vérifiées :
voir [`RESULTATS_RECHERCHE_ENTREPRISES.md`](RESULTATS_RECHERCHE_ENTREPRISES.md).
