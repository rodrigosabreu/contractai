# ContractAI — AGENTS.md

> **Objetivo**: Ponto de entrada para agentes trabalharem neste projeto. Contém instruções operacionais, stack real (backend + frontend), comandos e integração com o Agentic Home.

---

## 🎯 Objetivo do Produto

Prova de conceito para apoiar a análise de contratos com inteligência artificial. A aplicação permite cadastrar uma organização, enviar um documento (PDF/DOCX/TXT) e solicitar uma análise estruturada de cláusulas e riscos.

> **Aviso**: Projeto experimental, sem aprovação para produção ou uso com dados reais. As análises podem conter omissões ou erros e não substituem revisão jurídica. Use apenas documentos e dados fictícios.

---

## 🛠️ Stack Real

### Backend (`backend/`)
| Camada | Tecnologia |
|--------|------------|
| **Framework** | FastAPI 0.109+ |
| **Linguagem** | Python 3.11+ |
| **Database** | PostgreSQL 15+ com pgvector (produção) / SQLite + aiosqlite (desenvolvimento local) |
| **ORM** | SQLAlchemy 2.0 (async) |
| **Migrations** | Alembic |
| **Task Queue** | Celery + Redis |
| **Auth** | JWT (HS256) com token revocation (JTI blacklist), MFA (TOTP) |
| **LLM Providers** | OpenAI (GPT-4), NVIDIA (Nemotron) — fallback configurável |
| **Document Processing** | pdfplumber, pypdf, python-docx, Tesseract OCR |
| **Vector Search** | pgvector (1536-dim embeddings) |
| **Monitoring** | Prometheus metrics (`/metrics`), structured JSON logging, health checks |

### Frontend (`frontend/`)
| Camada | Tecnologia |
|--------|------------|
| **Framework** | Next.js 14+ (App Router) |
| **Linguagem** | TypeScript |
| **Styling** | Tailwind CSS |
| **State/Forms** | React Hook Form + Zod |
| **HTTP Client** | Axios |
| **Testing** | Vitest + React Testing Library, Playwright (E2E) |
| **Type Checking** | `npm run type-check` |

---

## 📁 Estrutura dos Componentes

```
contractai/
├── backend/                          # API FastAPI
│   ├── app/
│   │   ├── api/v1/                   # Endpoints REST
│   │   │   ├── auth.py               # Autenticação (register, login, refresh, logout, MFA)
│   │   │   ├── contracts.py          # CRUD contratos + upload
│   │   │   ├── analysis.py           # Análise de contratos
│   │   │   ├── reports.py            # Relatórios organizacionais
│   │   │   ├── connectors.py         # Conectores de armazenamento (Google Drive, OneDrive)
│   │   │   ├── organizations.py      # Gestão de organizações
│   │   │   ├── users.py              # Gestão de usuários
│   │   │   ├── clauses.py            # Busca/gerenciamento de cláusulas
│   │   │   └── router.py             # Agregação de rotas
│   │   ├── models/                   # SQLAlchemy models
│   │   ├── schemas/                  # Pydantic schemas (request/response)
│   │   ├── services/                 # Business logic
│   │   │   ├── auth.py               # JWT, tokens, revocation
│   │   │   ├── llm_client.py         # Abstração de provedores LLM
│   │   │   └── ...                   # Outros serviços
│   │   ├── workers/                  # Celery tasks (processamento assíncrono)
│   │   ├── main.py                   # FastAPI app entry point
│   │   ├── config.py                 # Configuração (Pydantic Settings)
│   │   └── database.py               # DB session management
│   ├── alembic/                      # Database migrations (PostgreSQL/pgvector)
│   ├── tests/                        # Test suite (pytest)
│   ├── pyproject.toml                # Dependencies + project config
│   ├── Dockerfile
│   ├── alembic.ini
│   └── README.md                     # Documentação detalhada do backend
│
├── frontend/                         # Next.js App
│   ├── app/                          # App Router pages
│   ├── components/                   # React components
│   ├── lib/                          # Utilities, API client (Axios)
│   ├── styles/                       # Global styles
│   ├── tests/                        # Vitest + React Testing Library
│   ├── public/                       # Static assets
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── Dockerfile
│   └── .env.local.example
│
├── docker-compose.yml                # PostgreSQL + Redis + API + Frontend
├── .env.example                      # Template de variáveis de ambiente
├── .gitignore
├── arquitetura-poc.png               # Diagrama de arquitetura
├── arquitetura-poc.html              # Versão HTML do diagrama
└── README.md                         # Este arquivo (visão geral)
```

---

## 🚀 Comandos de Execução e Testes

### Backend (Docker Compose — recomendado)
```bash
cd /opt/data/projects/contractai
docker compose -f docker-compose.yml up -d
docker compose exec api alembic upgrade head
# API em http://localhost:8000
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

### Backend (Desenvolvimento Local — SQLite)
```bash
cd /opt/data/projects/contractai/backend
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'

export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export DATABASE_URL='sqlite+aiosqlite:///./contractai_local.db'
export REDIS_URL='redis://localhost:6379/0'
export CELERY_BROKER_URL="$REDIS_URL" CELERY_RESULT_BACKEND="$REDIS_URL"
export APP_ENV=development DEBUG=false

uvicorn app.main:app --host 127.0.0.1 --port 8000
```

> **Nota**: SQLite local não substitui PostgreSQL/pgvector para testes de integração, vector search, Redis/Celery jobs, ou integrações LLM/OAuth. Migrações Alembic são específicas para PostgreSQL/pgvector — não executar `alembic upgrade head` no SQLite.

### Frontend
```bash
cd /opt/data/projects/contractai/frontend
npm ci
npm run dev
# Frontend em http://localhost:3000 (proxy para API em 8000)
```

### Testes
```bash
# Backend
cd /opt/data/projects/contractai/backend
pytest tests/ -v
pytest tests/ --cov=app --cov-report=html

# Frontend
cd /opt/data/projects/contractai/frontend
npm test
npm run type-check
```

### Variáveis de Ambiente Obrigatórias
Copie `.env.example` para `.env` e configure:
- `DATABASE_URL` — PostgreSQL async URL (ex: `postgresql+asyncpg://user:pass@db:5432/contractai`)
- `REDIS_URL` — Redis URL (ex: `redis://redis:6379/0`)
- `SECRET_KEY` — String aleatória forte (32+ chars) para JWT
- `OPENAI_API_KEY` ou `NVIDIA_API_KEY` — Pelo menos um provedor LLM
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` — Google Drive integration (opcional)
- `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET` — OneDrive integration (opcional)

---

## 🔒 Regras de Isolamento Multi-Tenant e Segurança

### Multi-Tenancy (Implementado no Backend)
- **Todos os recursos** são escopados por `organization_id`
- Usuários só acessam recursos dentro de sua organização
- Superusers (`admin` global) acessam todas as organizações

### Papéis de Usuário (Backend)
| Papel | Permissões |
|-------|------------|
| `admin` | Gestão completa da organização |
| `manager` | Gerencia usuários, contratos, análises |
| `analyst` | Cria análises, visualiza todos dados da org |
| `viewer` | Acesso somente leitura |

### Autenticação e Autorização
- **JWT tokens** (HS256): access token 30 min, refresh token 7 dias
- **Revogação de tokens** via JTI blacklist (logout, rotação de refresh, mudança de senha)
- **Refresh tokens** armazenados em HttpOnly cookies
- **MFA (TOTP)** com backup codes
- **Password hashing**: bcrypt
- **CORS** configurado por ambiente
- **SQL injection protection** via SQLAlchemy ORM
- **Input validation** via Pydantic

### LGPD Compliance (Backend)
- Políticas de retenção de dados (configuráveis)
- Endpoint de exportação de dados (`/api/v1/auth/data/export`)
- Endpoint de exclusão de dados (`/api/v1/auth/data/delete`)
- Anonimização na exclusão (configurável)
- Audit logging para operações sensíveis
- Data Processing Agreement (DPA) ready

### Integração LLM (Backend)
- **Provedores**: OpenAI (GPT-4), NVIDIA (Nemotron) — seleção via `provider` parameter
- **Fallback** configurável via `LLM_FALLBACK_ENABLED` (default: `false`)
- **Hermes API server (opcional)**: `HERMES_BASE_URL`, `HERMES_API_KEY`, `HERMES_MODEL` — selecionar com `provider="hermes"`
- **Não há garantia** de segurança, isolamento, privacidade ou conformidade regulatória para conteúdo enviado a LLMs externos

### Processamento de Documentos
- **PDF**: pdfplumber/pypdf + OCR fallback (Tesseract)
- **DOCX**: python-docx
- **TXT**: Plain text
- Processamento assíncrono via Celery workers (timeout padrão 8 min)

---

## 🔗 Integração com Agentic Home (Skills Compartilhadas)

Este projeto pode usar as skills compartilhadas do `agentic-home`:

```bash
# No Hermes Agent, carregue skills conforme necessário:
skill_view(name='descoberta')    # Exploração de problemas & requisitos
skill_view(name='arquitetura')   # Design técnico, trade-offs, ADRs
skill_view(name='desenvolvimento') # Padrões de implementação, testes, CI/CD
skill_view(name='qualidade')     # Validação, testes, revisão de código, observabilidade
```

**Templates disponíveis no Home:**
- `agentic-home/templates/handoff.md` — Template de handoff de tarefa (append-only)
- `agentic-home/templates/adr.md` — Template de ADR (decisões arquiteturais)

**Como usar:**
1. Clone o `agentic-home` e leia seu `AGENTS.md`
2. Navegue pelo catálogo: `cat projects/catalogo.md`
3. Carregue skills relevantes antes de iniciar trabalho
4. Crie `handoff.md` na raiz deste projeto para cada tarefa (seguindo template da Home)
5. Atualize o handoff conforme progride (append-only)

---

## 📋 Orientação para Handoffs por Tarefa

Para cada tarefa neste projeto:

1. **Crie/atualize** `handoff.md` na raiz do projeto (`/opt/data/projects/contractai/handoff.md`) usando o template: `agentic-home/templates/handoff.md`
2. **Preencha** os campos obrigatórios:
   - Identificador e descrição da tarefa
   - Projeto, Owner, Status
   - Aprovado (decisão, data, aprovador)
   - Aguardando (dependências/bloqueadores)
   - Próxima ação (explícita e executável)
   - Artefatos (caminhos reais)
   - Histórico (append-only)
   - Validação (checks executados, resultados, pendentes)
3. **Não sobrescreva** histórico anterior — apenas apende
4. **Referencie** artefatos reais (caminhos absolutos ou relativos ao repo)
5. **Não marque como aprovado** sem evidência (link para PR, testes, registro de aprovação)

---

## 📚 Documentação Relacionada

| Documento | Localização |
|-----------|-------------|
| README completo (raiz) | `README.md` |
| Backend detalhado | `backend/README.md` |
| Catálogo do Agentic Home | `agentic-home/projects/catalogo.md` |
| Skills compartilhadas | `agentic-home/skills/` |
| Template de handoff | `agentic-home/templates/handoff.md` |
| Template de ADR | `agentic-home/templates/adr.md` |

---

*Este AGENTS.md é a fonte de verdade para agentes operando neste projeto. Atualize quando houver mudanças na stack, comandos, estrutura ou regras.*