# Diagnóstico e Proposta de Integração AI-DLC — ContractAI

> **Fase 1: Diagnóstico** | **Fase 2: Proposta de Integração**
> **Projeto-alvo**: ContractAI (`/opt/data/projects/contractai`)
> **Referência AI-DLC**: sistema-condominio-qr (`/opt/data/projects/sistema-condominio-qr/aidlc`)
> **Hub Governança**: agentic-home (`/opt/data/projects/agentic-home`)
> **Data**: 2026-11-22
> **Autor**: Atlas (Tech Lead)

---

# FASE 1 — DIAGNÓSTICO

## 1.1 Estrutura do Agentic-Home (Recursos Compartilhados)

| Componente | Localização | Finalidade | Status |
|------------|-------------|------------|--------|
| **Catálogo de Projetos** | `projects/catalogo.md` | Registro central de projetos | ✅ Ativo (3 projetos) |
| **Skills Compartilhadas** | `skills/{descoberta,arquitetura,desenvolvimento,qualidade}/SKILL.md` | Processos reutilizáveis | ✅ 4 skills ativas |
| **Templates** | `templates/{handoff.md,adr.md}` | Padronização de artefatos | ✅ Disponíveis |
| **Documentação** | `docs/{arquitetura,governanca,onboarding}.md` | Governança e onboarding | ✅ Completo |
| **Catálogo de Projetos** | `projects/catalogo.md` | 3 projetos registrados | ✅ ContractAI presente |

### Skills Disponíveis (carregáveis via `skill_view()`)
| Skill | Versão | Foco | Artefatos de Saída |
|-------|--------|------|-------------------|
| **descoberta** | 1.0.0 | Problem statement, requisitos, cenários, ACs | Problem Statement, Requirements Spec, Scenario Map, Ambiguity Log, Acceptance Criteria |
| **arquitetura** | 1.0.0 | Design técnico, trade-offs, ADRs, risk register | Diagramas C4, ADRs, Risk Register, NFR Matrix, Dependency Graph |
| **desenvolvimento** | 1.0.0 | Implementação, testes, git hygiene, scope control | Code Changes, Testes, Migration Scripts, CHANGELOG |
| **qualidade** | 1.0.0 | Validação ACs, testes, regressão, defect reports | Test Report, Defect Report, Quality Gate Report |

### Templates Disponíveis
| Template | Localização | Uso |
|----------|-------------|-----|
| `handoff.md` | `agentic-home/templates/handoff.md` | Transferência de contexto entre sessões/agentes |
| `adr.md` | `agentic-home/templates/adr.md` | Decisões arquiteturais com compliance/AI-DLC impact |

### Governança (agentic-home/docs/governanca.md)
- Matriz de permissões por operação (merge, deploy, secrets, etc.)
- Fluxos de aprovação com thresholds por papel (Tech Lead, Security, Compliance, Business Owner)
- Security boundaries, change management, incident response
- Classificação de dados (Público → Restrito → Regulado)

---

## 1.2 Implementação AI-DLC no sistema-condominio-qr (Referência)

### Estrutura de Diretórios
```
/opt/data/projects/sistema-condominio-qr/aidlc/
├── spaces/
│   └── default/
│       ├── intents/
│       │   ├── intents.json                          # Índice de intents
│       │   └── 261030-frontend-redesign/             # Intent ativo
│       │       ├── aidlc-state.md                    # Estado da execução (fase, stage, next action)
│       │       ├── project-description.json          # Descrição do projeto
│       │       ├── ideation/                         # Fase 0: Ideação
│       │       │   ├── intent-capture/
│       │       │   ├── scope-definition/
│       │       │   ├── approval-handoff/             # Gate de aprovação humana
│       │       │   └── ...
│       │       ├── inception/                        # Fase 1: Concepção
│       │       │   ├── reverse-engineering/
│       │       │   ├── requirements-analysis/
│       │       │   ├── domain-design/
│       │       │   ├── contract-design/
│       │       │   └── delivery-planning/
│       │       ├── construction/                     # Fase 2: Construção
│       │       │   ├── code-generation/
│       │       │   ├── build-and-test/
│       │       │   ├── ci-pipeline/
│       │       │   └── ...
│       │       └── audit/                            # Auditoria de execução
│       └── memory/
│           ├── project.md                            # Memória do projeto
│           └── phases/inception.md
```

### Componentes-Chave do AI-DLC (Reutilizáveis)
| Componente | Arquivo/Dir | Função |
|------------|-------------|--------|
| **aidlc-state.md** | `intent/aidlc-state.md` | Estado da execução: fase, stage, next action, pending artifacts |
| **project-description.json** | `intent/project-description.json` | Descrição canônica do projeto (single source of truth) |
| **memory.md** | Por stage (`ideation/.../memory.md`) | Observações, tradeoffs, devições, open questions por stage |
| **aidlc-state.md (project level)** | `spaces/default/memory/project.md` | Memória persistente do projeto |
| **Audit trail** | `intent/audit/` | Log de execução para auditoria |
| **intents.json** | `intents/intents.json` | Índice de todos os intents do workspace |
| **Phase/Stage gates** | `aidlc-state.md` + approval-handoff | Gates de aprovação humana entre fases |

### Mecanismos de Continuidade
| Mecanismo | Implementação |
|-----------|---------------|
| **Recuperação de contexto** | `aidlc-state.md` + `project-description.json` + `memory.md` do stage atual |
| **Gates de aprovação** | `approval-handoff/memory.md` + status `[?]` em `aidlc-state.md` |
| **Handoffs entre agentes** | `handoff.md` (template) + history append-only |
| **Stage resume** | `aidlc-state.md` mostra `Session Resume Point` com `Last Completed Stage` + `Next Action` |

---

## 1.3 Análise do ContractAI (Estado Atual)

### Arquitetura Atual
```
contractai/
├── backend/                          # FastAPI 0.109+ / Python 3.11+
│   ├── app/
│   │   ├── api/v1/                   # Endpoints: auth, contracts, analysis, reports, connectors, organizations, users, clauses
│   │   ├── models/                   # SQLAlchemy 2.0 async models
│   │   ├── schemas/                  # Pydantic request/response schemas
│   │   ├── services/                 # auth, llm_client, contract, analysis, etc.
│   │   ├── workers/                  # Celery tasks (async document processing)
│   │   ├── main.py                   # FastAPI app + lifespan + exception handlers
│   │   ├── config.py                 # Pydantic Settings (BaseSettings)
│   │   └── database.py               # SQLAlchemy async session management
│   ├── alembic/                      # Migrations (PostgreSQL/pgvector)
│   ├── tests/                        # pytest suite
│   └── pyproject.toml                # Dependencies (uv/pip)
├── frontend/                         # Next.js 14+ App Router
│   ├── app/                          # App Router pages
│   ├── components/                   # React components
│   ├── lib/                          # Axios client, utils
│   └── tests/                        # Vitest + React Testing Library + Playwright
├── docker-compose.yml                # PostgreSQL + Redis + API + Frontend
├── .env.example                      # Template env vars
└── README.md / AGENTS.md
```

### Funcionalidades Implementadas
| Área | Status | Detalhes |
|------|--------|----------|
| **Auth** | ✅ | JWT HS256 (30min/7d), JTI blacklist, MFA TOTP, bcrypt |
| **Multi-tenancy** | ✅ | Escopo por `organization_id`, roles: admin/manager/analyst/viewer |
| **Contract CRUD** | ✅ | Upload PDF/DOCX/TXT, list, detail |
| **Analysis** | ✅ | Async via Celery, LLM providers (OpenAI, NVIDIA, Hermes), vector search pgvector |
| **Document Processing** | ✅ | pdfplumber, pypdf, python-docx, Tesseract OCR fallback |
| **Vector Search** | ✅ | pgvector 1536-dim embeddings |
| **LGPD Compliance** | ✅ | Export/Delete endpoints, retention policies, audit logging |
| **Monitoring** | ✅ | Prometheus `/metrics`, structured JSON logging, health checks |
| **Frontend** | ✅ | Next.js 14 App Router, React Hook Form + Zod, Axios, Tailwind |
| **Testing** | ⚠️ | Backend: pytest (unit/integration); Frontend: Vitest + Playwright |

### Decisões Técnicas Registradas (em AGENTS.md/PROGRESSO.md equivalente)
| Decisão | Status | Localização |
|---------|--------|-------------|
| FastAPI + SQLAlchemy 2.0 async | ✅ Implementado | `backend/app/main.py`, `config.py` |
| PostgreSQL + pgvector (prod) / SQLite (dev) | ✅ Implementado | `config.py`, `database.py` |
| JWT HS256 + JTI blacklist + MFA TOTP | ✅ Implementado | `services/auth.py` |
| LLM Providers: OpenAI, NVIDIA, Hermes (fallback disabled by default) | ✅ Implementado | `services/llm_client.py` |
| Celery + Redis para processamento assíncrono | ✅ Implementado | `workers/`, `config.py` |
| Alembic migrations (PostgreSQL/pgvector only) | ✅ Implementado | `alembic/` |
| LGPD: export/delete endpoints, audit logging | ✅ Implementado | `main.py` (endpoints LGPD) |
| Multi-tenancy por `organization_id` | ✅ Implementado | Models, services, middleware |

### Pendências e Bloqueios Atuais
| Item | Status | Impacto |
|------|--------|---------|
| Testes unitários (backend) | ⚠️ Parcial | Cobertura não medida |
| Testes de integração (PostgreSQL/pgvector) | ⚠️ Não executados em CI | Risco de regressão |
| Testes E2E (frontend) | ✅ 33/33 passando (manual) | Não automatizado em CI |
| CI/CD Pipeline | ❌ Ausente | Deploy manual |
| Rate limiting configurado | ✅ Implementado | Por usuário/IP |
| Hermes API server integration | ⚠️ Opcional, não testado | `HERMES_BASE_URL` configurável |
| LLM Fallback | ⚠️ Desabilitado por padrão | `LLM_FALLBACK_ENABLED=false` |
| OAuth Connectors (Google/OneDrive) | ⚠️ Configurado, não testado | Credenciais em `.env.example` |

### Estado Git
- **Commits**: 4 (inicial + 3 docs)
- **Branch**: `main` (clean, up to date com origin)
- **Último commit**: `ac31c4e` — AGENTS.md consolidado

---

## 1.4 Componentes Reutilizáveis vs. Específicos

### Reutilizáveis (Agentic-Home → ContractAI)
| Componente | Origem | Aplicação no ContractAI |
|------------|--------|------------------------|
| **Skills** | `agentic-home/skills/` | Carregar via `skill_view()` nas tarefas |
| **Templates** | `agentic-home/templates/` | `handoff.md`, `adr.md` — usar direto |
| **Governança** | `agentic-home/docs/governanca.md` | Aplicar matriz de permissões |
| **Catálogo** | `agentic-home/projects/catalogo.md` | ContractAI já registrado |
| **Skills format** | `skills/*/SKILL.md` | Formato padronizado para skills do projeto |

### Específicos do ContractAI (Não reutilizáveis)
| Componente | Motivo |
|------------|--------|
| **AI-DLC workspace** (`aidlc/`) | Estado do projeto, intents, memory — único por projeto |
| **Project description** | Descrição única do ContractAI |
| **Intents** | Intenções específicas do projeto (ex: "implementar vector search", "LGPD compliance") |
| **Stage memory** | Observações, tradeoffs por stage — contexto do projeto |
| **Project memory** | Decisões, decisões técnicas, ADRs do ContractAI |

---

## 1.5 Conflitos Identificados

| # | Conflito | Severidade | Descrição | Mitigação |
|---|----------|------------|-----------|-----------|
| 1 | **AGENTS.md vs AI-DLC state** | Média | AGENTS.md diz "leia handoff.md", AI-DLC usa `aidlc-state.md` + `memory.md` | Unificar: handoff.md para tarefas operacionais; AI-DLC state para ciclo de vida do projeto |
| 2 | **Templates ADR** | Baixa | Agentic-home tem template simples; AI-DLC tem campos extras (compliance, AI-DLC impact) | Usar template AI-DLC (mais completo) como padrão |
| 3 | **Handoff format** | Média | Template Home é simples; AI-DLC usa formato mais rico (phase gates, artifacts) | Estender template Home ou usar formato AI-DLC |
| 4 | **Stage gates** | Alta | Agentic-Home não define gates; AI-DLC tem gates obrigatórios (approval-handoff) | Adotar gates AI-DLC como padrão de governança |
| 5 | **Skill loading** | Baixa | `skill_view()` carrega skills Home; projeto pode ter skills próprias | Definir namespace: `agentic-home:` vs `contractai:` |
| 5 | **Catálogo aponta para AGENTS.md** | Baixa | Catálogo diz `AGENTS.md` na raiz; ContractAI tem AGENTS.md | OK — já compatível |

---

# FASE 2 — PROPOSTA DE INTEGRAÇÃO

## 2.1 Estrutura de Diretórios AI-DLC para ContractAI

```
/opt/data/projects/contractai/
├── aidlc/                              # NOVO: Workspace AI-DLC
│   └── spaces/
│       └── default/
│           ├── intents/
│           │   ├── intents.json                    # Índice de intents
│           │   └── 261122-contractai-stabilize/    # Intent inicial: estabilizar/madurecer
│           │       ├── aidlc-state.md              # Estado execução (fase, stage, next action)
│           │       ├── project-description.json    # Descrição canônica do ContractAI
│           │       ├── ideation/                   # Fase 0: Ideação (opcional - brownfield)
│           │       │   ├── intent-capture/
│           │       │   ├── scope-definition/
│           │       │   └── approval-handoff/       # Gate: aprovação para prosseguir
│           │       ├── inception/                  # Fase 1: Concepção
│           │       │   ├── reverse-engineering/    # Análise código existente
│           │       │   ├── requirements-analysis/  # Requisitos do estado atual
│           │       │   ├── domain-design/          # Modelo domínio (multi-tenancy, LGPD, etc.)
│           │       │   ├── contract-design/        # Contratos API, schemas
│           │       │   └── delivery-planning/      # Plano de entrega (CI/CD, testes, deploy)
│           │       ├── construction/               # Fase 2: Construção (futuro)
│           │       │   ├── code-generation/
│           │       │   ├── build-and-test/
│           │       │   ├── ci-pipeline/
│           │       │   └── ...
│           │       └── audit/                      # Trilha de auditoria
│           └── memory/
│               ├── project.md                      # Memória do projeto (decisões, ADRs, contexto)
│               └── phases/                         # Memória por fase
├── docs/
│   └── adr/                                      # NOVO: ADRs do projeto (template AI-DLC)
│       ├── ADR-001-stack-tecnologica.md
│       ├── ADR-002-multi-tenancy.md
│       ├── ADR-003-auth-jwt.md
│       ├── ADR-004-llm-providers.md
│       └── ADR-005-lgpd-compliance.md
├── handoff.md                                    # Handoff ativo (template Home + AI-DLC)
├── AGENTS.md                                     # EXISTENTE — atualizar referências AI-DLC
└── AGENTS.md (existente) — manter
```

### Arquivos a Criar
| Arquivo | Origem | Ação |
|---------|--------|------|
| `aidlc/spaces/default/intents/261122-contractai-stabilize/aidlc-state.md` | Baseado em `sistema-condominio-qr` | Novo |
| `aidlc/spaces/default/intents/261122-contractai-stabilize/project-description.json` | Baseado em `sistema-condominio-qr` | Novo |
| `aidlc/spaces/default/intents/261122-contractai-stabilize/ideation/approval-handoff/memory.md` | Template AI-DLC | Novo |
| `aidlc/spaces/default/memory/project.md` | Baseado em `sistema-condominio-qr` | Novo |
| `docs/adr/ADR-001-stack-tecnologica.md` | Template `agentic-home/templates/adr.md` + campos AI-DLC | Novo |
| `docs/adr/ADR-002-multi-tenancy.md` | Template | Novo |
| `docs/adr/ADR-003-auth-jwt.md` | Template | Novo |
| `docs/adr/ADR-004-llm-providers.md` | Template | Novo |
| `docs/adr/ADR-005-lgpd-compliance.md` | Template | Novo |
| `handoff.md` (atualizar) | Template `agentic-home/templates/handoff.md` + campos AI-DLC | Atualizar |
| `AGENTS.md` (atualizar) | Existente | Atualizar referências AI-DLC |

---

## 2.2 Mecanismo de Recuperação de Contexto

### Artefatos de Entrada (Ordem de Leitura)
| Ordem | Artefato | Conteúdo-Chave |
|-------|----------|----------------|
| 1 | `aidlc/spaces/default/intents/261122-contractai-stabilize/project-description.json` | Descrição canônica do projeto (single source of truth) |
| 2 | `aidlc/spaces/default/intents/261122-contractai-stabilize/aidlc-state.md` | Fase atual, stage atual, next action, pending artifacts |
| 3 | `aidlc/spaces/default/memory/project.md` | Decisões históricas, ADRs, contexto técnico, bloqueios conhecidos |
| 3 | `aidlc/spaces/default/intents/261122-contractai-stabilize/<fase>/<stage>/memory.md` | Observações, tradeoffs, devições do stage atual |
| 4 | `handoff.md` | Tarefa ativa, owner, status, next action, artifacts |
| 4 | `docs/adr/ADR-*.md` | Decisões arquiteturais com rationale |
| 5 | `AGENTS.md` | Instruções operacionais, stack, comandos, skills |

### Fluxo de Inicialização de Sessão
```bash
# 1. Ler project-description.json (contexto do projeto)
cat aidlc/spaces/default/intents/261122-contractai-stabilize/project-description.json

# 2. Ler aidlc-state.md (estado atual)
cat aidlc/spaces/default/intents/261122-contractai-stabilize/aidlc-state.md

# 3. Ler project.md (memória do projeto)
cat aidlc/spaces/default/memory/project.md

# 4. Ler memory.md do stage atual (ex: inception/requirements-analysis/memory.md)
cat aidlc/spaces/default/intents/261122-contractai-stabilize/inception/requirements-analysis/memory.md

# 5. Verificar handoff ativo
cat handoff.md

# 5. Carregar skills necessárias
skill_view(name='descoberta')
skill_view(name='arquitetura')
# etc.
```

---

## 2.3 Registro de Decisões e Evidências

### ADRs (Architecture Decision Records)
| ADR | Título | Status | Template |
|-----|--------|--------|----------|
| ADR-001 | Stack Tecnológica (FastAPI, PostgreSQL, Next.js) | ✅ Aceito | Template AI-DLC |
| ADR-002 | Multi-tenancy por `organization_id` | ✅ Aceito | Template AI-DLC |
| ADR-003 | Auth JWT HS256 + JTI Blacklist + MFA | ✅ Aceito | Template AI-DLC |
| ADR-004 | LLM Providers (OpenAI, NVIDIA, Hermes) | ✅ Aceito | Template AI-DLC |
| ADR-005 | LGPD Compliance (Export/Delete, Audit Log) | ✅ Aceito | Template AI-DLC |
| ADR-006 | CI/CD Pipeline (GitHub Actions / Harness) | 🔄 Proposto | Template |
| ADR-007 | Test Strategy (Unit, Integration, Contract, E2E) | 🔄 Proposto | Template |

### Template ADR (AI-DLC Enhanced)
```markdown
# ADR-<numero>: <Titulo>

## Status
[Proposto | Aceito | Substituído | Depreciado]

## Contexto
Qual o problema? Quais as restrições? Quais forças em jogo?

## Decisão
O que foi decidido? Seja específico e acionável.

## Alternativas Consideradas
| Alternativa | Prós | Contras | Decisão |
|-------------|------|---------|---------|
| 1. | | | |
| 2. | | | |
| 3. | | | |

## Consequências
### Positivas
- 
### Negativas
- 
### Riscos
- 
### Mitigações
- 

## Impacto de Compliance
- [ ] Regulatório financeiro (CVM, Bacen, etc.)
- [ ] LGPD (Lei 13.709)
- [ ] SOX (Lei 11.941/2009)
- [ ] PCI-DSS
- [ ] ANBIMA
- [ ] CMN 4.658
- [ ] Outro: ___________

## Impacto AI-DLC
- **Eval gates afetados**: 
- **Pipeline changes**: 
- **Observabilidade needs**: 
- **Model routing changes**: 
- **Cost impact**: 

## Implementation Notes
- 

## References
- [Link to issue/PR]
- [Link to documentation]
- [Link to related ADR]

## History
| Date | Version | Author | Change |
|------|---------|--------|--------|
| YYYY-MM-DD | 1.0 | <author> | Initial proposal |

## Approval
| Role | Name | Date | Signature |
|------|------|------|-----------|
| Author | | | |
| Reviewer | | | |
| Approver | | | |
```

### Evidências por Decisão
| Tipo de Evidência | Localização | Formato |
|-------------------|-------------|---------|
| **Code** | `backend/app/...` | Link para arquivo/linha no GitHub |
| **Test Results** | `qa/evidence/<timestamp>/` | JSON/HTML (JUnit, coverage, etc.) |
| **Performance** | `qa/evidence/<timestamp>/perf.json` | JSON |
| **Security Scan** | `qa/evidence/<timestamp>/security.json` | JSON (SAST/SCA/Secrets) |
| **Audit Log** | `aidlc/spaces/default/intents/<intent>/audit/` | Markdown |
| **Human Approval** | `handoff.md` + `approval-handoff/memory.md` | Markdown com assinatura |

---

## 2.4 Stage Gates e Aprovações Humanas

### Fases AI-DLC e Gates Obrigatórios
| Fase | Stages | Gate de Saída | Aprovação Necessária |
|------|--------|---------------|---------------------|
| **0. Ideation** | intent-capture, scope-definition, approval-handoff | `approval-handoff/memory.md` assinado | **Humano (PM/PO)** — valida problema e escopo |
| **1. Inception** | reverse-engineering, requirements-analysis, domain-design, contract-design, delivery-planning | `delivery-planning/memory.md` + plano aprovado | **Humano (TL/PM)** — valida arquitetura e plano |
| **2. Construction** | functional-design, code-generation, build-and-test, ci-pipeline, etc. | `build-and-test/memory.md` + test results + quality gates | **Humano (TL/QA)** — valida qualidade antes de deploy |
| **3. Operation** | deployment-pipeline, environment-provisioning, observability-setup | `deployment-pipeline/memory.md` + runbook | **Humano (TL/SRE)** — autoriza deploy produção |

### Gate de Aprovação (Formato `approval-handoff/memory.md`)
```markdown
<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Approval Record
| Field | Value |
|-------|-------|
| **Stage** | <fase>/<stage> |
| **Date** | YYYY-MM-DD |
| **Approver** | <Nome/Rol> |
| **Decision** | [Approved | Rejected | Conditional] |
| **Conditions** | <Lista de condições se Conditional> |
| **Signature** | <Assinatura/Hash> |

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open Questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
```

---

## 2.5 Handoffs entre Agentes (PM, TCL, Dev, QA)

### Papéis e Responsabilidades no AI-DLC
| Agente | Fase Principal | Responsabilidades | Artefatos de Entrada | Artefatos de Saída |
|--------|----------------|-------------------|---------------------|-------------------|
| **PM (Polaris)** | Ideation, Inception | Problem statement, requirements, ACs, scope, prioritization | Project description, stakeholder input | Problem Statement, Requirements Spec, Scenario Map, ACs, Scope Doc |
| **TCL (Atlas)** | Inception, Construction | Architecture, ADRs, tech decisions, delivery planning | PM artifacts, requirements | ADRs, Architecture Diagrams, Delivery Plan, NFR Matrix |
| **Dev (Nexus)** | Construction | Implementation, tests, code quality | TCL artifacts (ADRs, specs) | Code changes, Unit/Integration tests, Migration scripts |
| **QA (Sentinel)** | Construction, Operation | Validation, test execution, regression, quality gates | Dev artifacts, requirements | Test Reports, Defect Reports, Quality Gate Reports |

### Formato de Handoff (Estendido AI-DLC)
```markdown
# Task: <identificador e descrição>

- **Project**: contractai
- **Owner**: <agente>
- **Phase**: <ideation|inception|construction|operation>
- **Stage**: <stage-name>
- **Status**: <pending|in-progress|blocked|done>
- **Approved**: <decisão, data, aprovador>
- **Waiting**: <pendência ou dependência>
- **Next action**: <próxima ação concreta e executável>

---

## Artifacts
- <caminho real do artefato 1>
- <caminho real do artefato 2>

---

## History
- **YYYY-MM-DD HH:MM** | <etapa> | <ação executada e resultado obtido>

---

## Validation
- **Checks executed**: <lista de verificações executadas>
- **Results**: <resultados de cada verificação>
- **Pending**: <itens pendentes de validação>

---

## Phase Gate Status
- **Gate**: <fase>/<stage> gate
- **Status**: [pending|approved|rejected|conditional]
- **Approver**: <nome>
- **Date**: YYYY-MM-DD
- **Conditions**: <condições se conditional>

---

## Notes
- <observações adicionais, bloqueios, decisões tomadas>
```

---

## 2.6 Integração com Agentic-Home (Padrões Compartilhados)

| Recurso Agentic-Home | Uso no ContractAI | Localização |
|---------------------|-------------------|-------------|
| **Skills** | `skill_view(name='descoberta')` etc. | Carregar no início da tarefa |
| **Template Handoff** | Base para `handoff.md` do projeto | `agentic-home/templates/handoff.md` |
| **Template ADR** | Base para `docs/adr/ADR-*.md` | `agentic-home/templates/adr.md` (estendido) |
| **Catálogo** | ContractAI registrado em `projects/catalogo.md` | `agentic-home/projects/catalogo.md` |
| **Governança** | Matriz de permissões, fluxos de aprovação | `agentic-home/docs/governanca.md` |
| **Onboarding** | Self-service para novos agentes | `agentic-home/docs/onboarding.md` |

### Evitar Duplicação
| Não Duplicar | Usar do Home |
|--------------|--------------|
| Definições de skills | Carregar via `skill_view()` |
| Template handoff básico | Estender, não copiar |
| Template ADR básico | Estender com campos AI-DLC |
| Governança global | Referenciar `agentic-home/docs/governanca.md` |
| Catálogo de projetos | Manter sincronizado via commit |

---

## 2.7 Estratégia de Rollback

| Cenário | Ação de Rollback | Artefatos Afetados |
|---------|------------------|-------------------|
| **AI-DLC quebrado** | Deletar `aidlc/` e restaurar `AGENTS.md` original | `aidlc/`, `AGENTS.md`, `handoff.md`, `docs/adr/` |
| **Stage gate rejeitado** | Reverter `aidlc-state.md` para stage anterior; limpar memory.md do stage rejeitado | `aidlc-state.md`, `<stage>/memory.md` |
| **ADR rejeitado** | Marcar ADR como "Depreciado"; criar novo ADR substituto | `docs/adr/ADR-XXX.md` (status: Depreciado) |
| **Handoff corrompido** | Restaurar `handoff.md` do último commit válido | `handoff.md` |
| **Memória corrompida** | Restaurar `project.md` e `phase/*.md` do último commit válido | `memory/project.md`, `memory/phases/*.md` |

### Procedimento de Rollback
```bash
# 1. Identificar último commit válido
git log --oneline -10

# 2. Restaurar arquivos específicos
git checkout <commit-hash> -- aidlc/ AGENTS.md handoff.md docs/adr/

# 3. Verificar integridade
cat aidlc/spaces/default/intents/261122-contractai-stabilize/aidlc-state.md
cat handoff.md

# 4. Commit do rollback
git commit -m "chore: rollback AI-DLC to <commit-hash> due to <reason>"
```

---

## 2.8 Plano de Validação (Teste de Continuidade)

### Critérios de Sucesso
| Critério | Como Validar |
|----------|--------------|
| **1. Contexto recuperável** | Nova sessão lê `project-description.json` + `aidlc-state.md` + `project.md` + `handoff.md` e identifica fase/stage/next action corretos |
| **2. Histórico preservado** | Git history intacto; `aidlc/` versionado; ADRs e handoffs append-only |
| **3. Decisões rastreáveis** | ADRs têm rationale, alternativas, approval; handoffs têm history append-only |
| **4. Stage gates funcionais** | `approval-handoff/memory.md` registra aprovação; `aidlc-state.md` mostra gate status |
| **4. Handoffs estruturados** | `handoff.md` tem owner, status, next action, artifacts, history, validation |
| **5. Integração Agentic-Home** | Skills carregam via `skill_view()`; templates referenciam Home; catálogo sincronizado |
| **6. Teste de nova sessão** | Sessão isolada recupera contexto apenas dos artefatos persistidos |

### Teste de Continuidade (Executar Após Implementação)
```bash
# 1. Simular nova sessão (novo terminal/shell)
# 2. Navegar ao projeto
cd /opt/data/projects/contractai

# 3. Executar sequência de recuperação
cat aidlc/spaces/default/intents/261122-contractai-stabilize/project-description.json
cat aidlc/spaces/default/intents/261122-contractai-stabilize/aidlc-state.md
cat aidlc/spaces/default/memory/project.md
cat handoff.md

# 4. Verificar se identifica corretamente:
# - Fase atual: inception
# - Stage atual: requirements-analysis (ou similar)
# - Next action: <conforme aidlc-state.md>
# - Bloqueios: <conforme aidlc-state.md / handoff.md>
# - Decisões pendentes: <conforme ADRs com status Proposto>

# 5. Verificar se aprovações pendentes ainda bloqueiam
# - Se gate status = [?] ou pending, próxima ação deve ser "obter aprovação"

# 6. Comparar com estado real do repositório
git status
git log --oneline -5
```

### Evidências de Validação
| Evidência | Localização | Formato |
|-----------|-------------|---------|
| **Continuidade testada** | `qa/evidence/continuity-test-<timestamp>.md` | Markdown |
| **Estado recuperado vs real** | `qa/evidence/state-comparison-<timestamp>.json` | JSON |
| **Gaps identificados** | `qa/evidence/gaps-<timestamp>.md` | Markdown |

---

# RESUMO — ARQUIVOS A CRIAR/MODIFICAR

## Novos Arquivos (16)
| # | Arquivo | Tipo |
|---|---------|------|
| 1 | `aidlc/spaces/default/intents/261122-contractai-stabilize/aidlc-state.md` | Novo |
| 2 | `aidlc/spaces/default/intents/261122-contractai-stabilize/project-description.json` | Novo |
| 3 | `aidlc/spaces/default/intents/261122-contractai-stabilize/ideation/intent-capture/memory.md` | Novo |
| 4 | `aidlc/spaces/default/intents/261122-contractai-stabilize/ideation/scope-definition/memory.md` | Novo |
| 5 | `aidlc/spaces/default/intents/261122-contractai-stabilize/ideation/approval-handoff/memory.md` | Novo |
| 6 | `aidlc/spaces/default/intents/261122-contractai-stabilize/inception/reverse-engineering/memory.md` | Novo |
| 7 | `aidlc/spaces/default/intents/261122-contractai-stabilize/inception/requirements-analysis/memory.md` | Novo |
| 8 | `aidlc/spaces/default/intents/261122-contractai-stabilize/inception/domain-design/memory.md` | Novo |
| 9 | `aidlc/spaces/default/intents/261122-contractai-stabilize/inception/contract-design/memory.md` | Novo |
| 10 | `aidlc/spaces/default/intents/261122-contractai-stabilize/inception/delivery-planning/memory.md` | Novo |
| 11 | `aidlc/spaces/default/memory/project.md` | Novo |
| 12 | `aidlc/spaces/default/intents/intents.json` | Novo |
| 13 | `docs/adr/ADR-001-stack-tecnologica.md` | Novo |
| 14 | `docs/adr/ADR-002-multi-tenancy.md` | Novo |
| 15 | `docs/adr/ADR-003-auth-jwt.md` | Novo |
| 16 | `docs/adr/ADR-004-llm-providers.md` | Novo |
| 17 | `docs/adr/ADR-005-lgpd-compliance.md` | Novo |

## Arquivos a Modificar (4)
| # | Arquivo | Alteração |
|---|---------|-----------|
| 1 | `AGENTS.md` | Adicionar seção AI-DLC, referenciar `aidlc/`, skills, templates |
| 2 | `handoff.md` | Estender com campos AI-DLC (phase, stage, gate status) |
| 18 | `aidlc/spaces/default/intents/intents.json` | Adicionar intent `261122-contractai-stabilize` |
| 19 | `aidlc/spaces/default/intents/261122-contractai-stabilize/audit/` | Criar diretório (vazio) |

---

# RISCOS IDENTIFICADOS

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Conflito AGENTS.md vs AI-DLC state | Média | Médio | Unificar referências; handoff.md para tarefas, AI-DLC state para ciclo de vida |
| Stage gates não respeitados | Baixa | Alto | Gates obrigatórios no `aidlc-state.md`; validação no handoff |
| Perda de contexto entre sessões | Baixa | Alto | Teste de continuidade obrigatório pós-implementação |
| Duplicação de templates | Baixa | Baixo | Estender templates Home, não copiar |
| ADRs sem aprovação | Média | Médio | Gates de aprovação obrigatórios no handoff |
| Perda de histórico Git | Baixa | Crítico | `aidlc/` versionado; rollback documentado |

---

# PRÓXIMOS PASSOS

1. **Aprovação humana** desta proposta (você)
2. **Fase 3** — Preservação do histórico (baseline Git, registrar estado atual)
3. **Fase 4** — Implementação (criar estrutura, arquivos, integrar)
4. **Fase 5** — Validação (teste de continuidade, evidências)

---

**Aguardando sua aprovação explícita para prosseguir à Fase 3.**