# API Specification

## Live API Docs
- **Production**: [https://api.eunha.icu/docs](https://api.eunha.icu/docs)
- **Local**: [http://localhost:8000/docs](http://localhost:8000/docs)

## Offline Viewer
Open `../swagger-viewer.html` in your browser for the bundled spec.
```bash
cd ..
python -m http.server 8000
# Then open http://localhost:8000/swagger-viewer.html
```

## Spec Snapshot
`faas-backend/faas-api.yaml`
- **OpenAPI**: 1.0.0
- **Last validated**: 2025-12-07
- **Status**: ✅ Production-ready snapshot (authoritative source is the live docs above)

## Latest Changes (2025-12-07)
- IRSA-first ECR auth: `username` defaults to `AWS`, `password` optional.
- Build status accepts both `completed` and `done`.
- `function_id` is propagated to deployments for pod labels and Loki log filtering.

## Key Endpoints
### Workspaces
- `GET /api/workspaces` — list
- `POST /api/workspaces` — create
- `GET /api/workspaces/{workspace_id}` — detail
- `PATCH /api/workspaces/{workspace_id}` — update
- `DELETE /api/workspaces/{workspace_id}` — delete

### Functions
- `GET /api/workspaces/{workspace_id}/functions` — list
- `POST /api/workspaces/{workspace_id}/functions` — create (Base64 `code`)
- `GET /api/workspaces/{workspace_id}/functions/{function_id}` — detail
- `PATCH /api/workspaces/{workspace_id}/functions/{function_id}` — update/config/code
- `DELETE /api/workspaces/{workspace_id}/functions/{function_id}` — delete
- `POST /api/workspaces/{workspace_id}/functions/{function_id}/invoke` — invoke

### Logs & Metrics
- `GET /api/workspaces/{workspace_id}/logs?limit=N` — workspace recent logs
- `GET /api/workspaces/{workspace_id}/functions/{function_id}/logs?limit=N` — function logs (DynamoDB)
- `GET /api/functions/{function_id}/loki-logs?limit=N` — realtime Loki
- `GET /api/functions/{function_id}/metrics` — Prometheus CPU metrics

### Build & Deploy (Builder service proxy)
- `POST /api/v1/build` — upload + build
- `POST /api/v1/build-and-push` — build + ECR push
- `GET /api/v1/tasks/{task_id}` — poll task status
- `GET /api/v1/workspaces/{workspace_id}/tasks` — task history
- `POST /api/v1/push` — push existing artifact to ECR
- `POST /api/v1/scaffold` — generate SpinApp manifest
- `POST /api/v1/deploy` — deploy to Kubernetes (supports `function_id` label, autoscaling, spot)

## Operational Notes
- Poll long-running builder tasks every 5s for up to 10 minutes.
- Status values may include `pending | running | completed | done | failed`.
- When passing code, keep it Base64-encoded; backend decodes/validates before S3 write.

## Python Code Format (Spin)
```python
from spin_sdk import http
from spin_sdk.http import Request, Response


class IncomingHandler(http.IncomingHandler):
    def handle_request(self, request: Request) -> Response:
        return Response(
            200,
            {"content-type": "text/plain"},
            bytes("Hello from Blue FaaS!", "utf-8"),
        )
```
Reference: https://developer.fermyon.com/spin/v3/python-components

## Integration Targets
- **Builder**: https://builder.eunha.icu (REST + polling)
- **Kubernetes**: Deploy via `/api/v1/deploy`, labels with `function_id`, supports HPA/KEDA and spot
- **AWS**: DynamoDB (tasks/logs), S3 (sources/artifacts), ECR (images), IRSA for auth

## Troubleshooting
- Build fails with handler error → confirm Spin handler signature (see Python snippet).
- ECR push timeout → ensure IRSA on Builder; if not, supply valid ECR password.
- Deploy namespace missing → create namespace first: `kubectl create namespace <namespace>`.

---

**Last Updated**: 2025-12-07
**Maintainer**: Sungwoo Choi
