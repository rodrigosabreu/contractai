# ContractAI — Project Memory

> **Projeto**: ContractAI — Intelligent Contract Analysis Platform
> **Intent**: 261122-contractai-stabilize
> **Baseline**: Commit ac31c4e (2026-11-22)
> **AI-DLC Inicializado**: 2026-11-23

---

## Contexto do Projeto

### Descrição
ContractAI é uma Prova de Conceito (POC) para apoiar a análise de contratos com inteligência artificial. Permite cadastrar organizações, enviar documentos (PDF/DOCX/TXT) e solicitar análises estruturadas de cláusulas e riscos.

> **Aviso**: Projeto experimental, sem aprovação para produção ou uso com dados reais. As análises podem conter omissões ou erros e não substituem revisão jurídica.

### Objetivo do AI-DLC
Estabilizar e madurar o projeto ContractAI através de governança estruturada (AI-DLC), preservando o desenvolvimento existente e adicionando:
- Rastreabilidade de decisões (ADRs)
- Memória persistente entre sessões
- Stage gates com aprovação humana
- Handoffs estruturados entre agentes
- Integração com Agentic-Home (skills, templates, governança)

---

## Decisões Técnicas Registradas (Baseline — Sem Aprovação Retroativa)

> **Nota**: As decisões abaixo foram tomadas durante o desenvolvimento anterior ao AI-DLC. São registradas como *baseline histórico* (status: **Implemented**), **sem atribuição de aprovação retroativa**. Novas decisões a partir daqui seguirão o processo AI-DLC com gates de aprovação.

| ADR | Título | Status | Descrição Resumida |
|-----|--------|--------|-------------------|
| ADR-001 | Stack Tecnológica | Implemented | FastAPI 0.109+ / Python 3.11+ / PostgreSQL 15+ pgvector (prod) / SQLite (dev) / Next.js 14+ / TypeScript / Tailwind |
| ADR-002 | Multi-tenancy por `organization_id` | Implemented | Isolamento de dados por organização; roles: admin/manager/analyst/viewer; superusers acessam todas |
| ADR-003 | Auth JWT HS256 + JTI Blacklist + MFA TOTP | Implemented | Access token 30min, refresh 7d, JTI blacklist, MFA TOTP com backup codes, bcrypt |
| ADR-004 | LLM Providers | Implemented | OpenAI (GPT-4), NVIDIA (Nemotron), Hermes API (fallback desabilitado por padrão) |
| ADR-005 | LGPD Compliance | Implemented | Export/Delete endpoints, audit logging, retention policies, DPA ready |
| ADR-006 | CI/CD Pipeline | **Proposed** | Definir estratégia (GitHub Actions / Harness), quality gates, deploy |
| ADR-007 | Test Strategy | **Proposed** | Unit, Integration, Contract, E2E; coverage targets; baseline capture |

---

## Decisões Técnicas (Detalhamento do Baseline)

### ADR-001: Stack Tecnológica
- **Backend**: FastAPI 0.109+, Python 3.11+, SQLAlchemy 2.0 async, Alembic, Celery + Redis
- **Database**: PostgreSQL 15+ com pgvector (produção), SQLite + aiosqlite (desenvolvimento)
- **Frontend**: Next.js 14+ (App Router), TypeScript, Tailwind CSS, React Hook Form + Zod, Axios
- **LLM Providers**: OpenAI (GPT-4), NVIDIA (Nemotron), Hermes API (opcional)
- **Document Processing**: pdfplumber, pypdf, python-docx, Tesseract OCR
- **Vector Search**: pgvector (1536-dim embeddings)
- **Monitoring**: Prometheus metrics, structured JSON logging, health checks

### ADR-002: Multi-tenancy
- **Modelo**: Escopo por `organization_id` em todos os recursos
- **Roles**: admin (gestão total org), manager (users, contracts, analyses), analyst (create analyses, view all), viewer (read-only)
- **Superusers**: Acesso a todas as organizações
- **Isolamento**: Enforced em models, services, middleware

### ADR-003: Autenticação e Autorização
- **JWT**: HS256, access token 30min, refresh token 7 dias
- **Revocation**: JTI blacklist (logout, rotação refresh, mudança senha)
- **Refresh tokens**: HttpOnly cookies
- **MFA**: TOTP com backup codes
- **Password hashing**: bcrypt
- **CORS**: Configurado por ambiente

### ADR-004: LLM Providers
- **Providers**: OpenAI (GPT-4), NVIDIA (Nemotron), Hermes API (opcional)
- **Fallback**: Desabilitado por padrão (`LLM_FALLBACK_ENABLED=false`)
- **Hermes**: `HERMES_BASE_URL`, `HERMES_API_KEY`, `HERMES_MODEL` configuráveis
- **Aviso**: Sem garantia de segurança/isolamento/privacidade para LLMs externos

### ADR-005: LGPD Compliance
- **Data Retention**: Configurável (padrão 2555 dias = 7 anos)
- **Export Endpoint**: `/api/v1/auth/data/export` (LGPD Art. 18)
- **Delete Endpoint**: `/api/v1/auth/data/delete` (LGPD Art. 18)
- **Anonymization**: Configurável na exclusão
- **Audit Logging**: Todas operações sensíveis
- **DPA**: Ready

---

## Pendências e Bloqueios (Baseline)

| Item | Status | Impacto | Ação Necessária |
|------|--------|---------|-----------------|
| Testes unitários (backend) | Parcial | Médio | Medir cobertura, completar gaps |
| Testes integração (PostgreSQL/pgvector) | Não em CI | Alto | Configurar CI com PostgreSQL/pgvector |
| Testes E2E (frontend) | 33/33 manual | Médio | Automatizar em CI (Playwright) |
| CI/CD Pipeline | Ausente | Crítico | Implementar (GitHub Actions / Harness) |
| Rate limiting | Implementado | Baixo | Validar em carga |
| Hermes API server | Opcional, não testado | Baixo | Testar integração |
| LLM Fallback | Desabilitado | Baixo | Avaliar necessidade |
| OAuth Connectors (Google/OneDrive) | Configurado, não testado | Médio | Testar com credenciais reais |

---

## Conflitos Identificados (AI-DLC vs Existente)

| # | Conflito | Mitigação Planejada |
|---|----------|---------------------|
| 1 | AGENTS.md vs AI-DLC state | Unificar: handoff.md para tarefas operacionais; AI-DLC state para ciclo de vida do projeto |
| 2 | Templates ADR/handoff | Estender templates Home com campos AI-DLC (compliance, AI-DLC impact) |
| 3 | Stage gates | Adotar gates AI-DLC como padrão; gates obrigatórios entre fases |
| 4 | Skill loading | Namespace `agentic-home:` vs `contractai:`; carregar via `skill_view()` |
| 5 | Templates ADR | Usar template AI-DLC (mais completo: compliance + AI-DLC impact) |

---

## Riscos Residuais (Baseline)

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Quebra de contrato (envelope 400) | Média | Alto | Manter envelope legado; testar exhaustivamente |
| Precedência alterada (400 vs 403/404) | Alta | Alto | Invocação explícita no service; testar TC-AUTH-09/10/11 |
| Normalização perdida | Média | Médio | Normalização ANTES do validator; testar TC-NORM |
| Rate limit impede regressão | Alta | Alto | Desabilitar/eleva limite em ambiente QA |
| Dependência não aprovada | Média | Bloqueador | Rodrigo aprovar antes de `dotnet add package` |

---

## Métricas de Baseline (Commit ac31c4e)

| Métrica | Valor |
|---------|-------|
| **Commits** | 4 (main) |
| **Branch** | main (up to date com origin) |
| **Último commit** | ac31c4e — AGENTS.md consolidado |
| **Git status** | Clean (2 untracked: diagnósticos) |
| **Backend tests** | pytest (parcial) |
| **Frontend tests** | Vitest + Playwright (33/33 manual) |
| **Build backend** | `pip install -e '.[dev]'` + uvicorn |
| **Build frontend** | `npm ci` + `npm run dev` |
| **Docker Compose** | PostgreSQL + Redis + API + Frontend |

---

## Próximas Ações (AI-DLC)

1. **Reverse-engineering stage**: Documentar arquitetura atual, decisões, codebase
2. **Requirements-analysis**: Levantar requisitos do estado atual + gaps
3. **Domain-design**: Modelar domínio (multi-tenancy, LGPD, auth, LLM)
4. **Contract-design**: Definir contratos API, schemas, validações
5. **Delivery-planning**: Planejar CI/CD, testes, deploy, quality gates
6. **Approval-handoff**: Gate de aprovação humana para prosseguir à Construction

---

*Última atualização: 2026-11-23T00:00:00Z — Baseline registrado*