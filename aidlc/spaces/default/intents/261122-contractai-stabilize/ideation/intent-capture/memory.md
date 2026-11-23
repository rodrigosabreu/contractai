# Intent Capture — Memory

> **Stage**: intent-capture | **Phase**: ideation (skipped - brownfield) | **Intent**: 261122-contractai-stabilize
> **Date**: 2026-11-23 | **Agent**: atlas (Tech Lead)

---

## Intent Statement
> Estabilizar e madurar o ContractAI através de governança AI-DLC, preservando desenvolvimento existente (FastAPI + Next.js, multi-tenancy, JWT+MFA, LLM providers, LGPD) e adicionando: CI/CD pipeline, testes automatizados, observabilidade, stage gates, ADRs, handoffs estruturados e integração com Agentic-Home.

---

## Stakeholders

| Stakeholder | Papel | Interesse |
|-------------|-------|-----------|
| **Rodrigo Abreu** | Product Owner / Tech Lead | Entrega estável, governança, rastreabilidade |
| **Atlas (TCL)** | Tech Lead / Arquiteto | Arquitetura, ADRs, quality gates, CI/CD |
| **Polaris (PM)** | Product Manager | Priorização, requisitos, aceitação |
| **Nexus (Dev)** | Desenvolvedor | Implementação, testes, code quality |
| **Sentinel (QA)** | Quality Assurance | Validação, regressão, quality gates |

---

## Problema Real
> O ContractAI é uma POC funcional mas **não operacional para produção**: falta CI/CD, testes automatizados em CI, observabilidade completa, stage gates de qualidade, rastreabilidade de decisões (ADRs) e continuidade entre sessões de agentes. O desenvolvimento atual depende de conhecimento tribal e validação manual.

---

## Hipóteses de Valor
| Hipótese | Métrica de Sucesso |
|----------|-------------------|
| AI-DLC reduz tempo de onboarding de novos agentes | Onboarding < 30 min (vs horas atuais) |
| Stage gates reduzem bugs em produção | 0 bugs críticos em produção por release |
| CI/CD automatizado acelera delivery | Deploy staging < 15 min, production < 30 min |
| ADRs + handoffs eliminam conhecimento tribal | 100% decisões rastreáveis |
| Testes automatizados previnem regressão | 0 regressões em funcionalidades cobertas |

---

## Escopo (In/Out)

### In Scope (Milestone 1 - Estabilização Mínima)
- ✅ CI/CD Pipeline (GitHub Actions) com quality gates
- ✅ Testes unitários ≥ 80% (backend) + integração PG/pgvector
- ✅ Testes E2E automatizados (Playwright) em CI
- ✅ Security scans (SAST/SCA/Secrets/Container) em CI
- ✅ Deploy staging automatizado + rollback testado
- ✅ ADRs para 5 decisões existentes + 2 propostas
- ✅ Handoffs estruturados + AI-DLC state tracking
- ✅ Integração Agentic-Home (skills, templates, catálogo)

### Out of Scope (Milestone 1)
- ❌ Observabilidade completa (traces, dashboards avançados)
- ❌ Alerting (PagerDuty/Slack)
- ❌ Chaos engineering
- ❌ Blue-green production deploy (apenas staging)
- ❌ Chaos engineering / performance baselines
- ❌ Documentação arquitetura completa (C4 diagrams)

### Future Scope (Milestone 2+)
- Observabilidade completa + Alerting
- Blue-green production deploy
- Performance baselines + Chaos engineering
- Documentação completa (C4, runbooks)
- Chaos engineering

---

## Riscos Identificados

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| CI/CD flaky tests | Média | Alto | Quarentena flaky tests, retry logic |
| pgvector version mismatch | Baixa | Alto | Pin versions, testcontainers fixed version |
| Secrets em CI logs | Baixa | Crítico | Masked secrets, vault integration |
| Rate limit em CI | Alta | Médio | Disable rate limit em `APP_ENV=test` |
| LLM provider down em CI | Média | Baixo | Mock LLM em testes unitários |
| Flaky E2E tests | Alta | Médio | Retry 2x, screenshots on failure |
| Database migration conflict | Baixa | Alto | Review obrigatório, backup antes |
| Dependência não aprovada | Média | Bloqueador | Rodrigo aprovar antes de `dotnet add package` |

---

## Critérios de Sucesso (Inception Complete)
- [ ] Baseline documentado (reverse-engineering, requirements, domain-design, contract-design, delivery-planning)
- [ ] ADRs para 5 decisões existentes registradas (sem aprovação retroativa)
- [ ] 2 ADRs propostas (CI/CD, Test Strategy) para aprovação
- [ ] Delivery planning com CI/CD pipeline, environments, quality gates definido
- [ ] Stage gate approval-handoff pronto para aprovação humana
- [ ] AI-DLC state inicializado (aidlc-state.md = inception/reverse-engineering)

---

*Intent capture documentado. Próximo: scope-definition.*