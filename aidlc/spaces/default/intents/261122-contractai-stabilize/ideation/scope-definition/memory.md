# Scope Definition — Memory

> **Stage**: scope-definition | **Phase**: ideation (skipped - brownfield) | **Intent**: 261122-contractai-stabilize
> **Date**: 2026-11-23 | **Agent**: atlas (Tech Lead)

---

## Scope Statement
> Estabilizar o ContractAI para torná-lo operacional em produção através de governança AI-DLC, preservando código existente e adicionando: CI/CD, testes automatizados, observabilidade, ADRs, handoffs, stage gates e integração Agentic-Home.

---

## In Scope (Milestone 1 - Estabilização Mínima)

### Infraestrutura & CI/CD
- [ ] GitHub Actions pipeline completo (lint, typecheck, unit, integration, contract, security, e2e)
- [ ] Quality gates obrigatórios por stage (lint → unit → integration → contract → security → e2e)
- [ ] Deploy staging automatizado (main branch)
- [ ] Deploy production com aprovação manual (tag/release)
- [ ] Rollback testado e documentado (< 5 min)

### Testes & Qualidade
- [ ] Unit tests backend ≥ 80% cobertura
- [ ] Integration tests (PostgreSQL + pgvector) ≥ 70% cobertura
- [ ] Contract tests (Pact) consumer + provider
- [ ] E2E tests automatizados (Playwright) critical paths
- [ ] Security scans: SAST (Semgrep), SCA (Safety), Secrets (TruffleHog), Container (Trivy)
- [ ] Coverage reports (Codecov)

### Governança & Documentação
- [ ] 5 ADRs baseline (stack, multi-tenancy, auth, LLM, LGPD) - status: Implemented
- [ ] 2 ADRs propostas (CI/CD, Test Strategy) - status: Proposed
- [ ] ADR template AI-DLC (compliance + AI-DLC impact fields)
- [ ] Handoff template estendido (phase, stage, gate status)
- [ ] AI-DLC state tracking (aidlc-state.md)
- [ ] Project memory (project.md) + stage memories
- [ ] Stage gate approval-handoff com assinatura humana

### Integração Agentic-Home
- [ ] Skills carregáveis via `skill_view()`
- [ ] Templates handoff/adr estendidos (não duplicados)
- [ ] Catálogo sincronizado (ContractAI já registrado)
- [ ] Governança referenciada (`agentic-home/docs/governanca.md`)

### Integração & Deploy
- [ ] Deploy staging automatizado (main branch → staging)
- [ ] Deploy production com aprovação manual (tag + manual approval)
- [ ] Rollback testado (< 5 min)
- [ ] Environments: development → staging → production
- [ ] Environment variables por ambiente (vault/secrets)

---

## Out of Scope (Milestone 1)

### Observabilidade Completa
- ❌ Distributed tracing (Jaeger/Zipkin)
- ❌ Dashboards Grafana avançados
- ❌ Alerting (PagerDuty/Slack/email)
- ❌ Distributed tracing correlation IDs

### Deploy Avançado
- ❌ Blue-green production deploy
- ❌ Canary deployments
- ❌ Feature flags framework

### Qualidade Avançada
- ❌ Chaos engineering
- ❌ Performance baselines documentados
- ❌ Load testing automatizado
- ❌ Contract testing schema evolution

### Documentação Avançada
- ❌ Diagramas C4 completos
- ❌ Runbooks completos (incident response)
- ❌ Architecture Decision Records além dos 7 definidos
- ❌ API documentation completa (OpenAPI spec versionada)

### Funcionalidades de Produto
- ❌ Novas features de produto (apenas estabilização)
- ❌ Novos LLM providers
- ❌ Novos conectores
- ❌ Advanced analytics/ML features

---

## Boundary Conditions

### Technical Boundaries
- **Stack**: FastAPI + Next.js (não mudar)
- **Database**: PostgreSQL 15+ pgvector (prod), SQLite (dev)
- **Auth**: JWT HS256 + MFA (não mudar)
- **LLM Providers**: OpenAI, NVIDIA, Hermes (fallback disabled)
- **Multi-tenancy**: organization_id scoping (não mudar)

### Organizational Boundaries
- **Aprovação humana**: Rodrigo (deploy prod, dependências, ADRs)
- **Stage gates**: Obrigatórios entre fases AI-DLC
- **Code review**: Obrigatório para merge em main
- **Security reviews**: Obrigatórios para mudanças auth/LGPD

### Regulatory Boundaries
- **LGPD**: Export/Delete endpoints obrigatórios
- **Audit logging**: Todas operações sensíveis
- **Data retention**: 2555 dias (7 anos) configurável
- **Anonymization on delete**: Configurável

---

## Acceptance Criteria (Inception Complete)

| Critério | Evidência |
|----------|-----------|
| Baseline documentado | 5 memory.md files + project.md + aidlc-state.md |
| ADRs baseline registradas | 5 ADRs status "Implemented" em `docs/adr/` |
| ADRs propostas criadas | 2 ADRs status "Proposed" em `docs/adr/` |
| Delivery planning completo | Pipeline, environments, quality gates, runbooks |
| Stage gate pronto | `approval-handoff/memory.md` template pronto |
| AI-DLC state inicializado | `aidlc-state.md` = inception/reverse-engineering |
| Integração Home validada | Skills, templates, catálogo referenciados |

---

## Próximos Passos
1. **Approval-handoff**: Gate de aprovação humana para prosseguir à Construction
2. **Construction Phase**: Functional design → Code generation → Build & test → CI pipeline → Quality gates

---

*Scope definition documentado. Próximo: approval-handoff gate.*