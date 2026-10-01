import Link from "next/link";

export const metadata = { title: "Politique de confidentialité — CV Autopilot" };

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-8">
      <h2 className="mb-2 font-[family-name:var(--font-display)] text-xl font-semibold text-text">{title}</h2>
      <div className="space-y-3 text-sm leading-relaxed text-text-soft">{children}</div>
    </section>
  );
}

export default function PrivacyPolicyPage() {
  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <Link href="/" className="mb-8 inline-block font-mono text-xs uppercase tracking-wide text-accent">
        ← CV Autopilot
      </Link>
      <h1 className="mb-2 font-[family-name:var(--font-display)] text-3xl font-semibold text-text">
        Politique de confidentialité
      </h1>
      <p className="mb-10 text-sm text-text-faint">Dernière mise à jour : 15 août 2026.</p>

      <Section title="Ce que ce document décrit">
        <p>
          CV Autopilot est actuellement en bêta privée, accessible sur invitation. Ce document décrit
          exactement ce que le service fait aujourd&rsquo;hui avec tes données — pas ce qu&rsquo;il pourrait
          faire un jour. Il sera mis à jour à chaque changement réel, pas en avance sur le produit.
        </p>
      </Section>

      <Section title="Qui traite tes données">
        <p>
          CV Autopilot (Erman Willian Tagaintchuem, Tensoratech) est responsable du traitement. Pour toute
          question, écris à <a href="mailto:ermanwilliantag@tensoratech.com">ermanwilliantag@tensoratech.com</a>.
        </p>
      </Section>

      <Section title="Ce qui est collecté, et pourquoi">
        <ul className="list-disc space-y-2 pl-5">
          <li><strong>Compte</strong> — email, nom, mot de passe (jamais stocké en clair, haché avec bcrypt). Nécessaire pour te connecter.</li>
          <li><strong>CV que tu uploades</strong> — le fichier lui-même, et le texte qui en est extrait (postes, dates, compétences, formation). Nécessaire pour générer tes CV adaptés.</li>
          <li><strong>Rôles ciblés et mots-clés</strong> — les intitulés de poste que tu choisis de viser. Nécessaire pour la recherche automatique et le matching.</li>
          <li><strong>Offres et candidatures</strong> — les offres d&rsquo;emploi trouvées automatiquement (données publiques des entreprises, pas des données te concernant) et le suivi de tes candidatures.</li>
        </ul>
      </Section>

      <Section title="Qui d'autre voit ces données">
        <p>Trois sous-traitants techniques, aucun autre :</p>
        <ul className="list-disc space-y-2 pl-5">
          <li><strong>OpenRouter</strong> — reçoit le texte de ton CV pour l&rsquo;extraction et l&rsquo;adaptation par IA. Ne conserve pas ces données au-delà du traitement de la requête (politique du sous-traitant).</li>
          <li><strong>Railway</strong> — héberge le serveur et la base de données.</li>
          <li><strong>Greenhouse et Lever</strong> — quand tu ajoutes une entreprise à surveiller, on interroge leur API publique de candidature. Aucune donnée te concernant ne leur est envoyée — c&rsquo;est un flux à sens unique (eux → nous), jamais l&rsquo;inverse tant que tu n&rsquo;as pas postulé toi-même.</li>
        </ul>
        <p>Tes données ne sont jamais vendues, ni partagées à des fins publicitaires.</p>
      </Section>

      <Section title="Ce qu'on ne fait jamais">
        <ul className="list-disc space-y-2 pl-5">
          <li>Jamais de candidature envoyée automatiquement sur une plateforme tierce (LinkedIn, Indeed...) — toujours une validation de ta part.</li>
          <li>Jamais de contenu inventé dans un CV généré — tout vient de ce que tu as toi-même fourni ou confirmé.</li>
          <li>Jamais de secret (mot de passe de boîte mail, etc.) stocké en clair — chiffré avant écriture en base.</li>
        </ul>
      </Section>

      <Section title="Combien de temps c'est gardé">
        <p>
          Tant que ton compte existe. Tu peux demander la suppression complète de ton compte et de toutes
          les données associées à tout moment, en écrivant à l&rsquo;adresse ci-dessus — traité sous 30 jours.
        </p>
      </Section>

      <Section title="Tes droits">
        <p>
          Accès, rectification, suppression, export de tes données : écris-nous, on répond directement,
          pas de formulaire à remplir pendant la bêta.
        </p>
      </Section>

      <Section title="Cookies et suivi">
        <p>
          Aucun cookie de suivi, aucun outil d&rsquo;analytics tiers. La session de connexion est gardée dans
          le stockage local de ton navigateur (localStorage), jamais partagée avec un tiers.
        </p>
      </Section>
    </main>
  );
}
