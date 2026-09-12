import {
  ArchiveIcon,
  BoxIcon,
  BracesIcon,
  CogIcon,
  DatabaseIcon,
  FolderIcon,
  RouteIcon,
  type LucideIcon,
} from "lucide-react";

import type { NodeKind } from "@/lib/types";

export const KIND_ICON: Record<NodeKind | "database", LucideIcon> = {
  route: RouteIcon,
  service: CogIcon,
  repository: ArchiveIcon,
  model: BoxIcon,
  schema: BracesIcon,
  other: FolderIcon,
  database: DatabaseIcon,
};
