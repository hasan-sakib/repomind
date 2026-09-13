"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  BarChart3Icon,
  BookOpenIcon,
  GitPullRequestIcon,
  MessageSquareIcon,
  SearchIcon,
} from "lucide-react";

const FEATURES = [
  {
    icon: MessageSquareIcon,
    title: "Grounded AI chat",
    description:
      "Ask questions about a codebase and get answers with real file and line citations.",
  },
  {
    icon: GitPullRequestIcon,
    title: "Pull request intelligence",
    description:
      "Risk-level analysis grounded in the changed files, affected symbols, and existing tests.",
  },
  {
    icon: BookOpenIcon,
    title: "Automatic onboarding",
    description:
      "A generated guide — architecture overview, important modules, and a learning path.",
  },
  {
    icon: BarChart3Icon,
    title: "Engineering analytics",
    description:
      "Commit frequency, PR throughput, open issues, and code hotspots — computed from real data.",
  },
];

const EXAMPLE_PROMPTS = [
  "Explain the authentication flow",
  "What does src/router/dispatch.go do?",
  "Summarize the risk in PR #482",
  "Who owns the billing module?",
];

const TYPE_MS = 35;
const DELETE_MS = 18;
const HOLD_MS = 1400;

function TypewriterPrompt() {
  const [promptIndex, setPromptIndex] = useState(0);
  const [text, setText] = useState("");
  const [phase, setPhase] = useState<"typing" | "holding" | "deleting">("typing");

  useEffect(() => {
    const current = EXAMPLE_PROMPTS[promptIndex];
    let timeout: ReturnType<typeof setTimeout>;

    if (phase === "typing") {
      if (text.length < current.length) {
        timeout = setTimeout(() => setText(current.slice(0, text.length + 1)), TYPE_MS);
      } else {
        timeout = setTimeout(() => setPhase("deleting"), HOLD_MS);
      }
    } else {
      if (text.length > 0) {
        timeout = setTimeout(() => setText(text.slice(0, -1)), DELETE_MS);
      } else {
        setPromptIndex((i) => (i + 1) % EXAMPLE_PROMPTS.length);
        setPhase("typing");
      }
    }
    return () => clearTimeout(timeout);
  }, [text, phase, promptIndex]);

  return (
    <div className="flex items-center gap-2 rounded-lg border border-border bg-background/60 px-3 py-2.5 shadow-sm backdrop-blur-sm">
      <SearchIcon className="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
      <span className="font-mono text-xs text-foreground">
        {text}
        <span className="ml-0.5 inline-block h-3.5 w-px animate-pulse bg-foreground align-middle" />
      </span>
    </div>
  );
}

export function AuthBrandPanel() {
  const [activeFeature, setActiveFeature] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setActiveFeature((i) => (i + 1) % FEATURES.length);
    }, 2600);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="relative hidden flex-col justify-between overflow-hidden border-r border-border bg-sidebar px-10 py-12 lg:flex">
      <motion.div
        className="pointer-events-none absolute -left-24 -top-24 size-96 rounded-full bg-brand/10 blur-3xl"
        animate={{ x: [0, 40, 0], y: [0, 30, 0] }}
        transition={{ duration: 14, repeat: Infinity, ease: "easeInOut" }}
        aria-hidden="true"
      />
      <motion.div
        className="pointer-events-none absolute -bottom-32 -right-16 size-80 rounded-full bg-brand/10 blur-3xl"
        animate={{ x: [0, -30, 0], y: [0, -20, 0] }}
        transition={{ duration: 16, repeat: Infinity, ease: "easeInOut", delay: 1 }}
        aria-hidden="true"
      />

      <span className="text-sm font-semibold tracking-tight">RepoMind</span>

      <div className="flex flex-col gap-8">
        <div className="space-y-2">
          <h2 className="max-w-sm text-2xl font-semibold tracking-tight text-balance">
            Codebase intelligence for the repositories you already have.
          </h2>
          <p className="max-w-sm text-sm text-muted-foreground">
            AI codebase intelligence and developer onboarding platform.
          </p>
        </div>

        <TypewriterPrompt />

        <div className="flex flex-col gap-5">
          {FEATURES.map((feature, i) => {
            const active = i === activeFeature;
            return (
              <motion.div
                key={feature.title}
                className="flex gap-3"
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, delay: i * 0.05, ease: "easeOut" }}
              >
                <div
                  className={`mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md transition-colors duration-300 ${
                    active ? "bg-brand" : "bg-transparent"
                  }`}
                >
                  <feature.icon
                    className={`size-4 transition-colors duration-300 ${
                      active ? "text-white" : "text-muted-foreground"
                    }`}
                    aria-hidden="true"
                  />
                </div>
                <div className="space-y-0.5">
                  <h3 className="text-sm font-medium">{feature.title}</h3>
                  <p className="text-xs text-muted-foreground">{feature.description}</p>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>

      <span className="text-xs text-muted-foreground">
        © {new Date().getFullYear()} RepoMind
      </span>
    </div>
  );
}
