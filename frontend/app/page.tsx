import Link from "next/link";

import { Button } from "@/components/ui/button";
import { FeatureGrid } from "@/components/landing/feature-grid";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col">
      <header className="mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-5 sm:px-6">
        <span className="text-sm font-semibold tracking-tight">RepoMind</span>
        <div className="flex items-center gap-2">
          <Button render={<Link href="/login" />} variant="ghost" size="sm">
            Sign in
          </Button>
          <Button render={<Link href="/register" />} size="sm">
            Create account
          </Button>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col px-4 sm:px-6">
        <section className="flex flex-col items-start gap-5 py-16 sm:py-24">
          <h1 className="max-w-2xl text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
            Codebase intelligence for the repositories you already have.
          </h1>
          <p className="max-w-xl text-base text-muted-foreground">
            Connect a GitHub repository and get answers, onboarding
            documentation, and architecture insight grounded in the actual
            code — not a generic AI chat wrapper.
          </p>
          <div className="flex gap-2 pt-2">
            <Button render={<Link href="/register" />}>Create account</Button>
            <Button render={<Link href="/login" />} variant="outline">
              Sign in
            </Button>
          </div>
        </section>

        <FeatureGrid />
      </main>

      <footer className="mx-auto w-full max-w-5xl px-4 py-6 text-xs text-muted-foreground sm:px-6">
        RepoMind
      </footer>
    </div>
  );
}
