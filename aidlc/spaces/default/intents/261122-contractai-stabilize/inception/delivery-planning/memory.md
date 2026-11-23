# Delivery Planning — Memory

> **Stage**: delivery-planning | **Phase**: inception | **Intent**: 261122-contractai-stabilize
> **Date**: 2026-11-23 | **Agent**: atlas (Tech Lead)
> **Baseline**: Commit ac31c4e

---

## Objetivo
Definir plano de entrega: CI/CD pipeline, environments, deploy strategy, quality gates, observabilidade e runbooks para estabilização do ContractAI.

---

## CI/CD Pipeline (ADR-006 Proposto)

### Estratégia: GitHub Actions (Recomendado)
> **Rationale**: Integrado ao GitHub, gratuito para repos públicos/privados, boa integração com container registry, matrix builds.

### Pipeline Stages

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # ==========================================
  # STAGE 1: CODE QUALITY (Parallel)
  # ==========================================
  lint-and-typecheck:
    name: Lint & Type Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      - name: Install backend deps
        run: |
          cd backend
          pip install -e '.[dev]'
      - name: Run Ruff (lint)
        run: cd backend && ruff check .
      - name: Run MyPy (type check)
        run: cd backend && mypy app/
      - name: Frontend type check
        run: |
          cd frontend
          npm ci
          npm run type-check
      - name: Frontend lint
        run: cd frontend && npm run lint

  # ==========================================
  # STAGE 2: UNIT TESTS (Parallel)
  # ==========================================
  unit-tests-backend:
    name: Unit Tests (Backend)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      - name: Install deps
        run: |
          cd backend
          pip install -e '.[dev]'
      - name: Run unit tests
        run: cd backend && pytest tests/unit -v --cov=app --cov-report=xml --cov-fail-under=80
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./backend/coverage.xml

  unit-tests-frontend:
    name: Unit Tests (Frontend)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      - name: Install deps
        run: cd frontend && npm ci
      - name: Run unit tests
        run: cd frontend && npm test -- --coverage --coverageThreshold='{"global":{"lines":80}}'
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./frontend/coverage/lcov.info

  # ==========================================
  # STAGE 3: INTEGRATION TESTS (Sequential - needs DB)
  # ==========================================
  integration-tests:
    name: Integration Tests (PostgreSQL + pgvector)
    runs-on: ubuntu-latest
    needs: [lint-and-typecheck, unit-tests-backend]
    services:
      postgres:
        image: pgvector/pgvector:pg15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: contractai_test
        ports: ['5432:5432']
        options: >-
          --health-cmd="pg_isready -U test"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=5
      redis:
        image: redis:7-alpine
        ports: ['6379:6379']
        options: --health-cmd="redis-cli ping" --health-interval=10s --health-timeout=5s --health-retries=5
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      - name: Install deps
        run: |
          cd backend
          pip install -e '.[dev]'
      - name: Run migrations
        run: |
          cd backend
          alembic upgrade head
      - name: Run integration tests
        run: |
          cd backend
          pytest tests/integration -v --cov=app --cov-append --cov-report=xml --cov-fail-under=70
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./backend/coverage.xml

  # ==========================================
  # STAGE 4: CONTRACT TESTS (Consumer-Driven)
  # ==========================================
  contract-tests:
    name: Contract Tests (Pact)
    runs-on: ubuntu-latest
    needs: [lint-and-typecheck]
    steps:
      - uses: actions/checkout@v4
      # Consumer tests (Frontend)
      - name: Run consumer tests
        run: |
          cd frontend
          npm ci
          npm run test:contract
      # Provider verification (Backend)
      - name: Provider verification
        run: |
          cd backend
          pip install pact-verifier
          pact-verifier --pact-url=./pacts --provider-base-url=http://localhost:8000

  # ==========================================
  # STAGE 5: SECURITY SCANS
  # ==========================================
  security-scans:
    name: Security Scans
    runs-on: ubuntu-latest
    needs: [lint-and-typecheck]
    steps:
      - uses: actions/checkout@v4
      # SAST - Semgrep
      - name: SAST (Semgrep)
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/security-audit
            p/secrets
            p/python
            p/fastapi
      # SCA - Dependencies
      - name: SCA (Dependabot/Safety)
        run: |
          cd backend
          pip install safety
          safety check --json --output safety-report.json || true
      # Secrets
      - name: Secrets Scan (TruffleHog)
        uses: trufflesecurity/trufflehog-action@v3
        with:
          path: .
          config: |
            includePaths:
              - "backend/**/*.py"
              - "frontend/**/*.ts"
              - "frontend/**/*.tsx"
      # Container scan
      - name: Container Scan (Trivy)
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

  # ==========================================
  # STAGE 5: E2E TESTS (Playwright)
  # ==========================================
  e2e-tests:
    name: E2E Tests (Playwright)
    runs-on: ubuntu-latest
    needs: [lint-and-typecheck, unit-tests-frontend]
    services:
      postgres:
        image: pgvector/pgvector:pg15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: contractai_test
        ports: ['5432:5432']
        options: --health-cmd="pg_isready -U test" --health-interval=10s --health-timeout=5s --health-retries=5
      redis:
        image: redis:7-alpine
        ports: ['6379:6379']
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - name: Install frontend deps
        run: cd frontend && npm ci
      - name: Build frontend
        run: cd frontend && npm run build
      - name: Start backend
        run: |
          cd backend
          pip install -e '.[dev]'
          alembic upgrade head
          uvicorn app.main:app --host 0.0.0.0 --port 8000 &
          sleep 10
      - name: Start frontend
        run: |
          cd frontend
          npm run dev &
          sleep 10
      - name: Run Playwright tests
        run: |
          cd frontend
          npx playwright install --with-deps chromium
          npm run test:e2e
      - name: Upload Playwright report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: frontend/playwright-report/

  # ==========================================
  # STAGE 6: BUILD & PUSH IMAGES
  # ==========================================
  build-images:
    name: Build & Push Docker Images
    runs-on: ubuntu-latest
    needs: [integration-tests, contract-tests, security-scans, e2e-tests]
    if: github.ref == 'refs/heads/main'
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Build & Push Backend
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          push: true
          tags: ghcr.io/${{ github.repository }}/backend:${{ github.sha }},ghcr.io/${{ github.repository }}/backend:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
      - name: Build & Push Frontend
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          push: true
          tags: ghcr.io/${{ github.repository }}/frontend:${{ github.sha }},ghcr.io/${{ github.repository }}/frontend:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ==========================================
  # STAGE 7: DEPLOY STAGING
  # ==========================================
  deploy-staging:
    name: Deploy Staging
    runs-on: ubuntu-latest
    needs: [build-images]
    if: github.ref == 'refs/heads/main'
    environment: staging
    steps:
      - name: Deploy to Staging
        run: |
          # Deploy via Harness / kubectl / docker-compose
          # Health check staging
          curl -f https://staging.contractai.example.com/health/ready

  # ==========================================
  # STAGE 8: DEPLOY PRODUCTION (Manual Approval)
  # ==========================================
  deploy-production:
    name: Deploy Production
    runs-on: ubuntu-latest
    needs: [deploy-staging]
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
      - name: Manual Approval
        uses: trstringer/manual-approval@v1
        with:
          approvers: rodrigosabreu
          secret-token: ${{ secrets.GITHUB_TOKEN }}
      - name: Deploy to Production
        run: |
          # Blue-green deploy via Harness / kubectl
          # Health check production
          curl -f https://contractai.example.com/health/ready
      - name: Post-deploy smoke tests
        run: |
          # Critical path tests
          curl -f https://contractai.example.com/health
          curl -f https://contractai.example.com/health/ready
```

---

## Environments

| Environment | Branch | Deploy Trigger | URL | Purpose |
|-------------|--------|----------------|-----|---------|
| **Development** | `develop` | Auto on push | `https://dev.contractai.example.com` | Integration testing |
| **Staging** | `main` | Auto on merge to main | `https://staging.contractai.example.com` | QA, stakeholder review |
| **Production** | `main` + tag | Manual approval | `https://contractai.example.com` | Live traffic |

### Environment Variables por Ambiente

| Variável | Development | Staging | Production |
|----------|-------------|---------|------------|
| `APP_ENV` | `development` | `staging` | `production` |
| `DEBUG` | `true` | `false` | `false` |
| `DATABASE_URL` | SQLite local | PostgreSQL staging | PostgreSQL prod (pool) |
| `REDIS_URL` | Local Redis | Redis staging | Redis prod (cluster) |
| `SECRET_KEY` | Dev key | Staging key (vault) | Prod key (vault) |
| `OPENAI_API_KEY` | Dev key | Staging key | Prod key (vault) |
| `LLM_FALLBACK_ENABLED` | `true` | `false` | `false` |
| `CORS_ORIGINS` | `http://localhost:3000` | `https://staging.contractai.example.com` | `https://contractai.example.com` |

---

## Quality Gates (Por Stage)

| Stage | Gates Obrigatórios | Threshold |
|-------|-------------------|-----------|
| **PR Validation** | Lint, TypeCheck, Unit Tests | 100% pass |
| **CI (Integration)** | Integration Tests (PG/pgvector) | ≥ 70% coverage |
| **Contract Tests** | Consumer + Provider verification | 100% pass |
| **Security** | SAST/SCA/Secrets/Container | 0 CRITICAL/HIGH |
| **E2E** | Playwright critical paths | 100% pass |
| **Pre-Merge** | All above + Coverage ≥ 80% (unit) | 100% pass |
| **Pre-Deploy Staging** | All CI gates + Manual QA sign-off | Approved |
| **Pre-Deploy Production** | All Staging gates + Manual approval + Smoke tests | Approved |

---

## Observabilidade (ADR-008 Futuro)

### Métricas (Prometheus)
| Métrica | Tipo | Alert Threshold |
|---------|------|-----------------|
| `http_requests_total` | Counter | - |
| `http_request_duration_seconds` | Histogram | p99 > 500ms |
| `celery_tasks_total` | Counter | - |
| `celery_task_duration_seconds` | Histogram | p95 > 30s |
| `llm_requests_total` | Counter | - |
| `llm_tokens_total` | Counter | Cost alert > $100/day |
| `db_connections_active` | Gauge | > 80% pool |
| `redis_memory_used_bytes` | Gauge | > 80% maxmemory |

### Logs (Structured JSON)
```json
{
  "timestamp": "2026-11-23T00:00:00.123Z",
  "level": "INFO",
  "logger": "app.services.analysis",
  "message": "Analysis completed",
  "request_id": "req_abc123",
  "user_id": "usr_123",
  "organization_id": "org_456",
  "analysis_id": "ana_789",
  "duration_ms": 1234,
  "llm_provider": "openai",
  "tokens_used": 1500
}
```

### Health Checks
| Endpoint | Verifica | SLA |
|----------|----------|-----|
| `/health` | Liveness (app up) | < 1s |
| `/health/ready` | Readiness (DB, Redis, LLM) | < 2s |

### Alerting (Regras)
| Alerta | Condição | Severidade | Canal |
|--------|----------|------------|-------|
| API Down | `/health` 5xx > 5% por 5min | Critical | PagerDuty |
| High Latency | p99 > 500ms por 10min | Warning | Slack |
| High Error Rate | 5xx > 1% por 5min | Critical | PagerDuty |
| DB Pool Exhausted | `db_connections_active` > 80% | Warning | Slack |
| Celery Queue Backlog | `celery_queue_length` > 100 | Warning | Slack |
| LLM Cost Spike | `llm_cost_daily` > $100 | Warning | Slack |
| Security Scan Failed | Any CRITICAL finding | Critical | PagerDuty |

---

## Runbooks (Mínimos para Milestone 1)

| Runbook | Trigger | Ações |
|---------|---------|-------|
| **Deploy Rollback** | Deploy falhou / health check falha | 1. `kubectl rollout undo deployment/<service>` 2. Verificar `/health/ready` 3. Notificar #deploy |
| **DB Migration Rollback** | Migration falhou | 1. `alembic downgrade -1` 2. Verificar schema 3. Re-deploy anterior |
| **Celery Worker Down** | Queue backlog > 1000 | 1. `kubectl scale deployment celery-worker --replicas=N+2` 2. Investigar logs 3. Alertar #backend |
| **LLM Provider Down** | Health check LLM falha | 1. Verificar `LLM_FALLBACK_ENABLED` 2. Alternar provider 3. Alertar #ml |
| **DB Pool Exhausted** | Conexões > 80% | 1. Verificar queries longas 2. `pg_terminate_backend` idle 4. Scale pool |
| **LGPD Export Falhou** | Export endpoint 5xx | 1. Verificar logs 2. Reprocessar manual 3. Notificar DPO |

---

## Estratégia de Deploy

| Estratégia | Descrição | Quando Usar |
|------------|-----------|-------------|
| **Blue-Green** | Duas environments idênticas, switch DNS | Production (zero-downtime) |
| **Rolling** | Atualização gradual de pods | Staging/Development |
| **Canary** | 5% → 25% → 100% tráfego | Production (high-risk) |

### Blue-Green Production (Recomendado)
```bash
# 1. Deploy para environment "green" (inativo)
kubectl apply -f k8s/green/

# 2. Health checks extensivos
kubectl wait --for=condition=ready pod -l app=contractai,env=green --timeout=300s
curl -f https://green.contractai.internal/health/ready

# 3. Smoke tests automatizados
./scripts/smoke-tests.sh green

# 4. Switch traffic (DNS/Ingress)
kubectl patch ingress contractai -p '{"spec":{"rules":[{"host":"contractai.example.com","http":{"paths":[{"backend":{"serviceName":"contractai-green"}}]}}]}}'

# 5. Monitor por 10 min
# 6. Decomission blue (após confirmação)
kubectl delete -f k8s/blue/
```

---

## Rollback Strategy

| Cenário | Tempo Alvo | Procedimento |
|---------|------------|--------------|
| **Deploy falhou (health check)** | < 2 min | `kubectl rollout undo deployment/<service>` |
| **Migration falhou** | < 5 min | `alembic downgrade -1` + re-deploy anterior |
| **Bug crítico em produção** | < 10 min | Blue-Green: switch DNS para blue; Rolling: `kubectl rollout undo` |
| **Data corruption** | < 30 min | Restore backup point-in-time + re-play migrations |

### Validação de Rollback
- [ ] `/health` retorna 200
- [ ] `/health/ready` retorna 200 (DB, Redis, LLM)
- [ ] Smoke tests críticos passam
- [ ] Métricas de erro voltam ao baseline

---

## Riscos de Entrega

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| CI/CD flaky tests | Média | Alto | Quarentena flaky tests, retry logic |
| pgvector version mismatch | Baixa | Alto | Pin versions, testcontainers fixed version |
| Secrets em CI logs | Baixa | Crítico | Masked secrets, vault integration |
| Rate limit em CI | Alta | Médio | Disable rate limit em `APP_ENV=test` |
| LLM provider down em CI | Média | Baixo | Mock LLM em testes unitários |
| Flaky E2E tests | Alta | Médio | Retry 2x, screenshots on failure |
| Database migration conflict | Baixa | Alto | Review obrigatório, backup antes |
| LLM cost spike | Média | Médio | Budget alerts, fallback disabled |

---

## Próximos Passos (AI-DLC)

1. **Approval-handoff**: Gate de aprovação humana para prosseguir à Construction
2. **Construction Phase**: Functional design → Code generation → Build & test → CI pipeline → Quality gates

---

*Delivery planning documentado. Baseline para Approval Handoff.*