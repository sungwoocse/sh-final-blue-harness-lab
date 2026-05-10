import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useApp } from '@/contexts/AppContext';
import { AppLayout } from '@/components/AppLayout';
import { WorkspaceSidebar } from '@/components/WorkspaceSidebar';
import { EmptyState } from '@/components/EmptyState';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Code2, Plus, Search, MoreVertical, Trash, Power } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { toast } from 'sonner';

export default function FunctionsList() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const { functions, deleteFunction, updateFunction } = useApp();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');

  const workspaceFunctions = functions.filter(fn => fn.workspaceId === workspaceId);

  const filteredFunctions = workspaceFunctions.filter(fn =>
    fn.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    fn.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleDeleteFunction = async (id: string, name: string) => {
    if (confirm(t('functions.actions.deleteConfirm', { name }))) {
      try {
        await deleteFunction(id);
        toast.success(t('functions.actions.deleteSuccess'));
      } catch (error) {
        console.error("Failed to delete function:", error);
        toast.error(t('functions.actions.deleteError', 'Failed to delete function.'));
      }
    }
  };

  const handleToggleStatus = async (id: string, currentStatus: string) => {
    const newStatus = currentStatus === 'active' ? 'disabled' : 'active';
    const statusText = newStatus === 'active' ? t('functions.actions.enabled') : t('functions.actions.disabled');
    try {
      await updateFunction(id, { status: newStatus });
      toast.success(t('functions.actions.statusSuccess', { status: statusText }));
    } catch (error) {
      console.error("Failed to update function status:", error);
      toast.error(t('functions.actions.statusError', 'Failed to update function status.'));
    }
  };

  return (
    <AppLayout sidebar={<WorkspaceSidebar />}>
      <div className="p-8">
        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-4xl font-bold">{t('functions.title')}</h1>
              <p className="text-muted-foreground mt-1">
                {t('functions.description')}
              </p>
            </div>
            <Button onClick={() => navigate(`/workspaces/${workspaceId}/functions/new`)}>
              <Plus className="h-4 w-4 mr-2" />
              {t('functions.newFunction')}
            </Button>
          </div>

          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder={t('functions.searchPlaceholder')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {workspaceFunctions.length === 0 ? (
          <EmptyState
            icon={Code2}
            title={t('functions.emptyTitle')}
            description={t('functions.emptyDescription')}
            actionLabel={t('functions.emptyAction')}
            onAction={() => navigate(`/workspaces/${workspaceId}/functions/new`)}
          />
        ) : filteredFunctions.length === 0 ? (
          <div className="text-center py-16 text-muted-foreground">
            {t('functions.noMatch')}
          </div>
        ) : (
          <div className="border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('functions.table.name')}</TableHead>
                  <TableHead>{t('functions.table.runtime')}</TableHead>
                  <TableHead>{t('functions.table.status')}</TableHead>
                  <TableHead>{t('functions.table.invocations24h')}</TableHead>
                  <TableHead>{t('functions.table.lastModified')}</TableHead>
                  <TableHead className="w-[50px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredFunctions.map((fn) => (
                  <TableRow
                    key={fn.id}
                    className="cursor-pointer"
                    onClick={() => navigate(`/workspaces/${workspaceId}/functions/${fn.id}`)}
                  >
                    <TableCell>
                      <div>
                        <div className="font-medium">{fn.name}</div>
                        {fn.description && (
                          <div className="text-sm text-muted-foreground">{fn.description}</div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{fn.runtime}</TableCell>
                    <TableCell>
                      <Badge variant={fn.status === 'active' ? 'default' : 'secondary'}>
                        {t(`common.${fn.status}`)}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {fn.invocations24h?.toLocaleString() ?? '0'}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {fn.lastModified ? new Date(fn.lastModified).toLocaleString() : '-'}
                    </TableCell>
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleToggleStatus(fn.id, fn.status)}>
                            <Power className="h-4 w-4 mr-2" />
                            {fn.status === 'active' ? t('functions.actions.disable') : t('functions.actions.enable')}
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className="text-destructive"
                            onClick={() => handleDeleteFunction(fn.id, fn.name)}
                          >
                            <Trash className="h-4 w-4 mr-2" />
                            {t('functions.actions.delete')}
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
