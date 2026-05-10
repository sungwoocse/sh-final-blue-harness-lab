import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useApp } from '@/contexts/AppContext';
import { AppLayout } from '@/components/AppLayout';
import { WorkspaceSidebar } from '@/components/WorkspaceSidebar';
import { CodeEditor } from '@/components/CodeEditor';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Plus, X } from 'lucide-react';
import { toast } from 'sonner';

const DEFAULT_CODE = `from spin_sdk.http import IncomingHandler as BaseHandler, Request, Response


class IncomingHandler(BaseHandler):
    def handle_request(self, request: Request) -> Response:
        return Response(
            200,
            {"content-type": "text/plain"},
            bytes("Hello from Spin!", "utf-8"),
        )
`;

export default function NewFunction() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const { createFunction } = useApp();
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [memory, setMemory] = useState('256');
  const [timeout, setTimeout] = useState('30');
  const [httpMethods, setHttpMethods] = useState<string[]>(['GET', 'POST']);
  const [code, setCode] = useState(DEFAULT_CODE);
  const [envVars, setEnvVars] = useState<Array<{ key: string; value: string }>>([]);

  const handleMethodToggle = (method: string) => {
    setHttpMethods(prev =>
      prev.includes(method)
        ? prev.filter(m => m !== method)
        : [...prev, method]
    );
  };

  const handleAddEnvVar = () => {
    setEnvVars([...envVars, { key: '', value: '' }]);
  };

  const handleRemoveEnvVar = (index: number) => {
    setEnvVars(envVars.filter((_, i) => i !== index));
  };

  const handleEnvVarChange = (index: number, field: 'key' | 'value', value: string) => {
    setEnvVars(envVars.map((env, i) =>
      i === index ? { ...env, [field]: value } : env
    ));
  };

  const handleSubmit = async () => {
    if (!name.trim()) {
      toast.error(t('newFunction.actions.nameRequired'));
      return;
    }

    if (httpMethods.length === 0) {
      toast.error(t('newFunction.actions.methodRequired'));
      return;
    }

    const environmentVariables = envVars.reduce((acc, env) => {
      if (env.key.trim()) {
        acc[env.key] = env.value;
      }
      return acc;
    }, {} as Record<string, string>);

    try {
      // Step 1: Function 생성 (DynamoDB에 저장)
      toast.info('Creating function...');
      const fn = await createFunction({
        workspaceId: workspaceId!,
        name,
        description,
        runtime: 'Python 3.12',
        memory: parseInt(memory),
        timeout: parseInt(timeout),
        httpMethods,
        environmentVariables,
        code,
        status: 'building', // 빌드 중 상태
      });

      toast.success(t('newFunction.actions.success'));

      // Step 2: 빌드 & 배포 시작 (백그라운드)
      // 사용자는 Function Detail 페이지로 이동
      navigate(`/workspaces/${workspaceId}/functions/${fn.id}`);

      // Note: 실제 빌드/배포는 FunctionDetail 페이지에서 진행
      // 또는 여기서 백그라운드로 시작할 수 있음
    } catch (error) {
      console.error('Failed to create function:', error);
      toast.error('Failed to create function');
    }
  };

  return (
    <AppLayout sidebar={<WorkspaceSidebar />}>
      <div className="p-8">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">{t('newFunction.title')}</h1>
          <p className="text-muted-foreground">
            {t('newFunction.description')}
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left: Configuration */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>{t('newFunction.basicInfo.title')}</CardTitle>
                <CardDescription>{t('newFunction.basicInfo.description')}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">{t('newFunction.basicInfo.nameLabel')}</Label>
                  <Input
                    id="name"
                    placeholder={t('newFunction.basicInfo.namePlaceholder')}
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="description">{t('newFunction.basicInfo.descriptionLabel')}</Label>
                  <Textarea
                    id="description"
                    placeholder={t('newFunction.basicInfo.descriptionPlaceholder')}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label>{t('newFunction.basicInfo.runtime')}</Label>
                  <div className="flex items-center justify-between p-3 border rounded-md bg-muted">
                    <span>Python 3.12</span>
                    <span className="text-xs text-muted-foreground">{t('newFunction.basicInfo.otherLanguages')}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>{t('newFunction.httpConfig.title')}</CardTitle>
                <CardDescription>{t('newFunction.httpConfig.description')}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {['GET', 'POST', 'PUT', 'DELETE', 'PATCH'].map((method) => (
                    <div key={method} className="flex items-center space-x-2">
                      <Checkbox
                        id={method}
                        checked={httpMethods.includes(method)}
                        onCheckedChange={() => handleMethodToggle(method)}
                      />
                      <Label htmlFor={method} className="cursor-pointer">
                        {method}
                      </Label>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card className="relative overflow-hidden border-amber-200 bg-amber-50/60">
              <div className="pointer-events-none absolute inset-0">
                <div className="absolute inset-x-3 top-5 border-t-2 border-amber-300 border-dashed" />
                <div className="absolute inset-x-3 bottom-5 border-t-2 border-amber-300 border-dashed" />
              </div>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <CardTitle>{t('newFunction.resourceConfig.title')}</CardTitle>
                  <Badge variant="outline" className="text-xs uppercase">Mock</Badge>
                </div>
                <CardDescription>{t('newFunction.resourceConfig.description')}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="memory">{t('newFunction.resourceConfig.memory')}</Label>
                  <Select value={memory} onValueChange={setMemory}>
                    <SelectTrigger id="memory">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="128">128 MB</SelectItem>
                      <SelectItem value="256">256 MB</SelectItem>
                      <SelectItem value="512">512 MB</SelectItem>
                      <SelectItem value="1024">1 GB</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="timeout">{t('newFunction.resourceConfig.timeout')}</Label>
                  <Input
                    id="timeout"
                    type="number"
                    min="1"
                    max="900"
                    value={timeout}
                    onChange={(e) => setTimeout(e.target.value)}
                  />
                </div>
              </CardContent>
            </Card>

            <Card className="relative overflow-hidden border-amber-200 bg-amber-50/60">
              <div className="pointer-events-none absolute inset-0">
                <div className="absolute inset-x-3 top-5 border-t-2 border-amber-300 border-dashed" />
                <div className="absolute inset-x-3 bottom-5 border-t-2 border-amber-300 border-dashed" />
              </div>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <CardTitle>{t('newFunction.envVars.title')}</CardTitle>
                  <Badge variant="outline" className="text-xs uppercase">Mock</Badge>
                </div>
                <CardDescription>{t('newFunction.envVars.description')}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {envVars.map((env, index) => (
                  <div key={index} className="flex gap-2">
                    <Input
                      placeholder={t('newFunction.envVars.keyPlaceholder')}
                      value={env.key}
                      onChange={(e) => handleEnvVarChange(index, 'key', e.target.value)}
                    />
                    <Input
                      placeholder={t('newFunction.envVars.valuePlaceholder')}
                      value={env.value}
                      onChange={(e) => handleEnvVarChange(index, 'value', e.target.value)}
                    />
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRemoveEnvVar(index)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
                <Button variant="outline" onClick={handleAddEnvVar} className="w-full">
                  <Plus className="h-4 w-4 mr-2" />
                  {t('newFunction.envVars.addButton')}
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* Right: Code Editor */}
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>{t('newFunction.code.title')}</CardTitle>
                <CardDescription>
                  {t('newFunction.code.description')}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <CodeEditor
                  value={code}
                  onChange={setCode}
                  language="python"
                  height="600px"
                />
              </CardContent>
            </Card>
          </div>
        </div>

        <div className="flex justify-end gap-4 mt-8">
          <Button variant="outline" onClick={() => navigate(`/workspaces/${workspaceId}/functions`)}>
            {t('newFunction.actions.cancel')}
          </Button>
          <Button onClick={handleSubmit}>{t('newFunction.actions.create')}</Button>
        </div>
      </div>
    </AppLayout>
  );
}
