const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
  constructor(public status: number, public statusText: string, public data?: any) {
    super(`API Error: ${status} ${statusText}`);
  }
}

export async function fetchApi<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    let errorData;
    try {
      errorData = await response.json();
    } catch {
      errorData = null;
    }
    throw new ApiError(response.status, response.statusText, errorData);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

// --- Interfaces ---

export interface Workspace {
  id: string;
  name: string;
  description: string;
  createdAt: string;
  functionCount: number;
  invocations24h: number;
  errorRate: number;
}

export interface CreateWorkspaceData {
  name: string;
  description: string;
}

export interface UpdateWorkspaceData {
  name?: string;
  description?: string;
}

export interface FunctionItem {
  id: string;
  workspaceId: string;
  name: string;
  description: string;
  runtime: string;
  memory: number;
  timeout: number;
  httpMethods: string[];
  environmentVariables: Record<string, string>;
  code: string; // Base64 encoded string from backend
  invocationUrl: string | null;
  status: 'active' | 'building' | 'deploying' | 'failed' | 'disabled';
  lastModified: string;
  lastDeployed: string | null;
  invocations24h: number;
  errors24h: number;
  avgDuration: number;
}

export interface CreateFunctionData {
  name: string;
  description: string;
  runtime: string;
  memory: number;
  timeout: number;
  httpMethods: string[];
  environmentVariables: Record<string, string>;
  code: string; // Must be Base64 encoded
}

export interface UpdateFunctionData {
  description?: string;
  memory?: number;
  timeout?: number;
  httpMethods?: string[];
  environmentVariables?: Record<string, string>;
  code?: string; // Must be Base64 encoded
  status?: string;
  invocationUrl?: string | null;
   lastDeployed?: string | null;
}

export interface LogItem {
  id: string;
  functionId: string;
  timestamp: string;
  status: 'success' | 'error';
  duration: number;
  statusCode: number;
  requestBody?: any;
  responseBody?: any;
  logs: string[];
  level: 'info' | 'warn' | 'error';
}

export interface LokiLogEntry {
  timestamp: string;
  line: string;
}

export interface LokiLogsResponse {
  logs: LokiLogEntry[];
  total: number;
  function_id: string;
}

export interface PrometheusMetricPoint {
  timestamp: number;
  value: number;
}

export interface PrometheusMetricsData {
  cpu_total: number | null;
  cpu_series: PrometheusMetricPoint[];
  window_seconds: number;
  instant_query: string;
  range_query: string;
  raw_instant?: any;
  raw_range?: any;
}

export interface PrometheusMetricsResponse {
  status: string;
  data: PrometheusMetricsData;
  function_id: string;
}

// --- Workspace API ---

export async function getWorkspaces(): Promise<Workspace[]> {
  return fetchApi<Workspace[]>('/api/workspaces');
}

export async function createWorkspace(data: CreateWorkspaceData): Promise<Workspace> {
  return fetchApi<Workspace>('/api/workspaces', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getWorkspace(id: string): Promise<Workspace> {
  return fetchApi<Workspace>(`/api/workspaces/${id}`);
}

export async function updateWorkspace(id: string, data: UpdateWorkspaceData): Promise<Workspace> {
  return fetchApi<Workspace>(`/api/workspaces/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteWorkspace(id: string): Promise<void> {
  return fetchApi<void>(`/api/workspaces/${id}`, {
    method: 'DELETE',
  });
}

// --- Function API ---

export async function getFunctions(workspaceId: string): Promise<FunctionItem[]> {
  return fetchApi<FunctionItem[]>(`/api/workspaces/${workspaceId}/functions`);
}

export async function createFunction(workspaceId: string, data: CreateFunctionData): Promise<FunctionItem> {
  return fetchApi<FunctionItem>(`/api/workspaces/${workspaceId}/functions`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getFunction(workspaceId: string, functionId: string): Promise<FunctionItem> {
  return fetchApi<FunctionItem>(`/api/workspaces/${workspaceId}/functions/${functionId}`);
}

export async function updateFunction(workspaceId: string, functionId: string, data: UpdateFunctionData): Promise<FunctionItem> {
  return fetchApi<FunctionItem>(`/api/workspaces/${workspaceId}/functions/${functionId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteFunction(workspaceId: string, functionId: string): Promise<void> {
  return fetchApi<void>(`/api/workspaces/${workspaceId}/functions/${functionId}`, {
    method: 'DELETE',
  });
}

export interface LogsResponse {
  logs: LogItem[];
  total: number;
}

export async function getWorkspaceLogs(workspaceId: string, limit: number = 50): Promise<LogItem[]> {
  const response = await fetchApi<LogsResponse>(`/api/workspaces/${workspaceId}/logs?limit=${limit}`);
  return response.logs;
}

export async function getFunctionLogs(workspaceId: string, functionId: string): Promise<LogItem[]> {
  // Assuming the backend supports query params for limit, e.g. ?limit=100
  const response = await fetchApi<LogsResponse>(`/api/workspaces/${workspaceId}/functions/${functionId}/logs?limit=100`);
  return response.logs;
}

export async function invokeFunction(workspaceId: string, functionId: string, requestBody: any): Promise<LogItem> {
  return fetchApi<LogItem>(`/api/workspaces/${workspaceId}/functions/${functionId}/invoke`, {
    method: 'POST',
    body: JSON.stringify(requestBody),
  });
}

// --- Loki Logs API ---

export async function getLokiLogs(functionId: string, limit: number = 100): Promise<LokiLogsResponse> {
  return fetchApi<LokiLogsResponse>(`/api/functions/${functionId}/loki-logs?limit=${limit}`);
}

// --- Prometheus Metrics API ---

export async function getPrometheusMetrics(functionId: string): Promise<PrometheusMetricsResponse> {
  return fetchApi<PrometheusMetricsResponse>(`/api/functions/${functionId}/metrics`);
}

// --- Build API ---

export interface BuildTaskResult {
  wasm_path: string | null;
  image_url: string | null;
  file_path: string | null;
}

export interface BuildResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface TaskStatusResponse {
  task_id: string;
  status: 'pending' | 'running' | 'building' | 'pushing' | 'completed' | 'done' | 'failed';
  result: BuildTaskResult | null;
  error: string | null;
}

export interface WorkspaceTaskItem {
  task_id: string;
  status: string;
  app_name: string | null;
  created_at: string;
  updated_at: string;
  result: BuildTaskResult | null;
  error: string | null;
}

export interface WorkspaceTasksResponse {
  workspace_id: string;
  tasks: WorkspaceTaskItem[];
  count: number;
}

export interface PushRequest {
  registry_url: string;
  username?: string;
  password?: string | null;
  tag?: string;
  app_dir?: string;
  workspace_id?: string;
}

export interface ScaffoldRequest {
  image_ref: string;
  component?: string;
  replicas?: number;
  output_path?: string;
}

export interface ScaffoldResponse {
  success: boolean;
  yaml_content: string | null;
  file_path: string | null;
}

export interface DeployRequest {
  app_name?: string;
  namespace: string;
  service_account?: string;
  cpu_limit?: string;
  memory_limit?: string;
  cpu_request?: string;
  memory_request?: string;
  image_ref: string;
  enable_autoscaling?: boolean;
  replicas?: number;
  use_spot?: boolean;
  custom_tolerations?: any[];
  custom_affinity?: any;
  function_id?: string;
}

export interface DeployResponse {
  app_name: string;
  namespace: string;
  service_name: string;
  service_status: string;
  endpoint: string | null;
  enable_autoscaling: boolean;
  use_spot: boolean;
}

/**
 * 파일 업로드 및 빌드 시작
 */
export async function buildFromFile(
  file: File,
  appName?: string,
  workspaceId: string = 'ws-default'
): Promise<BuildResponse> {
  const formData = new FormData();
  formData.append('file', file);
  if (appName) {
    formData.append('app_name', appName);
  }
  formData.append('workspace_id', workspaceId);

  const url = `${API_BASE_URL}/api/v1/build`;
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    let errorData;
    try {
      errorData = await response.json();
    } catch {
      errorData = null;
    }
    throw new ApiError(response.status, response.statusText, errorData);
  }

  return response.json();
}

/**
 * 작업 상태 조회
 */
export async function getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  return fetchApi<TaskStatusResponse>(`/api/v1/tasks/${taskId}`);
}

/**
 * 워크스페이스의 모든 빌드 작업 조회
 */
export async function getWorkspaceTasks(workspaceId: string): Promise<WorkspaceTasksResponse> {
  return fetchApi<WorkspaceTasksResponse>(`/api/v1/workspaces/${workspaceId}/tasks`);
}

/**
 * ECR에 이미지 푸시
 */
export async function pushToECR(data: PushRequest): Promise<BuildResponse> {
  const payload: PushRequest = {
    tag: 'sha256',
    username: 'AWS',
    workspace_id: 'ws-default',
    password: 'dummy-password',
    ...data,
    // 빈 문자열/null이면 더미 값으로 덮어쓰기
    password: data.password && data.password !== '' ? data.password : 'dummy-password',
  };
  return fetchApi<BuildResponse>('/api/v1/push', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * SpinApp 매니페스트 생성
 */
export async function scaffoldSpinApp(data: ScaffoldRequest): Promise<ScaffoldResponse> {
  return fetchApi<ScaffoldResponse>('/api/v1/scaffold', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * K8s에 SpinApp 배포
 */
export async function deployToK8s(data: DeployRequest): Promise<DeployResponse> {
  return fetchApi<DeployResponse>('/api/v1/deploy', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * 빌드 및 푸시 통합
 */
export async function buildAndPush(
  file: File,
  registryUrl: string,
  username: string = 'AWS',
  password: string | null = 'dummy-password',
  tag: string = 'sha256',
  appName?: string,
  workspaceId: string = 'ws-default'
): Promise<BuildResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('registry_url', registryUrl);
  formData.append('username', username);
  formData.append('password', password || 'dummy-password');
  formData.append('tag', tag);
  if (appName) {
    formData.append('app_name', appName);
  }
  formData.append('workspace_id', workspaceId);

  const url = `${API_BASE_URL}/api/v1/build-and-push`;
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    let errorData;
    try {
      errorData = await response.json();
    } catch {
      errorData = null;
    }
    throw new ApiError(response.status, response.statusText, errorData);
  }

  return response.json();
}
