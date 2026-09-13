"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import type { COBEOptions } from "cobe";
import {
  BarChart3Icon,
  BookOpenIcon,
  GitPullRequestIcon,
  MessageSquareIcon,
  SearchIcon,
} from "lucide-react";

import { Globe } from "@/components/ui/globe";
import { useTheme } from "@/components/theme-provider";

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

const GLOBE_MARKERS = [
  { location: [14.5995, 120.9842] as [number, number], size: 0.03 },
  { location: [19.076, 72.8777] as [number, number], size: 0.1 },
  { location: [23.8103, 90.4125] as [number, number], size: 0.05 },
  { location: [30.0444, 31.2357] as [number, number], size: 0.07 },
  { location: [39.9042, 116.4074] as [number, number], size: 0.08 },
  { location: [-23.5505, -46.6333] as [number, number], size: 0.1 },
  { location: [19.4326, -99.1332] as [number, number], size: 0.1 },
  { location: [40.7128, -74.006] as [number, number], size: 0.1 },
  { location: [34.6937, 135.5022] as [number, number], size: 0.05 },
  { location: [41.0082, 28.9784] as [number, number], size: 0.06 },
];

// Two palettes instead of one static config — cobe's colors are literal
// RGB tuples, not CSS custom properties, so they can't just inherit the
// panel's `.dark` tokens automatically the way everything else here does.
const GLOBE_CONFIG_LIGHT: COBEOptions = {
  width: 800,
  height: 800,
  onRender: () => {},
  devicePixelRatio: 2,
  phi: 0,
  theta: 0.3,
  dark: 0,
  diffuse: 0.4,
  mapSamples: 16000,
  mapBrightness: 1.2,
  baseColor: [1, 1, 1],
  markerColor: [251 / 255, 100 / 255, 21 / 255],
  glowColor: [1, 1, 1],
  markers: GLOBE_MARKERS,
};

const GLOBE_CONFIG_DARK: COBEOptions = {
  ...GLOBE_CONFIG_LIGHT,
  dark: 1,
  baseColor: [0.15, 0.16, 0.19],
  glowColor: [0.25, 0.35, 0.55],
};

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
  const { theme } = useTheme();
  const globeConfig = useMemo(
    () => (theme === "dark" ? GLOBE_CONFIG_DARK : GLOBE_CONFIG_LIGHT),
    [theme],
  );

  useEffect(() => {
    const id = setInterval(() => {
      setActiveFeature((i) => (i + 1) % FEATURES.length);
    }, 2600);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="relative hidden flex-col justify-between overflow-hidden border-r border-border bg-sidebar px-10 py-12 lg:flex">
      <div className="absolute inset-x-0 -bottom-32 z-0 mx-auto aspect-square w-full max-w-130 opacity-80">
        <Globe key={theme} config={globeConfig} />
      </div>

      <span className="relative z-10 text-sm font-semibold tracking-tight">RepoMind</span>

      <div className="relative z-10 flex flex-col gap-8">
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

      <span className="relative z-10 text-xs text-muted-foreground">
        © {new Date().getFullYear()} RepoMind
      </span>
    </div>
  );
}
