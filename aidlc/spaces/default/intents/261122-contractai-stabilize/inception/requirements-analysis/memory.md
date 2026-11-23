# Requirements Analysis — Memory

> **Stage**: requirements-analysis | **Phase**: inception | **Intent**: 261122-contractai-stabilize
> **Date**: 2026-11-23 | **Agent**: atlas (Tech Lead)
> **Baseline**: Commit ac31c4e

---

## Objetivo
Levantar requisitos do estado atual, identificar gaps, priorizar trabalho futuro e definir critérios de aceite para estabilização do ContractAI.

---

## Requisitos Funcionais (Estado Atual)

### Implementados ✅

| ID | Requisito | Status | Endpoint/Componente |
|----|-----------|--------|---------------------|
| RF-001 | Cadastro de organização | ✅ | `POST /api/v1/auth/register` |
| RF-002 | Login/Logout | ✅ | `POST /api/v1/auth/login`, `/logout`, `/refresh` |
| RF-003 | MFA (TOTP) | ✅ | `POST /api/v1/auth/mfa/enable` |
| RF-004 | CRUD Contratos | ✅ | `GET/POST /api/v1/contracts`, `GET /api/v1/contracts/{id}` |
| RF-005 | Upload de documentos | ✅ | `POST /api/v1/contracts/upload` |
| RF-006 | Análise de contratos (async) | ✅ | `POST /api/v1/analysis`, `GET /api/v1/analysis/{id}` |
| RF-007 | Busca semântica de cláusulas | ✅ | `POST /api/v1/clauses/search` |
| RF-008 | Listagem de cláusulas | ✅ | `GET /api/v1/clauses` |
| RF-009 | Relatórios organizacionais | ✅ | `GET /api/v1/reports/organization/summary` |
| RF-010 | Conectores (Google Drive, OneDrive) | ⚠️ Parcial | `GET/POST /api/v1/connectors` |
| RF-011 | Gestão de usuários | ✅ | `GET/POST/PUT /api/v1/users` |
| RF-012 | Gestão de organizações | ✅ | `GET/POST/PUT /api/v1/organizations` |
| RF-013 | Exportação dados (LGPD) | ✅ | `POST /api/v1/auth/data/export` |
| RF-014 | Exclusão dados (LGPD) | ✅ | `POST /api/v1/auth/data/delete` |
| RF-015 | Health checks | ✅ | `GET /health`, `/health/ready` |
| RF-016 | Métricas Prometheus | ✅ | `GET /metrics` |
| RF-017 | Frontend: Login, Dashboard, CRUDs | ✅ | Next.js App Router |

### Não Implementados / Parciais ❌

| ID | Requisito | Status | Observação |
|----|-----------|--------|------------|
| RF-018 | CI/CD Pipeline | ❌ | Ausente |
| RF-019 | Testes automatizados em CI | ❌ | Apenas manual |
| RF-020 | Testes integração (PG/pgvector) | ❌ | Apenas local |
| RF-021 | Cobertura de código medida | ⚠️ | Parcial |
| RF-022 | Deploy automatizado | ❌ | Manual |
| RF-023 | Rollback automatizado | ❌ | Manual |
| RF-024 | Observabilidade completa | ⚠️ | Métricas básicas apenas |
| RF-025 | Alertas/Alerting | ❌ | Ausente |
| RF-026 | Rate limiting em carga | ⚠️ | Não validado |
| RF-027 | Hermes integration testada | ❌ | Código existe, não validado |
| RF-028 | OAuth Connectors testados | ❌ | Configurado, não testado |

---

## Requisitos Não-Funcionais (Estado Atual)

| ID | Requisito | Estado Atual | Target | Gap |
|----|-----------|--------------|--------|-----|
| NFR-001 | Latência API (p99) | Não medida | < 500ms | Medir |
| NFR-002 | Throughput | Não medido | > 100 req/s | Medir |
| NFR-003 | Disponibilidade | Não medida | 99.9% | Implementar SLA |
| NFR-004 | Latência análise (async) | Não medida | < 30s (p95) | Medir |
| NFR-005 | Throughput Celery | Não medido | > 10 jobs/s | Medir |
| NFR-006 | Cobertura unit tests | Não medida | ≥ 80% | Medir + completar |
| NFR-006 | Cobertura integration tests | 0% | ≥ 70% | Implementar |
| NFR-007 | Cobertura E2E tests | 33/33 manual | 100% automatizado | Automatizar |
| NFR-008 | Build time | Não medido | < 5 min | Otimizar |
| NFR-008 | Deploy time | Manual | < 10 min | Automatizar |
| NFR-009 | Rollback time | Manual | < 5 min | Automatizar |
| NFR-010 | LGPD export time | Não medido | < 30s | Medir |
| NFR-010 | LGPD delete time | Não medido | < 5 min | Medir |
| NFR-011 | Segurança (SAST/SCA) | Não executado | 0 HIGH/CRITICAL | Implementar |
| NFR-012 | Secrets scan | Não executado | 0 findings | Implementar |
| NFR-013 | Container scan | Não executado | 0 CRITICAL | Implementar |
| NFR-014 | LGPD export completeness | Não validado | 100% dados | Validar |
| NFR-015 | Audit log retention | 2555 dias | 2555 dias | ✅ OK |

---

## Gaps Priorizados (Backlog de Estabilização)

### Crítico (P0)
| Item | Descrição | Esforço Estimado | Dependências |
|------|-----------|------------------|--------------|
| CI/CD Pipeline | GitHub Actions / Harness com quality gates | 2-3 dias | ADR-006 |
| Testes Integração PG/pgvector | pytest + testcontainers / Docker Compose | 2 dias | PostgreSQL 15+ pgvector |
| Testes E2E Automatizados | Playwright em CI | 2 dias | Frontend build |
| Security Scans (SAST/SCA/Secrets) | Pipeline steps | 1 dia | Pipeline |

### Alto (P1)
| Item | Descrição | Esforço Estimado | Dependências |
|------|-----------|------------------|--------------|
| Cobertura unit tests ≥ 80% | Completar gaps | 3-5 dias | - |
| Cobertura integration tests ≥ 70% | Implementar suite | 3-5 dias | PG/pgvector CI |
| E2E automatizado ≥ 90% | Playwright full suite | 3 dias | CI |
| Deploy automatizado | GitHub Actions / Harness deploy | 2 dias | Pipeline |
| Rollback automatizado | < 5 min | 1 dia | Deploy |
| Security Scans (SAST/SCA/Secrets) | Pipeline steps | 1 dia | Pipeline |
| Rate limiting validation | Load test | 1 dia | Ambiente QA |

### Médio (P2)
| Item | Descrição | Esforço Estimado | Dependências |
|------|-----------|------------------|--------------|
| Observabilidade completa | Logs estruturados, traces, dashboards | 3 dias | - |
| Alerting | PagerDuty/Slack alerts | 2 dias | Observabilidade |
| Hermes integration test | Validar endpoints | 1 dia | Credenciais |
| OAuth Connectors test | Google/OneDrive | 2 dias | Credenciais reais |
| LGPD export/delete validation | Testes completos | 2 dias | Dados seed |
| Documentação API | OpenAPI/Swagger completo | 1 dia | - |

### Baixo (P3)
| Item | Descrição | Esforço Estimado |
|------|-----------|------------------|
| Documentação arquitetura | Diagramas C4 atualizados | 1 dia |
| Runbooks | Operação, incident response | 2 dias |
| Chaos engineering | Resilience testing | 3 dias |
| Performance baselines | Benchmarks documentados | 1 dia |

---

## Critérios de Aceite para Estabilização (Definition of Done)

### Estabilização Mínima (Milestone 1)
- [ ] CI/CD Pipeline funcional com quality gates
- [ ] Testes unitários ≥ 80% cobertura (backend)
- [ ] Testes integração PG/pgvector em CI
- [ ] Testes E2E automatizados (Playwright) em CI
- [ ] Security scans (SAST/SCA/Secrets) em CI
- [ ] Deploy automatizado (staging)
- [ ] Rollback testado (< 5 min)

### Estabilização Completa (Milestone 2)
- [ ] Cobertura integration tests ≥ 70%
- [ ] Observabilidade completa (logs, metrics, traces, alerting)
- [ ] Deploy production automatizado + rollback < 5 min
- [ ] LGPD export/delete validados end-to-end
- [ ] Hermes integration testado
- [ ] OAuth Connectors testados
- [ ] Documentação API completa (OpenAPI)
- [ ] Runbooks básicos (deploy, rollback, incident)
- [ ] Performance baselines documentados

---

## Riscos de Requisitos

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Escopo crescer indefinidamente | Alta | Médio | Definition of Done clara, scope freeze por milestone |
| Dependências externas (LLM, OAuth) falharem | Média | Alta | Mocks em testes, fallback gracioso, timeouts |
| pgvector incompatibilidade versões | Baixa | Alta | Pin versions, testcontainers com versão fixa |
| Rate limiting quebrar CI | Média | Média | Desabilitar/eleva limite em ambiente CI |
| Dados sensíveis em testes | Baixa | Crítica | Apenas dados sintéticos, .env.test isolado |

---

## Decisões de Requisitos (Registradas)

| Decisão | Status | Rationale |
|---------|--------|-----------|
| SQLite para dev, PostgreSQL/pgvector para CI/prod | Confirmado | Custo/velocidade dev vs fidelidade prod |
| Testes unitários ≥ 80%, integração ≥ 70% | Confirmado | Padrão indústria, balanceado |
| E2E automatizado obrigatório para merge | Confirmado | Prevenção regressão frontend |
| Security scans obrigatórios em CI | Confirmado | Compliance, segurança |
| LGPD export/delete validados em CI | Confirmado | Compliance legal |
| Deploy apenas após quality gates passarem | Confirmado | Qualidade, rollback safety |

---

## Próximos Passos (AI-DLC)

1. **Domain-design**: Formalizar modelo de domínio (entidades, value objects, aggregates)
2. **Contract-design**: Definir contratos API (OpenAPI), schemas de validação, versionamento
3. **Delivery-planning**: Detalhar CI/CD pipeline, environments, deploy strategy, quality gates
4. **Approval-handoff**: Gate para prosseguir à Construction phase

---

*Requirements analysis concluído. Baseline de requisitos documentado.*