import { ReactNode, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useApp } from "@/contexts/AppContext";
import { Button } from "@/components/ui/button";
import { AppFooter } from "@/components/AppFooter";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Layers, ChevronDown, User, Plus, Languages } from "lucide-react";

interface AppLayoutProps {
  children: ReactNode;
  sidebar?: ReactNode;
  showWorkspaceSelector?: boolean;
}

const handleLogoClick = () => {
  window.location.href = "/"; // or window.location.replace('/')
};

export const AppLayout = ({
  children,
  sidebar,
  showWorkspaceSelector = true,
}: AppLayoutProps) => {
  const { workspaces, currentWorkspaceId, setCurrentWorkspaceId } = useApp();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { workspaceId } = useParams<{ workspaceId?: string }>();

  const currentWorkspace = workspaces.find(
    (ws) => ws.id === currentWorkspaceId
  );

  // Keep context in sync when page is loaded via deep link/refresh.
  useEffect(() => {
    if (workspaceId && workspaceId !== currentWorkspaceId) {
      setCurrentWorkspaceId(workspaceId);
    }
  }, [workspaceId, currentWorkspaceId, setCurrentWorkspaceId]);

  const changeLanguage = (lng: string) => {
    i18n.changeLanguage(lng);
  };

  // ...existing code...
  // Example: Replace hardcoded title with localized title
  // Find the location where the app title is rendered and use t('app.title')
  // For example:
  // <div className="app-title">{t('app.title')}</div>
  // ...existing code...
  return (
    <div className="min-h-screen flex flex-col w-full bg-background">
      {/* Top Bar */}
      <header className="h-14 border-b border-border bg-card flex items-center justify-between px-4 sticky top-0 z-50">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            className="flex items-center gap-2 font-semibold text-lg hover:bg-transparent"
            onClick={handleLogoClick}
          >
            <Layers className="h-5 w-5 text-primary" />
            <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
              {t("app.title")}
            </span>
          </Button>

          {showWorkspaceSelector && currentWorkspace && (
            <>
              <div className="w-px h-6 bg-border" />
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="gap-2">
                    {currentWorkspace.name}
                    <ChevronDown className="h-4 w-4 opacity-50" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="w-64">
                  <DropdownMenuLabel>
                    {t("landing.workspaces.title")}
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {workspaces.map((ws) => (
                    <DropdownMenuItem
                      key={ws.id}
                      onClick={() => {
                        setCurrentWorkspaceId(ws.id);
                        navigate(`/workspaces/${ws.id}`);
                      }}
                      className={
                        ws.id === currentWorkspaceId ? "bg-accent" : ""
                      }
                    >
                      <div className="flex flex-col">
                        <span className="font-medium">{ws.name}</span>
                        <span className="text-xs text-muted-foreground">
                          {ws.functionCount}{" "}
                          {t("landing.workspaces.functionsCount")}
                          {ws.functionCount !== 1 ? "s" : ""}
                        </span>
                      </div>
                    </DropdownMenuItem>
                  ))}
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => navigate("/")}>
                    <Plus className="h-4 w-4 mr-2" />
                    {t("landing.workspaces.createButton")}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </>
          )}
        </div>

        <div className="flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <Languages className="h-5 w-5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => changeLanguage("ko")}>
                한국어
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => changeLanguage("en")}>
                English
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => changeLanguage("ja")}>
                日本語
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="rounded-full">
                <User className="h-5 w-5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>{t("app.myAccount")}</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem>{t("app.profile")}</DropdownMenuItem>
              <DropdownMenuItem>{t("app.settings")}</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem>{t("app.signOut")}</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex flex-1 w-full">
        {sidebar && (
          <aside className="w-64 border-r border-border bg-card">
            {sidebar}
          </aside>
        )}
        <main className="flex-1 overflow-auto">{children}</main>
      </div>
      <AppFooter />
    </div>
  );
};
