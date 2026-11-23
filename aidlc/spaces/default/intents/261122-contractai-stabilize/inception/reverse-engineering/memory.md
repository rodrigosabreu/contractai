# Reverse Engineering — Memory

> **Stage**: reverse-engineering | **Phase**: inception | **Intent**: 261122-contractai-stabilize
> **Date**: 2026-11-23 | **Agent**: atlas (Tech Lead)
> **Baseline Commit**: ac31c4e

---

## Objetivo
Documentar a arquitetura atual, decisões técnicas, código existente e estado do projeto como baseline para o AI-DLC. Não reinventar — apenas registrar o que existe.

---

## Arquitetura Geral (Reverse-Engineered)

### Visão de Alto Nível
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│    Backend       │────▶│   Database      │
│   (Next.js 14)  │     │   (FastAPI)      │     │  (PostgreSQL    │
│   Port 3000     │     │   Port 8000      │     │   + pgvector)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                              │
                              ▼
                        ┌──────────────────┐
                        │   Message Queue  │
                        │    (Redis +      │
                        │    Celery)       │
                        └──────────────────┘
                              │
                              ▼
                        ┌──────────────────┐
                        │   LLM Providers  │
                        │  (OpenAI/NVIDIA/ │
                        │   Hermes)        │
                        └──────────────────┘
```

### Componentes Principais

#### Backend (`/backend`)
| Componente | Localização | Responsabilidade |
|------------|-------------|------------------|
| **API Layer** | `app/api/v1/` | Endpoints REST organizados por domínio |
| **Models** | `app/models/` | SQLAlchemy 2.0 async models |
| **Schemas** | `app/schemas/` | Pydantic request/response validation |
| **Services** | `app/services/` | Business logic, orchestration |
| **Workers** | `app/workers/` | Celery tasks (async processing) |
| **Auth** | `app/services/auth.py` | JWT, MFA, token management |
| **LLM Client** | `app/services/llm_client.py` | Multi-provider abstraction |
| **Config** | `app/config.py` | Pydantic Settings (env-driven) |
| **Database** | `app/database.py` | SQLAlchemy async engine/session |

#### Frontend (`/frontend`)
| Componente | Localização | Responsabilidade |
|------------|-------------|------------------|
| **Pages** | `app/` | Next.js 14 App Router pages |
| **Components** | `components/` | Reusable React components |
| **API Client** | `lib/api.ts` | Axios instance + interceptors |
| **Auth** | `lib/auth.ts` | Token management, session |
| **Types** | `lib/types.ts` | TypeScript interfaces |

---

## Decisões Técnicas (Reverse-Engineered)

### Backend
| Área | Decisão | Evidência |
|------|---------|-----------|
| **Framework** | FastAPI 0.109+ | `pyproject.toml`, `main.py` |
| **Async** | Full async (SQLAlchemy 2.0 async, asyncpg) | `database.py`, `models/` |
| **ORM** | SQLAlchemy 2.0 (async) | `models/`, `database.py` |
| **Migrations** | Alembic (PostgreSQL/pgvector only) | `alembic/`, `config.py` |
| **Auth** | JWT HS256 + JTI blacklist + MFA TOTP | `services/auth.py`, `config.py` |
| **Task Queue** | Celery + Redis | `workers/`, `config.py` |
| **LLM Abstraction** | Strategy pattern (OpenAI/NVIDIA/Hermes) | `services/llm_client.py` |
| **Document Processing** | pdfplumber, pypdf, python-docx, Tesseract | `workers/`, `schemas/` |
| **Vector Search** | pgvector (1536-dim) | `models/`, `alembic/` |
| **Monitoring** | Prometheus (`/metrics`), JSON logging, health checks | `main.py`, `config.py` |
| **LGPD** | Export/Delete endpoints, audit logging | `main.py` (LGPD endpoints) |

### Frontend
| Área | Decisão | Evidência |
|------|---------|-----------|
| **Framework** | Next.js 14 (App Router) | `package.json`, `app/` |
| **Language** | TypeScript (strict) | `tsconfig.json` |
| **Styling** | Tailwind CSS | `tailwind.config.js`, `postcss.config.js` |
| **Forms** | React Hook Form + Zod | `components/`, `schemas/` |
| **HTTP Client** | Axios + interceptors | `lib/api.ts` |
| **Auth** | localStorage + token refresh | `lib/auth.ts`, `lib/api.ts` |
| **Testing** | Vitest + React Testing Library + Playwright | `tests/`, `package.json` |

### Infrastructure
| Componente | Decisão | Evidência |
|------------|---------|-----------|
| **Containerization** | Docker Compose (PostgreSQL, Redis, API, Frontend) | `docker-compose.yml` |
| **Database Prod** | PostgreSQL 15+ + pgvector | `docker-compose.yml`, `config.py` |
| **Database Dev** | SQLite + aiosqlite | `config.py` (dev overrides) |
| **Cache/Queue** | Redis 7+ | `docker-compose.yml`, `config.py` |
| **Migrations** | Alembic (PostgreSQL only) | `alembic/`, `alembic.ini` |
| **Env Management** | `.env` + `.env.example` + Pydantic Settings | `config.py`, `.env.example` |

---

## Código Existente — Pontos-Chave

### Backend Entry Point (`backend/app/main.py`)
- **Lifespan**: Inicializa LLM client, DB, fecha conexões no shutdown
- **Exception Handlers**: SQLAlchemyError→500, ValueError→400, Generic→500
- **LGPD Endpoints**: `/api/v1/auth/data/export`, `/api/v1/auth/data/delete`
- **Health Checks**: `/health` (liveness), `/health/ready` (readiness + deps)
- **Metrics**: Prometheus `/metrics` (condicional)
- **CORS**: Configurável via `CORS_ORIGINS`

### Configuração (`backend/app/config.py`)
- **Pydantic Settings** com validação rigorosa
- **SECRET_KEY**: Obrigatório, min 32 chars
- **DEBUG**: False por padrão, warning em produção
- **LLM_FALLBACK_ENABLED**: False por padrão (segurança)
- **LGPD**: Retention days, anonymize on delete, audit log retention
- **CORS**: Parsing de string para lista

### Autenticação (`backend/app/services/auth.py`)
- **JWT**: HS256, access 30min, refresh 7d
- **JTI Blacklist**: Revogação em logout/rotação/senha
- **MFA**: TOTP + backup codes
- **Password**: bcrypt
- **Refresh Tokens**: HttpOnly cookies
- **Escopo**: `organization_id` no token

### LLM Client (`backend/app/services/llm_client.py`)
- **Strategy Pattern**: OpenAI, NVIDIA, Hermes providers
- **Fallback**: Desabilitado por padrão (`LLM_FALLBACK_ENABLED=false`)
- **Hermes**: Configurável via `HERMES_BASE_URL`, `HERMES_API_KEY`, `HERMES_MODEL`

### Frontend Auth (`frontend/lib/auth.ts` + `frontend/lib/api.ts`)
- **Storage**: localStorage (token + expiry + user)
- **Auto-refresh**: Interceptor 401 → refresh → retry
- **Expiry Check**: Validação client-side de expiração
- **Session**: `{ token, expiraEm, usuario }`

---

## Dados e Seed

### Seed de Desenvolvimento (`backend/app/DadosDesenvolvimento.cs` equivalente em Python)
- **2 Organizações**: `admin.geral@sistema.com` (Super Admin), `sindico@flores.com.br` (Admin Flores), etc.
- **4 Usuários**: Super Admin, Admin Flores, Funcionário Flores, Admin Aurora
- **Senha Padrão**: `Dev@12345`
- **Locais**: 5 locais com QR Codes ativos
- **Serviços**: Histórico variado

---

## Testes Existentes

### Backend (`backend/tests/`)
- **Framework**: pytest
- **Cobertura**: Parcial (não medida)
- **Tipos**: Unit + Integration (parcial)
- **Execução**: `pytest tests/ -v`, `pytest tests/ --cov=app --cov-report=html`

### Frontend (`frontend/tests/`)
- **Unit/Component**: Vitest + React Testing Library
- **E2E**: Playwright (33/33 passando — manual)
- **Type Checking**: `npm run type-check`
- **Execução**: `npm test`, `npm run type-check`

---

## Gaps Identificados (Baseline)

| Gap | Severidade | Localização |
|-----|------------|-------------|
| **Sem CI/CD** | Crítica | Ausente |
| **Testes integração PG/pgvector** | Alta | Não em CI |
| **Testes E2E automatizados** | Média | Apenas manual (33/33) |
| **Cobertura de código** | Média | Não medida |
| **CI/CD Pipeline** | Crítica | Ausente |
| **Testes unitários completos** | Média | Parcial |
| **Hermes integration** | Baixa | Não testado |
| **OAuth Connectors** | Média | Configurado, não testado |

---

## Observações para AI-DLC

### Pontos de Atenção
1. **Multi-tenancy**: Implementado via `organization_id` + JWT claims — validar em todos os endpoints
2. **LGPD**: Endpoints implementados mas não testados em cenários reais
3. **LLM Fallback**: Desabilitado por padrão — decisão de segurança consciente
4. **Hermes Integration**: Código existe mas não validado
5. **Rate Limiting**: Implementado por usuário/IP — validar em carga
6. **Migrations**: Alembic apenas para PostgreSQL — SQLite dev usa `create_all`

### Decisões Não Documentadas (Agora Registradas)
- Uso de `organization_id` redundante em `QrCode` para validação sem join
- `PapelUsuario` como enum (não tabela) para simplificar
- Senha sem trim (preserva espaços intencionais)
- CNPJ normalização: extrai dígitos, valida 14 dígitos
- Email normalização: lowercase + trim
- Rate limit por usuário autenticado (fallback IP para anônimos)

---

## Próximos Passos (AI-DLC)

1. **Requirements-analysis**: Levantar requisitos atuais + gaps
2. **Domain-design**: Modelar domínio formalmente
3. **Contract-design**: Definir contratos API, schemas, validações
3. **Delivery-planning**: CI/CD, testes, deploy, quality gates
4. **Approval-handoff**: Gate para Construction

---

*Reverse-engineering concluído. Baseline documentado sem atribuição de aprovação retroativa.*