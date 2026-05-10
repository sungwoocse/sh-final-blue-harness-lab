import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useApp } from '@/contexts/AppContext';
import { AppLayout } from '@/components/AppLayout';
import { WorkspaceSidebar } from '@/components/WorkspaceSidebar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';

export default function WorkspaceSettings() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const { workspaces, updateWorkspace, deleteWorkspace } = useApp();
  const { t } = useTranslation();
  const navigate = useNavigate();

  const workspace = workspaces.find(ws => ws.id === workspaceId);

  const [name, setName] = useState(workspace?.name || '');
  const [description, setDescription] = useState(workspace?.description || '');

  if (!workspace) {
    return (
      <AppLayout>
        <div className="p-8">
          <h1 className="text-2xl font-bold">{t('workspaceSettings.notFound')}</h1>
        </div>
      </AppLayout>
    );
  }

  const handleSave = async () => {
    if (!name.trim()) {
      toast.error(t('workspaceSettings.details.nameRequired'));
      return;
    }
    try {
      await updateWorkspace(workspace.id, { name, description });
      toast.success(t('workspaceSettings.details.success'));
    } catch (error) {
      console.error("Failed to save workspace settings:", error);
      toast.error(t('workspaceSettings.details.error', 'Failed to save changes.'));
    }
  };

  const handleDelete = async () => {
    if (confirm(t('workspaceSettings.danger.deleteConfirm', { name: workspace.name }))) {
      try {
        await deleteWorkspace(workspace.id);
        toast.success(t('workspaceSettings.danger.deleteSuccess'));
        navigate('/');
      } catch (error) {
        console.error("Failed to delete workspace:", error);
        toast.error(t('workspaceSettings.danger.deleteError', 'Failed to delete workspace.'));
      }
    }
  };

  return (
    <AppLayout sidebar={<WorkspaceSidebar />}>
      <div className="p-8 max-w-3xl">
        <div className="mb-8">
          <h1 className="text-4xl font-bold">{t('workspaceSettings.title')}</h1>
          <p className="text-muted-foreground mt-1">
            {t('workspaceSettings.description')}
          </p>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>{t('workspaceSettings.details.title')}</CardTitle>
              <CardDescription>{t('workspaceSettings.details.description')}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">{t('workspaceSettings.details.nameLabel')}</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">{t('workspaceSettings.details.descriptionLabel')}</Label>
                <Textarea
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>

              <Button onClick={handleSave}>{t('workspaceSettings.details.saveButton')}</Button>
            </CardContent>
          </Card>

          <Card className="border-destructive">
            <CardHeader>
              <CardTitle>{t('workspaceSettings.danger.title')}</CardTitle>
              <CardDescription>{t('workspaceSettings.danger.description')}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h4 className="font-medium mb-2">{t('workspaceSettings.danger.deleteTitle')}</h4>
                <p className="text-sm text-muted-foreground mb-4">
                  {t('workspaceSettings.danger.deleteDescription')}
                </p>
                <Button variant="destructive" onClick={handleDelete}>
                  {t('workspaceSettings.danger.deleteButton')}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </AppLayout>
  );
}
