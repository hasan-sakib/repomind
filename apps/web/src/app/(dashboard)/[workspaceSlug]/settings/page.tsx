import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function SettingsPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-4 px-4 py-6 sm:px-6">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">Workspace and integration settings.</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">GitHub App</CardTitle>
          <CardDescription>
            Manage which GitHub organizations and repositories RepoMind can access.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Not yet available — see docs/architecture/backend-architecture.md for the planned
          installation flow.
        </CardContent>
      </Card>
    </div>
  );
}
