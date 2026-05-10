import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AppProvider } from "@/contexts/AppContext";
import Landing from "./pages/Landing";
import WorkspaceDashboard from "./pages/WorkspaceDashboard";
import FunctionsList from "./pages/FunctionsList";
import NewFunction from "./pages/NewFunction";
import FunctionDetail from "./pages/FunctionDetail";
import WorkspaceSettings from "./pages/WorkspaceSettings";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <AppProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/workspaces/:workspaceId" element={<WorkspaceDashboard />} />
            <Route path="/workspaces/:workspaceId/functions" element={<FunctionsList />} />
            <Route path="/workspaces/:workspaceId/functions/new" element={<NewFunction />} />
            <Route path="/workspaces/:workspaceId/functions/:functionId" element={<FunctionDetail />} />
            <Route path="/workspaces/:workspaceId/settings" element={<WorkspaceSettings />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </AppProvider>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
