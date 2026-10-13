/**
 * Root placeholder page.
 *
 * This is a minimal stub to verify that Next.js, Tailwind CSS, and the
 * App Router are working correctly.
 *
 * Replace this page with real application screens as the product is built.
 */
export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-white dark:bg-zinc-950 px-6">
      <div className="flex flex-col items-center gap-4 text-center">
        <span className="inline-block rounded-full bg-zinc-100 dark:bg-zinc-800 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-zinc-500 dark:text-zinc-400">
          Frontend — Architecture Bootstrap
        </span>

        <h1 className="text-4xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
          Ready for development
        </h1>

        <p className="max-w-md text-base leading-relaxed text-zinc-500 dark:text-zinc-400">
          The Next.js App Router, TypeScript, Tailwind CSS, ESLint, and the
          Axios API client are configured. Replace this page to begin building
          application screens.
        </p>

        <div className="mt-4 flex flex-wrap items-center justify-center gap-3">
          {[
            'Next.js 16 + App Router',
            'TypeScript (strict)',
            'Tailwind CSS v4',
            'Axios',
            'ESLint',
          ].map((badge) => (
            <span
              key={badge}
              className="rounded-md border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 px-3 py-1 text-xs font-medium text-zinc-600 dark:text-zinc-300"
            >
              {badge}
            </span>
          ))}
        </div>
      </div>
    </main>
  );
}
