# Contract Design — Memory

> **Stage**: contract-design | **Phase**: inception | **Intent**: 261122-contractai-stabilize
> **Date**: 2026-11-23 | **Agent**: atlas (Tech Lead)
> **Baseline**: Commit ac31c4e

---

## Objetivo
Definir contratos de API (OpenAPI), schemas de validação, versionamento, convenções de erro e padrões de comunicação entre frontend/backend.

---

## API Contract (OpenAPI 3.1)

### Versionamento
| Estratégia | Detalhes |
|------------|----------|
| **URL Versioning** | `/api/v1/` prefix obrigatório |
| **Deprecation** | Header `Deprecation: true` + `Sunset` date |
| **Breaking Changes** | Nova versão `/api/v2/` |
| **Additive Changes** | Mesma versão (campos opcionais, novos endpoints) |

### Convenções de Nomenclatura
| Elemento | Convenção | Exemplo |
|----------|-----------|---------|
| **Paths** | kebab-case, plural | `/api/v1/contracts`, `/api/v1/analysis-results` |
| **Query Params** | snake_case | `page_size`, `created_after` |
| **Request Body** | camelCase (JSON) | `contractTitle`, `pageSize` |
| **Response Body** | camelCase (JSON) | `contractId`, `createdAt` |
| **Enums** | PascalCase (string) | `"TipoServico": "Limpeza"` |
| **IDs** | UUID string | `"contractId": "550e8400-e29b-41d4-a716-446655440000"` |
| **Timestamps** | ISO 8601 UTC | `"createdAt": "2026-11-23T00:00:00Z"` |

### Envelope de Resposta Padronizado

#### Sucesso (2xx)
```json
{
  "data": { ... },           // Objeto ou array
  "meta": {                  // Opcional: paginação, metadata
    "page": 1,
    "pageSize": 20,
    "total": 150
  }
}
```

#### Erro (4xx/5xx) — Envelope Legado (RNF03)
```json
{
  "erro": "validation_error",           // Código de erro
  "mensagem": "Descrição amigável",     // Mensagem legível (pt-BR)
  "detalhes": [                         // Opcional: detalhes por campo
    {
      "codigo": "VALIDATION_ERROR",
      "campo": "email",
      "mensagem": "E-mail inválido"
    }
  ],
  "requestId": "req_abc123"             // Header X-Request-ID
}
```

#### Códigos de Erro Padronizados
| Código | HTTP Status | Uso |
|--------|-------------|-----|
| `validation_error` | 400 | Dados de entrada inválidos |
| `not_found` | 404 | Recurso não encontrado |
| `unauthorized` | 401 | Token inválido/ausente |
| `forbidden` | 403 | Sem permissão (escopo) |
| `conflict` | 409 | Conflito (ex: email duplicado) |
| `rate_limited` | 429 | Rate limit excedido |
| `internal_error` | 500 | Erro interno |
| `database_error` | 500 | Erro de banco |
| `llm_error` | 502 | Erro provedor LLM |

---

## Endpoints Contratados (v1)

### Autenticação (`/api/v1/auth`)

| Método | Path | Descrição | Auth | Request | Response |
|--------|------|-----------|------|---------|----------|
| POST | `/register` | Registrar org + admin | Público | `RegisterRequest` | `AuthResponse` |
| POST | `/login` | Login | Público | `LoginRequest` | `LoginResponse` |
| POST | `/refresh` | Refresh token | Refresh token | - | `LoginResponse` |
| POST | `/logout` | Logout (revoga tokens) | Access token | - | `204` |
| POST | `/mfa/enable` | Ativar MFA | Access token | `MfaEnableRequest` | `MfaEnableResponse` |
| POST | `/mfa/verify` | Verificar MFA | Access token | `MfaVerifyRequest` | `MfaVerifyResponse` |
| POST | `/data/export` | Exportar dados (LGPD) | Access token | - | `DataExportResponse` |
| POST | `/data/delete` | Solicitar exclusão (LGPD) | Access token | - | `DataDeleteResponse` |

### Contratos (`/api/v1/contracts`)

| Método | Path | Descrição | Auth | Request | Response |
|--------|------|-----------|------|---------|----------|
| GET | `/` | Listar contratos | Access token | Query: `page`, `pageSize`, `status` | `PaginatedResponse<ContractDto>` |
| POST | `/` | Criar contrato | Access token | `CreateContractRequest` (multipart) | `ContractDto` (201) |
| GET | `/{id}` | Obter contrato | Access token | - | `ContractDto` |
| DELETE | `/{id}` | Soft delete | Access token | - | `204` |
| POST | `/{id}/analyze` | Solicitar análise | Access token | `AnalyzeRequest` | `AnalysisDto` (202) |

### Análises (`/api/v1/analysis`)

| Método | Path | Descrição | Auth | Request | Response |
|--------|------|-----------|------|---------|----------|
| POST | `/` | Criar análise | Access token | `CreateAnalysisRequest` | `AnalysisDto` (201) |
| GET | `/` | Listar análises | Access token | Query: `page`, `pageSize`, `status` | `PaginatedResponse<AnalysisDto>` |
| GET | `/{id}` | Obter análise | Access token | - | `AnalysisDto` |
| GET | `/{id}/result` | Obter resultado | Access token | - | `AnalysisResultDto` |

### Cláusulas (`/api/v1/clauses`)

| Método | Path | Descrição | Auth | Request | Response |
|--------|------|-----------|------|---------|----------|
| GET | `/` | Buscar/listar cláusulas | Access token | Query: `page`, `pageSize`, `type`, `riskLevel` | `PaginatedResponse<ClauseDto>` |
| POST | `/search` | Busca semântica | Access token | `SemanticSearchRequest` | `SemanticSearchResponse` |

### Relatórios (`/api/v1/reports`)

| Método | Path | Descrição | Auth | Request | Response |
|--------|------|-----------|------|---------|----------|
| GET | `/organization/summary` | Resumo organizacional | Access token | - | `OrganizationSummaryDto` |

### Conectores (`/api/v1/connectors`)

| Método | Path | Descrição | Auth | Request | Response |
|--------|------|-----------|------|---------|----------|
| GET | `/` | Listar conectores | Access token | - | `ConnectorDto[]` |
| POST | `/` | Adicionar conector | Access token | `CreateConnectorRequest` | `ConnectorDto` (201) |

### Organizações (`/api/v1/organizations`)

| Método | Path | Descrição | Auth | Request | Response |
|--------|------|-----------|------|---------|----------|
| GET | `/` | Listar organizações | Access token | - | `OrganizationDto[]` |
| POST | `/` | Criar organização | Access token (Super Admin) | `CreateOrganizationRequest` | `OrganizationDto` (201) |
| PUT | `/{id}` | Atualizar organização | Access token | `UpdateOrganizationRequest` | `OrganizationDto` |

### Usuários (`/api/v1/users`)

| Método | Path | Descrição | Auth | Request | Response |
|--------|------|-----------|------|---------|----------|
| GET | `/` | Listar usuários | Access token | Query: `page`, `pageSize` | `PaginatedResponse<UserDto>` |
| POST | `/` | Criar usuário | Access token (Admin) | `CreateUserRequest` | `UserDto` (201) |
| PUT | `/{id}` | Atualizar usuário | Access token | `UpdateUserRequest` | `UserDto` |

---

## Schemas de Request/Response (Principais)

### Auth
```typescript
// Requests
interface RegisterRequest {
  organizationName: string;
  cnpj?: string;
  adminName: string;
  adminEmail: string;
  adminPassword: string;  // min 8 chars
}

interface LoginRequest {
  email: string;      // lowercase, trimmed
  password: string;   // sem trim - preserva espaços
}

interface LoginResponse {
  token: string;           // JWT access token
  expiresAt: string;       // ISO 8601
  refreshToken: string;    // HttpOnly cookie (não no body)
  user: UserSessionDto;
}

// Responses
interface UserSessionDto {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'manager' | 'analyst' | 'viewer';
  organizationId: string | null;  // null para Super Admin
}

interface DataExportResponse {
  message: string;
  exportedAt: string;  // ISO 8601
  data: {
    user: UserDto;
    contracts: ContractDto[];
    analyses: AnalysisDto[];
    clauses: ClauseDto[];
    auditLogs: AuditLogDto[];
    connectors: ConnectorDto[];
  };
}
```

### Contratos
```typescript
interface ContractDto {
  id: string;
  title: string;
  source: 'upload' | 'google_drive' | 'onedrive';
  filePath: string;
  pageCount: number;
  language: string;
  status: 'uploaded' | 'processing' | 'analyzed' | 'error';
  ownerId: string;
  organizationId: string;
  createdAt: string;
  updatedAt: string;
}

interface CreateContractRequest {
  title: string;
  file: File;  // multipart/form-data
}

interface CreateAnalysisRequest {
  contractId: string;
  type: 'full' | 'clauses_only' | 'risk_only' | 'summary';
  provider?: 'openai' | 'nvidia' | 'hermes';
}

interface AnalysisDto {
  id: string;
  contractId: string;
  type: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  llmProvider: string;
  llmModel: string;
  result?: AnalysisResultDto;
  errorMessage?: string;
  createdAt: string;
  completedAt?: string;
}
```

### Cláusulas e Busca
```typescript
interface ClauseDto {
  id: string;
  analysisId: string;
  type: string;
  content: string;
  riskScore: number;      // 0-1
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  entities: EntityDto[];
  createdAt: string;
}

interface SemanticSearchRequest {
  query: string;
  organizationId?: string;  // inferido do token se não informado
  filters?: {
    type?: string;
    riskLevel?: string;
    riskScoreMin?: number;
    riskScoreMax?: number;
  };
  limit?: number;  // default 20, max 100
}

interface SemanticSearchResponse {
  results: ClauseSearchResultDto[];
  total: number;
}

interface ClauseSearchResultDto {
  clause: ClauseDto;
  score: number;  // similarity score
}
```

### Paginação (Padrão)
```typescript
interface PaginatedResponse<T> {
  data: T[];
  meta: {
    page: number;        // 1-indexed
    pageSize: number;    // 1-100, default 20
    total: number;
    totalPages: number;
  };
}
```

---

## Versionamento de Schemas

| Schema | Versão Atual | Estratégia de Evolução |
|--------|--------------|------------------------|
| `ContractDto` | v1 | Aditivo apenas (campos opcionais) |
| `AnalysisDto` | v1 | Aditivo; breaking → v2 |
| `AnalysisResultDto` | v1 | Aditivo; estrutura interna pode mudar |
| `ClauseDto` | v1 | Aditivo |
| `UserDto` | v1 | Aditivo |
| `ErrorResponse` | v1 | Estável (RNF03) |

---

## Validação de Contrato (Consumer-Driven Contracts)

### Pact (Consumer: Frontend, Provider: Backend)
| Consumer | Provider | Contratos Cobertos |
|----------|----------|-------------------|
| Frontend (Next.js) | Backend (FastAPI) | Todos endpoints v1 |

### Execução
```bash
# Consumer tests (Frontend)
cd frontend && npm run test:contract

# Provider verification (Backend)
cd backend && pact-verifier --pact-url=./pacts --provider-base-url=http://localhost:8000
```

---

## Convenções de Erro (Frontend Consumption)

### Frontend (`frontend/src/api/cliente.ts`)
```typescript
// Extrai mensagem: corpo.mensagem → corpo.erro → fallback
const erro = await resposta.json();
const mensagem = erro.mensagem ?? erro.erro ?? 'Erro desconhecido';
throw new ErroApi(resposta.status, mensagem);
```

### Compatibilidade
- **RNF03**: Envelope `{ erro, mensagem }` mantido
- **Frontend não consome** `detalhes[]` nem `errors[]`
- **Logging**: Backend loga todos erros internamente (auditoria)

---

## Versionamento de API

| Versão | Status | Sunset Date | Migração |
|--------|--------|-------------|----------|
| v1 | Atual | TBD | - |
| v0 (legacy) | Deprecated | 2026-12-31 | Migrado para v1 |

---

## Documentação OpenAPI

### Geração Automática
```bash
# Backend
cd backend && python -m scripts.generate_openapi > openapi.json

# Frontend consumption
cd frontend && npx openapi-typescript openapi.json -o lib/api-types.ts
```

### Anotações FastAPI (Exemplo)
```python
@router.post(
    "/contracts",
    response_model=ContractDto,
    status_code=201,
    summary="Criar contrato",
    responses={
        400: {"model": ErrorResponse, "description": "Dados inválidos"},
        401: {"model": ErrorResponse, "description": "Não autenticado"},
        403: {"model": ErrorResponse, "description": "Sem permissão"},
        413: {"model": ErrorResponse, "description": "Arquivo muito grande"},
    }
)
async def create_contract(...):
    ...
```

---

## Gaps de Contrato (Para Construction)

| Gap | Descrição | Prioridade |
|-----|-----------|------------|
| OpenAPI spec não versionada | Gerar `openapi.json` versionado em CI | Alta |
| Pact tests não em CI | Adicionar consumer/provider verification | Alta |
| Schemas não versionados | Adicionar versionamento semântico | Média |
| Deprecation headers | Implementar `Deprecation` + `Sunset` headers | Baixa |
| Contract testing (frontend) | Validar schemas em build | Média |
| Breaking change detection | Tool para detectar breaking changes | Baixa |

---

## Próximos Passos (AI-DLC)

1. **Delivery-planning**: CI/CD pipeline, environments, deploy strategy, quality gates
2. **Approval-handoff**: Gate para prosseguir à Construction

---

*Contract design formalizado. Baseline para Delivery Planning.*