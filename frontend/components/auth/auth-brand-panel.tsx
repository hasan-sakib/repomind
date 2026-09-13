"use client";

import { useMemo } from "react";
import type { COBEOptions } from "cobe";

import { Globe } from "@/components/ui/globe";
import { useTheme } from "@/components/theme-provider";

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

export function AuthBrandPanel() {
  const { theme } = useTheme();
  const globeConfig = useMemo(
    () => (theme === "dark" ? GLOBE_CONFIG_DARK : GLOBE_CONFIG_LIGHT),
    [theme],
  );

  return (
    <div className="relative hidden items-center justify-center overflow-hidden border-r border-border bg-sidebar lg:flex">
      <div className="absolute inset-x-0 top-1/2 z-0 mx-auto aspect-square w-full max-w-130 translate-y-[-35%]">
        <Globe key={theme} config={globeConfig} />
      </div>

      <span className="pointer-events-none relative z-10 whitespace-pre-wrap bg-linear-to-b from-foreground to-foreground/10 bg-clip-text text-center text-7xl leading-none font-semibold text-transparent">
        RepoMind
      </span>

      <div className="pointer-events-none absolute inset-0 z-20 bg-[radial-gradient(circle_at_50%_200%,rgba(0,0,0,0.2),rgba(255,255,255,0))]" />
    </div>
  );
}
