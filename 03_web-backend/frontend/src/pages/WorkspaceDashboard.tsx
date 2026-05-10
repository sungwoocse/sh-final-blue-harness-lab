import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useApp } from '@/contexts/AppContext';
import { AppLayout } from '@/components/AppLayout';
import { WorkspaceSidebar } from '@/components/WorkspaceSidebar';
import { MetricsCard } from '@/components/MetricsCard';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Activity, AlertCircle, Clock, Code2, Plus } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export default function WorkspaceDashboard() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const { workspaces, functions, executionLogs, loadWorkspaceLogs } = useApp();
  const { t } = useTranslation();
  const navigate = useNavigate();

  const workspace = workspaces.find(ws => ws.id === workspaceId);
  const workspaceFunctions = functions.filter(fn => fn.workspaceId === workspaceId);

  useEffect(() => {
    if (!workspaceId) return;
    loadWorkspaceLogs(workspaceId);
  }, [workspaceId, loadWorkspaceLogs]);

  if (!workspace) {
    return (
      <AppLayout>
        <div className="p-8">
          <h1 className="text-2xl font-bold">{t('workspace.notFound')}</h1>
        </div>
      </AppLayout>
    );
  }

  const totalInvocations = workspaceFunctions.reduce((sum, fn) => sum + fn.invocations24h, 0);
  const totalErrors = workspaceFunctions.reduce((sum, fn) => sum + fn.errors24h, 0);
  const errorRate = totalInvocations > 0 ? ((totalErrors / totalInvocations) * 100).toFixed(2) : 0;
  const avgDuration = workspaceFunctions.length > 0
    ? Math.round(workspaceFunctions.reduce((sum, fn) => sum + fn.avgDuration, 0) / workspaceFunctions.length)
    : 0;

  const recentLogs = executionLogs
    .filter(log => {
      const fn = functions.find(f => f.id === log.functionId);
      return fn?.workspaceId === workspaceId;
    })
    .slice(0, 10);

  return (
    <AppLayout sidebar={<WorkspaceSidebar />}>
      <div className="p-8">
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-4xl font-bold">{workspace.name}</h1>
            <Button onClick={() => navigate(`/workspaces/${workspaceId}/functions/new`)}>
              <Plus className="h-4 w-4 mr-2" />
              {t('workspace.createFunction')}
            </Button>
          </div>
          {workspace.description && (
            <p className="text-muted-foreground">{workspace.description}</p>
          )}
        </div>

        {/* Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricsCard
            title={t('workspace.metrics.totalFunctions')}
            value={workspaceFunctions.length.toString()}
            icon={Code2}
            description={t('workspace.metrics.activeAndDisabled')}
          />
          <MetricsCard
            title={t('workspace.metrics.invocations')}
            value={totalInvocations.toLocaleString()}
            icon={Activity}
            description={t('workspace.metrics.last24h')}
          />
          <MetricsCard
            title={t('workspace.metrics.errorRate')}
            value={`${errorRate}%`}
            icon={AlertCircle}
            description={t('workspace.metrics.last24h')}
          />
          <MetricsCard
            title={t('workspace.metrics.avgDuration')}
            value={`${avgDuration} ms`}
            icon={Clock}
            description={t('workspace.metrics.acrossAll')}
          />
        </div>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle>{t('workspace.recentActivity.title')}</CardTitle>
            <CardDescription>{t('workspace.recentActivity.description')}</CardDescription>
          </CardHeader>
          <CardContent>
            {recentLogs.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                {t('workspace.recentActivity.noActivity')}
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t('workspace.recentActivity.time')}</TableHead>
                    <TableHead>{t('workspace.recentActivity.function')}</TableHead>
                    <TableHead>{t('workspace.recentActivity.status')}</TableHead>
                    <TableHead>{t('workspace.recentActivity.duration')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recentLogs.map((log) => {
                    const fn = functions.find(f => f.id === log.functionId);
                    return (
                      <TableRow 
                        key={log.id}
                        className="cursor-pointer"
                        onClick={() => navigate(`/workspaces/${workspaceId}/functions/${log.functionId}`)}
                      >
                        <TableCell className="text-muted-foreground">
                          {formatDistanceToNow(new Date(log.timestamp), { addSuffix: true })}
                        </TableCell>
                        <TableCell className="font-medium">{fn?.name || t('common.unknown')}</TableCell>
                        <TableCell>
                          <Badge variant={log.status === 'success' ? 'default' : 'destructive'}>
                            {log.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {`${log.duration} ms`}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  );
}
