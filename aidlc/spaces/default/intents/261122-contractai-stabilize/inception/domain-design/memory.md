# Domain Design — Memory

> **Stage**: domain-design | **Phase**: inception | **Intent**: 261122-contractai-stabilize
> **Date**: 2026-11-23 | **Agent**: atlas (Tech Lead)
> **Baseline**: Commit ac31c4e

---

## Objetivo
Formalizar o modelo de domínio do ContractAI baseado no código existente (reverse-engineering) e requisitos levantados. Definir entidades, value objects, aggregates, domain events e regras de negócio.

---

## Modelo de Domínio (Formalizado)

### Aggregates Roots

#### Organization (Aggregate Root)
```python
class Organization(AggregateRoot):
    id: OrganizationId (UUID)
    name: str (1-200 chars)
    cnpj: CNPJ (value object, 14 dígitos, único)
    address: Address (value object)
    phone: Phone (value object, opcional)
    active: bool
    created_at: DateTime
    updated_at: DateTime
    version: int (optimistic locking)
    
    # Invariants
    - CNPJ deve ser único globalmente
    - Name não pode ser vazio
    - Apenas Super Admin pode criar organizações
```

#### User (Aggregate Root)
```python
class User(AggregateRoot):
    id: UserId (UUID)
    organization_id: OrganizationId (FK, nullable para Super Admin)
    name: str (1-200 chars)
    email: Email (value object, único por organização)
    password_hash: PasswordHash (bcrypt)
    role: Role (enum: admin, manager, analyst, viewer)
    phone: Phone (opcional)
    unit: str (opcional, ex: apartamento, andar)
    active: bool
    mfa_enabled: bool
    mfa_secret: TOTPSecret (encrypted, opcional)
    backup_codes: List[BackupCode] (hashed)
    last_login_at: DateTime (nullable)
    created_at: DateTime
    updated_at: DateTime
    version: int
    
    # Invariants
    - Email único dentro da organização
    - Senha min 8 chars (bcrypt)
    - Apenas Super Admin pode criar Admin Geral
    - Admin de condomínio só cria/edita funcionários da própria org
    - Senha nunca retornada em responses
```

#### Contract (Aggregate Root)
```python
class Contract(AggregateRoot):
    id: ContractId (UUID)
    owner_id: UserId (FK)
    organization_id: OrganizationId (FK, denormalized para queries)
    title: str (1-500 chars)
    source: str (upload, google_drive, onedrive)
    file_path: str (storage path)
    file_hash: str (SHA256 para deduplicação)
    page_count: int
    language: Language (enum)
    status: ContractStatus (enum: uploaded, processing, analyzed, error)
    deleted_at: DateTime (soft delete)
    created_at: DateTime
    updated_at: DateTime
    version: int
    
    # Invariants
    - Owner deve pertencer à organização
    - Apenas owner ou admin da org pode acessar
    - Soft delete preserva histórico
```

#### Analysis (Aggregate Root)
```python
class Analysis(AggregateRoot):
    id: AnalysisId (UUID)
    contract_id: ContractId (FK)
    created_by_id: UserId (FK)
    organization_id: OrganizationId (FK, denormalized)
    type: AnalysisType (enum: full, clauses_only, risk_only, summary)
    status: AnalysisStatus (enum: pending, processing, completed, error)
    llm_provider: LLMProvider (enum: openai, nvidia, hermes)
    llm_model: str
    result: AnalysisResult (JSON serializable)
    error_message: str (nullable)
    execution_evidence: ExecutionEvidence (HMAC-bound, verified)
    metadata: AnalysisMetadata (tokens, cost, duration, etc.)
    created_at: DateTime
    completed_at: DateTime (nullable)
    deleted_at: DateTime (soft delete)
    version: int
    
    # Invariants
    - Contract deve pertencer à mesma organização
    - Apenas creator ou admin da org pode acessar
    - Execution evidence HMAC-bound to analysis_id + SECRET_KEY
```

#### Clause (Entity)
```python
class Clause(Entity):
    id: ClauseId (UUID)
    analysis_id: AnalysisId (FK)
    organization_id: OrganizationId (FK, denormalized)
    type: ClauseType (enum)
    content: str
    risk_score: float (0-1)
    risk_level: RiskLevel (enum: low, medium, high, critical)
    entities: List[Entity] (extracted entities)
    embedding: Vector (1536-dim, pgvector)
    created_at: DateTime
    
    # Invariants
    - Risk score entre 0-1
    - Embedding gerado apenas para cláusulas analisadas
```

#### Connector (Aggregate Root)
```python
class Connector(AggregateRoot):
    id: ConnectorId (UUID)
    organization_id: OrganizationId (FK)
    name: str
    type: ConnectorType (enum: google_drive, onedrive)
    config: ConnectorConfig (encrypted credentials)
    is_active: bool
    last_sync_at: DateTime (nullable)
    sync_status: SyncStatus (enum)
    created_at: DateTime
    updated_at: DateTime
    version: int
    
    # Invariants
    - Credenciais criptografadas em repouso
    - Apenas admin da organização pode gerenciar
```

---

## Value Objects

### CNPJ
```python
class CNPJ(ValueObject):
    value: str (14 dígitos, apenas números)
    
    # Factory
    @classmethod
    def from_string(cls, raw: str) -> CNPJ:
        digits = ''.join(c for c in raw if c.isdigit())
        if len(digits) != 14:
            raise ValueError("CNPJ deve conter 14 dígitos")
        return CNPJ(digits)
    
    # Formatted
    def formatted(self) -> str:
        return f"{self.value[:2]}.{self.value[2:5]}.{self.value[5:8]}/{self.value[8:12]}-{self.value[12:]}"
```

### Email
```python
class Email(ValueObject):
    value: str (lowercase, trimmed)
    
    @classmethod
    def from_string(cls, raw: str) -> Email:
        email = raw.strip().lower()
        if not regex.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            raise ValueError("E-mail inválido")
        return Email(email)
```

### PasswordHash
```python
class PasswordHash(ValueObject):
    value: str (bcrypt hash)
    
    @classmethod
    def create(cls, plain: str) -> PasswordHash:
        if len(plain) < 8:
            raise ValueError("Senha deve ter no mínimo 8 caracteres")
        # NÃO aplica trim - preserva espaços intencionais
        return PasswordHash(bcrypt.hash(plain))
    
    def verify(self, plain: str) -> bool:
        return bcrypt.verify(plain, self.value)
```

### Address
```python
class Address(ValueObject):
    street: str
    number: str
    complement: str (optional)
    neighborhood: str
    city: str
    state: str (UF 2 chars)
    zip_code: str (8 digits)
```

### Phone
```python
class Phone(ValueObject):
    value: str (digits only, 10-11 digits)
    
    @classmethod
    def from_string(cls, raw: str) -> Phone:
        digits = ''.join(c for c in raw if c.isdigit())
        if len(digits) not in (10, 11):
            raise ValueError("Telefone deve ter 10 ou 11 dígitos")
        return Phone(digits)
```

### Vector (pgvector)
```python
class Vector(ValueObject):
    value: List[float] (1536 dimensions)
    
    def cosine_similarity(self, other: Vector) -> float:
        # pgvector cosine similarity
        pass
```

---

## Domain Events

| Evento | Trigger | Payload | Consumers |
|--------|---------|---------|-----------|
| `ContractUploaded` | Upload bem-sucedido | `{contract_id, org_id, user_id, file_hash}` | Analysis queue, Audit log |
| `AnalysisCompleted` | Análise finalizada | `{analysis_id, contract_id, status, result_summary}` | Notification, Report generation |
| `AnalysisFailed` | Análise com erro | `{analysis_id, contract_id, error}` | Notification, Alert |
| `UserRegistered` | Registro concluído | `{user_id, org_id, role}` | Welcome email, Audit log |
| `UserLogin` | Login bem-sucedido | `{user_id, org_id, ip, user_agent}` | Audit log, Rate limit |
| `ContractAnalyzed` | Análise de contrato | `{contract_id, analysis_id, clauses_count, risk_summary}` | Report generation |
| `DataExported` | LGPD export | `{user_id, org_id, data_types}` | Audit log (LGPD) |
| `DataDeleted` | LGPD delete | `{user_id, org_id}` | Audit log (LGPD) |
| `ConnectorSyncCompleted` | Sync finalizado | `{connector_id, org_id, status, items_count}` | Notification |

---

## Domain Services (Cross-Aggregate)

### OrganizationDomainService
```python
class OrganizationDomainService:
    def can_create_organization(user: User) -> bool:
        return user.role == Role.SUPER_ADMIN
    
    def validate_cnpj_unique(cnpj: CNPJ) -> bool:
        # Check global uniqueness
        pass
```

### UserDomainService
```python
class UserDomainService:
    def can_create_user(actor: User, target_role: Role) -> bool:
        if actor.role == Role.SUPER_ADMIN:
            return True
        if actor.role == Role.ADMIN and target_role == Role.USER:
            return True
        return False
    
    def can_edit_user(actor: User, target: User) -> bool:
        if actor.role == Role.SUPER_ADMIN:
            return True
        if actor.role == Role.ADMIN and target.role == Role.USER:
            return actor.organization_id == target.organization_id
        return False
    
    def can_promote_to_admin(actor: User) -> bool:
        return actor.role == Role.SUPER_ADMIN
```

### ContractDomainService
```python
class ContractDomainService:
    def can_access_contract(user: User, contract: Contract) -> bool:
        if user.role == Role.SUPER_ADMIN:
            return True
        return contract.organization_id == user.organization_id
    
    def validate_file_upload(file: UploadFile) -> ValidationResult:
        # Check extension, size, content-type
        pass
```

### AnalysisDomainService
```python
class AnalysisDomainService:
    def can_start_analysis(user: User, contract: Contract) -> bool:
        # Check permissions, contract status, etc.
        pass
    
    def select_llm_provider(requested: Optional[LLMProvider]) -> LLMProvider:
        # Fallback logic if enabled
        pass
```

---

## Repository Interfaces (Domain Layer)

```python
class OrganizationRepository(Repository[Organization]):
    async def find_by_id(id: OrganizationId) -> Optional[Organization]
    async def find_by_cnpj(cnpj: CNPJ) -> Optional[Organization]
    async def save(org: Organization) -> None

class UserRepository(Repository[User]):
    async def find_by_id(id: UserId) -> Optional[User]
    async def find_by_email(org_id: OrganizationId, email: Email) -> Optional[User]
    async def find_by_organization(org_id: OrganizationId) -> List[User]
    async def save(user: User) -> None

class ContractRepository(Repository[Contract]):
    async def find_by_id(id: ContractId) -> Optional[Contract]
    async def find_by_organization(org_id: OrganizationId, filters: ContractFilters) -> PaginatedResult[Contract]
    async def find_by_owner(owner_id: UserId) -> List[Contract]
    async def save(contract: Contract) -> None

class AnalysisRepository(Repository[Analysis]):
    async def find_by_id(id: AnalysisId) -> Optional[Analysis]
    async def find_by_contract(contract_id: ContractId) -> List[Analysis]
    async def find_by_organization(org_id: OrganizationId, filters: AnalysisFilters) -> PaginatedResult[Analysis]
    async def save(analysis: Analysis) -> None

class ClauseRepository(Repository[Clause]):
    async def find_by_analysis(analysis_id: AnalysisId) -> List[Clause]
    async def semantic_search(org_id: OrganizationId, query_vector: Vector, filters: ClauseFilters, limit: int) -> List[Clause]
    async def save(clause: Clause) -> None
```

---

## Invariants Globais (Cross-Cutting)

| Regra | Onde Validar |
|-------|--------------|
| `organization_id` no token deve corresponder ao recurso acessado | Middleware/AuthZ |
| Super Admin (`geral: true`) ignora escopo de organização | Middleware/AuthZ |
| Soft delete preserva integridade referencial | Repository/Service |
| Audit log em todas operações sensíveis | Service/Event handler |
| LGPD: export inclui todos dados do usuário | Service |
| LGPD: delete anonimiza (configurável) | Service |
| Senha nunca em logs/responses | Middleware/Serializer |
| JWT claims: `organization_id`, `user_id`, `role`, `geral` | Token generation |

---

## Mapeamento para Código Existente

| Domain Concept | Código Existente | Localização |
|----------------|------------------|-------------|
| `Organization` | `Organization` model | `backend/app/models/organization.py` |
| `User` | `User` model | `backend/app/models/user.py` |
| `Contract` | `Contract` model | `backend/app/models/contract.py` |
| `Analysis` | `Analysis` model | `backend/app/models/analysis.py` |
| `Clause` | `Clause` model | `backend/app/models/clause.py` |
| `Connector` | `Connector` model | `backend/app/models/connector.py` |
| `CNPJ` value object | `Validacao.Cnpj()` | `backend/app/Validacao.py` |
| `Email` value object | `Validacao.Email()` | `backend/app/Validacao.py` |
| `PasswordHash` | `Validacao.Senha()` + `hashSenha` | `backend/app/Validacao.py`, `services/auth.py` |
| `OrganizationDomainService` | `EscopoUsuario.ValidarAdministradorGeral()` | `backend/app/Dtos/Dtos.cs` (ou Python equivalente) |
| `UserDomainService` | `EscopoUsuario.ValidarCondominio()` | `backend/app/Dtos/Dtos.cs` |
| `ContractRepository` | `IAplicacaoDbContext.Condominios` | `backend/app/Abstracoes/Interfaces.cs` |

---

## Gaps de Domínio (Para Construction)

| Gap | Descrição | Prioridade |
|-------|-------------|------------|
| Value Objects não formalizados | CNPJ, Email, PasswordHash, Address, Phone como classes | Alta |
| Domain Events não implementados | Event-driven architecture para async processing | Média |
| Domain Services não formalizados | Lógica de negócio espalhada em Services | Alta |
| Repository Interfaces | Abstração para facilitar testes | Média |
| Aggregates não enforçados | Invariants validadas apenas em Services | Alta |
| Domain Events publishing | Integração com message broker (Celery/Redis) | Média |

---

## Próximos Passos (AI-DLC)

1. **Contract-design**: Definir contratos API (OpenAPI), schemas de validação, versionamento
2. **Delivery-planning**: CI/CD, environments, deploy strategy, quality gates
3. **Approval-handoff**: Gate para prosseguir à Construction

---

*Domain design formalizado baseado em reverse-engineering. Baseline para Construction phase.*