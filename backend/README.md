# ContractAI Backend

> **Experimental POC:** This document contains proposed and partially implemented features. Do not assume that security, tenant isolation, OAuth connectors, semantic search, Docker deployment, or production readiness has been validated. Use fictional documents only and verify each procedure before use.

Backend API for ContractAI - Intelligent Contract Analysis Platform.

## Tech Stack

- **Framework**: FastAPI 0.109+
- **Database**: PostgreSQL 15+ with pgvector extension
- **ORM**: SQLAlchemy 2.0 (async)
- **Migrations**: Alembic
- **Task Queue**: Celery + Redis
- **Auth**: JWT (HS256) with token revocation
- **LLM Providers**: OpenAI (GPT-4), NVIDIA (Nemotron)
- **Document Processing**: pdfplumber, pypdf, python-docx, Tesseract OCR
- **Vector Search**: pgvector (1536-dim embeddings)

## Quick Start

### Prerequisites

- Docker & Docker Compose
- PostgreSQL 15+ with pgvector
- Redis 7+
- Python 3.11+ (for local development)

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your settings
```

Required variables:
- `DATABASE_URL` - PostgreSQL async URL (e.g., `postgresql+asyncpg://user:pass@db:5432/contractai`)
- `REDIS_URL` - Redis URL (e.g., `redis://redis:6379/0`)
- `SECRET_KEY` - Strong random string (32+ chars) for JWT signing
- `OPENAI_API_KEY` or `NVIDIA_API_KEY` - At least one LLM provider
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` - For Google Drive integration
- `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET` - For OneDrive integration

### Development with Docker Compose

```bash
# Start all services
docker compose -f docker-compose.yml up -d

# Run migrations
docker compose exec api alembic upgrade head

# View logs
docker compose logs -f api
```

### Local Development (SQLite)

Use Python 3.11 or 3.12. From `backend/`:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'

# Local-only settings; export a fresh secret without printing it.
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export DATABASE_URL='sqlite+aiosqlite:///./contractai_local.db'
export REDIS_URL='redis://localhost:6379/0'
export CELERY_BROKER_URL="$REDIS_URL" CELERY_RESULT_BACKEND="$REDIS_URL"
export APP_ENV=development DEBUG=false
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Environment variables override values from `.env`; do not commit credentials.
A stable secret is required to keep tokens valid across restarts. Generate and
store one securely for continued development; do not use the example for production.
Startup creates **missing** SQLite tables from the current models; it does not
alter existing tables. Use a new filename for a clean local database. Before
changing an existing database or schema, make a verified backup. SQLite local
mode is not a substitute for PostgreSQL/pgvector integration tests, vector search,
Redis/Celery jobs, or external LLM/OAuth integrations. Redis URL settings alone
do not start Redis.

**Migrations:** `alembic/versions/001_initial.py` is PostgreSQL/pgvector-specific,
not a SQLite migration. Do not run `alembic upgrade head` or `alembic stamp`
on the SQLite development database. `create_all` is not a schema migration;
it will not repair or upgrade an older SQLite schema. For PostgreSQL, back up
the target and review its current schema and revision before applying migrations;
never stamp an existing database without independently verifying schema parity.

Run the isolated local database tests with `python -m pytest tests/ -q`.
These tests create temporary databases and do not need Redis. Existing tests in
`app/tests/` can also be run explicitly; some may require additional setup.


## API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

### Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/auth/register` | Register organization + admin user |
| `POST /api/v1/auth/login` | User login (returns JWT tokens) |
| `POST /api/v1/auth/refresh` | Refresh access token |
| `POST /api/v1/auth/logout` | Logout (revokes tokens) |
| `POST /api/v1/auth/mfa/enable` | Enable MFA (TOTP) |
| `GET /api/v1/contracts` | List contracts |
| `POST /api/v1/contracts/upload` | Upload contract (PDF/DOCX/TXT) |
| `GET /api/v1/contracts/{id}` | Get contract details |
| `POST /api/v1/analysis` | Create contract analysis |
| `GET /api/v1/analysis/{id}` | Get analysis results |
| `GET /api/v1/reports/organization/summary` | Organization summary report |
| `GET /api/v1/clauses` | Search/filter clauses |
| `POST /api/v1/clauses/search` | Semantic clause search |
| `GET /api/v1/connectors` | List storage connectors |
| `POST /api/v1/connectors` | Add storage connector |
| `GET /api/v1/organizations/me` | Current organization details |

## Multi-tenancy

All resources are scoped by `organization_id`. Users can only access resources within their organization. Superusers can access all organizations.

### User Roles

- `admin` - Full organization management
- `manager` - Manage users, contracts, analyses
- `analyst` - Create analyses, view all org data
- `viewer` - Read-only access

## LLM Providers

Supports multiple LLM providers with configurable fallback:

```python
from app.services.llm_client import get_llm_client

client = get_llm_client()
response = await client.complete(
    messages=[{"role": "user", "content": "Analyze this contract..."}],
    provider="nvidia",  # or "openai"
    temperature=0.1,
    max_tokens=2000,
)
```

**Fallback behavior**: Controlled by `LLM_FALLBACK_ENABLED` env var (default: `false`). When enabled, automatically tries other providers on failure.

### Hermes API server (optional)

Set `HERMES_BASE_URL` to the trusted API server's base URL including `/v1`,
`HERMES_API_KEY` to its bearer token, and optionally `HERMES_MODEL` (default
`hermes-agent`). Select it explicitly with `provider="hermes"` or set
`DEFAULT_LLM_PROVIDER=hermes`. No Hermes configuration is modified or service
started by this application. The API server is an agent runtime, not the
subscription proxy: its profile, tools, memory, persistence and upstream model
determine what happens to contract data. Use an isolated, appropriately
restricted profile and an authorized endpoint; protect transport with TLS where
needed. Enabling fallback may send contract text to other configured providers.
JSON response-format enforcement depends on the server and underlying model;
invalid JSON fails analysis. Embeddings are not implemented for this adapter;
select an existing embedding provider explicitly. Cost is unknown and represented
as zero for compatibility, with `metadata.cost_available=false` (not free).
`analysis.execution_evidence` is the API's verified field for execution provenance;
`result.llm_execution` alone must not be trusted, especially for historical results.
New results store an HMAC bound to the analysis ID using `SECRET_KEY`; the API
verifies it and omits the signature from serialized results. Changing that key
invalidates prior evidence, which then becomes unknown. Historical analyses are
not modified and have no evidence unless independently verifiable. The adapter
identifies which ContractAI adapter succeeded, including after fallback; it is not
Hermes' upstream provider. Direct OpenAI responses from its official endpoint can
supply their reported model. Hermes Chat Completions' `model` can be an alias and
cannot prove its upstream model or internal fallback, so those fields stay null.
For Hermes, the requested alias is separate from its unknown effective model.
When creating an analysis, the requested provider and model default to the
corresponding ContractAI settings if omitted; they are not execution evidence.
See the Hermes API server documentation:
https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server

## Document Processing

Supports:
- **PDF**: Text extraction via pdfplumber/pypdf, OCR fallback (Tesseract)
- **DOCX**: Text extraction via python-docx
- **TXT**: Plain text

Files are processed asynchronously via Celery workers with configurable timeouts (default 8 minutes).

## Vector Search

Uses pgvector for semantic search:
- 1536-dim embeddings (OpenAI text-embedding-3-small / NVIDIA embedding-v1)
- Clause-level semantic search
- Risk-based filtering

## Security

- JWT tokens (HS256) with short expiry (30 min access, 7 days refresh)
- Token revocation via JTI blacklist (logout, refresh rotation, password change)
- Refresh tokens stored in HttpOnly cookies
- MFA (TOTP) with backup codes
- Password hashing: bcrypt
- CORS configured per environment
- SQL injection protection via SQLAlchemy ORM
- Input validation via Pydantic

## LGPD Compliance

- Data retention policies (configurable)
- Data export endpoint (`/api/v1/auth/data/export`)
- Data deletion endpoint (`/api/v1/auth/data/delete`)
- Anonymization on delete (configurable)
- Audit logging for all sensitive operations
- Data Processing Agreement (DPA) ready

## Monitoring

- Prometheus metrics at `/metrics`
- Structured JSON logging
- Health checks: `/health` (liveness), `/health/ready` (readiness)
- Audit logging for all sensitive operations

## Testing

```bash
# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html
```

## Deployment

### Production Checklist

- [ ] Set `APP_ENV=production`
- [ ] Set `DEBUG=false`
- [ ] Generate strong `SECRET_KEY` (32+ chars)
- [ ] Configure production `DATABASE_URL` and `REDIS_URL`
- [ ] Set `LLM_FALLBACK_ENABLED=false`
- [ ] Configure TLS/SSL (reverse proxy)
- [ ] Set up backup/restore for PostgreSQL
- [ ] Configure log aggregation
- [ ] Set up alerting on health checks
- [ ] Run security scan on Docker image

### Docker Production

```bash
docker build -t contractai-api .
docker run -d \
  --name contractai-api \
  -p 8000:8000 \
  --env-file .env.production \
  contractai-api
```

## Project Structure

```
backend/
├── app/
│   ├── api/v1/           # API endpoints
│   │   ├── auth.py       # Authentication
│   │   ├── contracts.py  # Contract CRUD
│   │   ├── analysis.py   # Analysis management
│   │   ├── reports.py    # Reporting
│   │   ├── connectors.py # Storage connectors
│   │   ├── organizations.py # Org management
│   │   ├── users.py      # User management
│   │   ├── clauses.py    # Clause search/management
│   │   └── router.py     # Router aggregation
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   │   ├── auth.py       # JWT, tokens, revocation
│   │   ├── llm_client.py # LLM provider abstraction
│   │   └── ...           # Other services
│   ├── workers/          # Celery tasks
│   ├── main.py           # FastAPI app
│   ├── config.py         # Configuration
│   └── database.py       # DB session management
├── alembic/              # Database migrations
├── tests/                # Test suite
├── pyproject.toml        # Dependencies
├── Dockerfile
├── alembic.ini
└── README.md
```

## License

Proprietary - ContractAI Team