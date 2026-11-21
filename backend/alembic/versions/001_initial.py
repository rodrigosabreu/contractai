"""Initial migration - ContractAI schema.

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Organizations table
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('plan', sa.Enum('free', 'pro', 'enterprise', name='organizationplan'), nullable=False, server_default='free'),
        sa.Column('is_single_tenant', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('settings', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug', name='uq_organizations_slug'),
    )
    op.create_index('ix_organizations_deleted_at', 'organizations', ['deleted_at'])
    op.create_index('ix_organizations_slug', 'organizations', ['slug'], unique=True)

    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('role', sa.Enum('admin', 'manager', 'analyst', 'viewer', name='userrole'), nullable=False, server_default='viewer'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('mfa_secret', sa.String(255), nullable=True),
        sa.Column('mfa_backup_codes', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('email', name='uq_users_email'),
    )
    op.create_index('ix_users_deleted_at', 'users', ['deleted_at'])
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_organization_id', 'users', ['organization_id'])
    op.create_index('ix_users_organization_id_deleted_at', 'users', ['organization_id', 'deleted_at'])

    # Token Blacklist table
    op.create_table(
        'token_blacklist',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('jti', sa.String(64), nullable=False),
        sa.Column('token_type', sa.Enum('access', 'refresh', 'reset', name='tokentype'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reason', sa.String(50), nullable=False, server_default='revoked'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jti', name='uq_token_blacklist_jti'),
    )
    op.create_index('ix_token_blacklist_jti', 'token_blacklist', ['jti'], unique=True)
    op.create_index('ix_token_blacklist_expires_at', 'token_blacklist', ['expires_at'])
    op.create_index('ix_token_blacklist_user_id_type', 'token_blacklist', ['user_id', 'token_type'])

    # Connectors table
    op.create_table(
        'connectors',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('config', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('credentials', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_connectors_deleted_at', 'connectors', ['deleted_at'])
    op.create_index('ix_connectors_organization_id', 'connectors', ['organization_id'])

    # Contracts table
    op.create_table(
        'contracts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source', sa.Enum('upload', 'google_drive', 'onedrive', 'api', name='contractsource'), nullable=False, server_default='upload'),
        sa.Column('source_id', sa.String(255), nullable=True),
        sa.Column('source_url', sa.String(1000), nullable=True),
        sa.Column('file_path', sa.String(1000), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('status', sa.Enum('uploaded', 'parsing', 'parsed', 'analyzing', 'analyzed', 'error', name='contractstatus'), nullable=False, server_default='uploaded'),
        sa.Column('content_text', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=True),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('language', sa.String(10), nullable=False, server_default='pt-BR'),
        sa.Column('meta', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_contracts_deleted_at', 'contracts', ['deleted_at'])
    op.create_index('ix_contracts_organization_id', 'contracts', ['organization_id'])
    op.create_index('ix_contracts_owner_id', 'contracts', ['owner_id'])
    op.create_index('ix_contracts_source', 'contracts', ['source'])
    op.create_index('ix_contracts_source_id', 'contracts', ['source_id'])
    op.create_index('ix_contracts_status', 'contracts', ['status'])
    op.create_index('ix_contracts_content_hash', 'contracts', ['content_hash'])

    # Contract Versions table (for diff/comparison)
    op.create_table(
        'contract_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contract_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('content_text', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('contract_id', 'version_number', name='uq_contract_versions_contract_version'),
    )
    op.create_index('ix_contract_versions_contract_id', 'contract_versions', ['contract_id'])

    # Analyses table
    op.create_table(
        'analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contract_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.Enum('full', 'clause_extraction', 'risk_assessment', 'comparison', 'entity_extraction', name='analysistype'), nullable=False, server_default='full'),
        sa.Column('status', sa.Enum('pending', 'processing', 'completed', 'failed', name='analysisstatus'), nullable=False, server_default='pending'),
        sa.Column('llm_provider', sa.String(50), nullable=False),
        sa.Column('llm_model', sa.String(100), nullable=False),
        sa.Column('prompt_version', sa.String(50), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('total_cost_usd', sa.Float(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('result', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_analyses_deleted_at', 'analyses', ['deleted_at'])
    op.create_index('ix_analyses_organization_id', 'analyses', ['organization_id'])
    op.create_index('ix_analyses_contract_id', 'analyses', ['contract_id'])
    op.create_index('ix_analyses_created_by_id', 'analyses', ['created_by_id'])
    op.create_index('ix_analyses_status', 'analyses', ['status'])
    op.create_index('ix_analyses_type', 'analyses', ['type'])

    # Clauses table with pgvector
    op.create_table(
        'clauses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contract_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('clause_number', sa.String(50), nullable=True),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('type', sa.Enum('parties', 'definitions', 'scope', 'obligations', 'payment', 'term', 'termination', 'liability', 'indemnification', 'confidentiality', 'intellectual_property', 'dispute_resolution', 'force_majeure', 'governing_law', 'amendment', 'assignment', 'notices', 'general', 'other', name='clausetype'), nullable=False, server_default='general'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('page_start', sa.Integer(), nullable=True),
        sa.Column('page_end', sa.Integer(), nullable=True),
        sa.Column('char_start', sa.Integer(), nullable=True),
        sa.Column('char_end', sa.Integer(), nullable=True),
        sa.Column('language', sa.String(10), nullable=False, server_default='pt-BR'),
        sa.Column('meta', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('embedding', postgresql.VECTOR(1536), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('risk_level', sa.Enum('low', 'medium', 'high', 'critical', name='risklevel'), nullable=False, server_default='low'),
        sa.Column('risk_factors', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('risk_explanation', sa.Text(), nullable=True),
        sa.Column('entities', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['analysis_id'], ['analyses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_clauses_deleted_at', 'clauses', ['deleted_at'])
    op.create_index('ix_clauses_analysis_id', 'clauses', ['analysis_id'])
    op.create_index('ix_clauses_contract_id', 'clauses', ['contract_id'])
    op.create_index('ix_clauses_organization_id', 'clauses', ['organization_id'])
    op.create_index('ix_clauses_type', 'clauses', ['type'])
    op.create_index('ix_clauses_risk_level', 'clauses', ['risk_level'])
    op.create_index('ix_clauses_risk_score', 'clauses', ['risk_score'])
    op.create_index('ix_clauses_content_hash', 'clauses', ['content_hash'])
    op.create_index('ix_clauses_embedding', 'clauses', ['embedding'], postgresql_using='ivfflat', postgresql_with={'lists': 100})

    # Audit Log table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.String(100), nullable=True),
        sa.Column('status', sa.Enum('success', 'failure', 'partial', name='auditstatus'), nullable=False, server_default='success'),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('request_id', sa.String(100), nullable=True),
        sa.Column('details', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_audit_logs_organization_id', 'audit_logs', ['organization_id'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_resource_type_id', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('ix_audit_logs_status', 'audit_logs', ['status'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('audit_logs')
    op.drop_table('clauses')
    op.drop_table('analyses')
    op.drop_table('contract_versions')
    op.drop_table('contracts')
    op.drop_table('connectors')
    op.drop_table('token_blacklist')
    op.drop_table('users')
    op.drop_table('organizations')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS auditstatus')
    op.execute('DROP TYPE IF EXISTS risklevel')
    op.execute('DROP TYPE IF EXISTS clausetype')
    op.execute('DROP TYPE IF EXISTS analysistype')
    op.execute('DROP TYPE IF EXISTS contractstatus')
    op.execute('DROP TYPE IF EXISTS contractsource')
    op.execute('DROP TYPE IF EXISTS userrole')
    op.execute('DROP TYPE IF EXISTS organizationplan')
    op.execute('DROP TYPE IF EXISTS tokentype')
    op.execute('DROP TYPE IF EXISTS revocationreason')
    op.execute('DROP TYPE IF EXISTS auditaction')