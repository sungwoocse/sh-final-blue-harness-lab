import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useApp } from "@/contexts/AppContext";
import { AppLayout } from "@/components/AppLayout";
import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Layers, Plus, TrendingUp, AlertCircle, Calendar } from "lucide-react";
import { toast } from "sonner";

export default function Landing() {
  const { workspaces, createWorkspace, setCurrentWorkspaceId } = useApp();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [newWorkspaceDescription, setNewWorkspaceDescription] = useState("");

  const handleCreateWorkspace = async () => {
    if (!newWorkspaceName.trim()) {
      toast.error(t("landing.createDialog.nameRequired"));
      return;
    }

    try {
      const workspace = await createWorkspace(
        newWorkspaceName,
        newWorkspaceDescription
      );

      setCurrentWorkspaceId(workspace.id);
      setIsCreateDialogOpen(false);
      setNewWorkspaceName("");
      setNewWorkspaceDescription("");

      toast.success(t("landing.createDialog.success"));

      navigate(`/workspaces/${workspace.id}`);
    } catch (error) {
      console.error("Failed to create workspace:", error);
      toast.error(
        t(
          "landing.createDialog.error",
          "Failed to create workspace. Please try again."
        )
      );
    }
  };

  return (
    <AppLayout showWorkspaceSelector={false}>
      <div className="max-w-7xl mx-auto p-8">
        {/* Hero Section */}
        <div className="text-center mb-16 py-12">
          <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent">
            {t("landing.hero.title")}
          </h1>
          <p className="text-xl text-muted-foreground mx-auto whitespace-nowrap">
            {t("landing.hero.subtitle")}
          </p>
        </div>

        {/* Workspaces Section */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-3xl font-bold">
                {t("landing.workspaces.title")}
              </h2>
              <p className="text-muted-foreground mt-1">
                {t("landing.workspaces.description")}
              </p>
            </div>
            <Button onClick={() => setIsCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              {t("landing.workspaces.createButton")}
            </Button>
          </div>

          {workspaces.length === 0 ? (
            <EmptyState
              icon={Layers}
              title={t("landing.workspaces.emptyTitle")}
              description={t("landing.workspaces.emptyDescription")}
              actionLabel={t("landing.workspaces.emptyAction")}
              onAction={() => setIsCreateDialogOpen(true)}
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {workspaces.map((workspace) => (
                <Card
                  key={workspace.id}
                  className="hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => {
                    setCurrentWorkspaceId(workspace.id);
                    navigate(`/workspaces/${workspace.id}`);
                  }}
                >
                  <CardHeader>
                    <CardTitle className="flex items-start justify-between">
                      <span>{workspace.name}</span>
                      <Badge variant="secondary">
                        {workspace.functionCount}{" "}
                        {t("landing.workspaces.functionsCount")}
                      </Badge>
                    </CardTitle>
                    {workspace.description && (
                      <CardDescription>{workspace.description}</CardDescription>
                    )}
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-sm">
                        <Calendar className="h-4 w-4 text-muted-foreground" />
                        <span className="text-muted-foreground">
                          {t("landing.workspaces.createdAt")}{" "}
                          {workspace.createdAt.toLocaleDateString()}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <TrendingUp className="h-4 w-4 text-success" />
                        <span className="text-muted-foreground">
                          {workspace.invocations24h.toLocaleString()}{" "}
                          {t("landing.workspaces.invocations24h")}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <AlertCircle className="h-4 w-4 text-destructive" />
                        <span className="text-muted-foreground">
                          {workspace.errorRate.toFixed(2)}%{" "}
                          {t("landing.workspaces.errorRate")}
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Create Workspace Dialog */}
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t("landing.createDialog.title")}</DialogTitle>
              <DialogDescription>
                {t("landing.createDialog.description")}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="name">
                  {t("landing.createDialog.nameLabel")}
                </Label>
                <Input
                  id="name"
                  placeholder={t("landing.createDialog.namePlaceholder")}
                  value={newWorkspaceName}
                  onChange={(e) => setNewWorkspaceName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">
                  {t("landing.createDialog.descriptionLabel")}
                </Label>
                <Textarea
                  id="description"
                  placeholder={t("landing.createDialog.descriptionPlaceholder")}
                  value={newWorkspaceDescription}
                  onChange={(e) => setNewWorkspaceDescription(e.target.value)}
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setIsCreateDialogOpen(false)}
              >
                {t("landing.createDialog.cancel")}
              </Button>
              <Button onClick={handleCreateWorkspace}>
                {t("landing.createDialog.create")}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </AppLayout>
  );
}
