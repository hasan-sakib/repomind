import { notFound } from "next/navigation";

import { AppShell } from "@/components/shell/app-shell";
import { demoWorkspaces } from "@/lib/demo-data";

export default async function WorkspaceLayout(props: LayoutProps<"/[workspaceSlug]">) {
  const { workspaceSlug } = await props.params;

  if (!demoWorkspaces.some((w) => w.slug === workspaceSlug)) {
    notFound();
  }

  return <AppShell workspaceSlug={workspaceSlug}>{props.children}</AppShell>;
}
