"use client";

import { motion } from "framer-motion";
import {
  BarChart3Icon,
  BookOpenIcon,
  GitPullRequestIcon,
  MessageSquareIcon,
  NetworkIcon,
} from "lucide-react";

const FEATURES = [
  {
    icon: MessageSquareIcon,
    title: "Grounded AI chat",
    description:
      "Ask questions about a codebase and get answers with real file and line citations — retrieved from indexed code and commit history, not guessed.",
  },
  {
    icon: NetworkIcon,
    title: "Architecture explorer",
    description:
      "Package- and module-level dependency graphs derived from the actual import graph, with a click-to-inspect panel for symbols and dependents.",
  },
  {
    icon: GitPullRequestIcon,
    title: "Pull request intelligence",
    description:
      "Risk-level analysis grounded in the changed files, affected symbols, and existing tests — not a generic summary of the diff.",
  },
  {
    icon: BookOpenIcon,
    title: "Automatic onboarding",
    description:
      "A generated guide — architecture overview, important modules, setup steps, and a learning path — built from indexed code, with AI used only where synthesis is genuinely needed.",
  },
  {
    icon: BarChart3Icon,
    title: "Engineering analytics",
    description:
      "Commit frequency, PR throughput and cycle time, open issues, and code hotspots — computed from real repository data, no AI involved.",
  },
];

export function FeatureGrid() {
  return (
    <section className="grid grid-cols-1 gap-6 border-t border-border py-16 sm:grid-cols-2 lg:grid-cols-3">
      {FEATURES.map((feature) => (
        <motion.div
          key={feature.title}
          className="flex flex-col gap-2 rounded-lg p-3 -m-3"
          whileHover={{ y: -2 }}
          transition={{ duration: 0.15, ease: "easeOut" }}
        >
          <feature.icon className="size-5 text-muted-foreground" aria-hidden="true" />
          <h2 className="text-sm font-semibold tracking-tight">{feature.title}</h2>
          <p className="text-sm text-muted-foreground">{feature.description}</p>
        </motion.div>
      ))}
    </section>
  );
}
