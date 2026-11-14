"""b0 all tables

Revision ID: 0001
Revises:
"""
import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table('action_rules',
    sa.Column('code', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=False),
    sa.Column('cost_usd', sa.Double(), nullable=False),
    sa.Column('approval_role', sa.String(), nullable=False),
    sa.Column('categories', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('min_high_risk_orders', sa.Integer(), nullable=False),
    sa.Column('requires_evidence', sa.Boolean(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_table('documents',
    sa.Column('code', sa.String(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('origin', sa.String(), nullable=False),
    sa.Column('content_hash', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('chunk_count', sa.Integer(), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_table('eval_runs',
    sa.Column('kind', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('llm_cache',
    sa.Column('request_hash', sa.String(), nullable=False),
    sa.Column('model', sa.String(), nullable=False),
    sa.Column('response', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('cost_usd', sa.Double(), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('request_hash')
    )
    op.create_table('model_versions',
    sa.Column('task', sa.String(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('family', sa.String(), nullable=False),
    sa.Column('artifact_path', sa.String(), nullable=False),
    sa.Column('artifact_hash', sa.String(), nullable=False),
    sa.Column('snapshot_hash', sa.String(), nullable=True),
    sa.Column('git_commit', sa.String(), nullable=True),
    sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('gate', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('promoted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('users',
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('password_hash', sa.String(), nullable=False),
    sa.Column('role', sa.String(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('audit_log',
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('action', sa.String(), nullable=False),
    sa.Column('entity', sa.String(), nullable=False),
    sa.Column('entity_id', sa.String(), nullable=True),
    sa.Column('detail', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('chat_messages',
    sa.Column('session_id', sa.String(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.String(), nullable=False),
    sa.Column('content', sa.String(), nullable=False),
    sa.Column('tool_calls', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('citations', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_messages_session_id'), 'chat_messages', ['session_id'], unique=False)
    op.create_table('chunks',
    sa.Column('document_id', sa.Integer(), nullable=False),
    sa.Column('n', sa.Integer(), nullable=False),
    sa.Column('citation_key', sa.String(), nullable=False),
    sa.Column('section', sa.String(), nullable=True),
    sa.Column('text', sa.String(), nullable=False),
    sa.Column('tsv', postgresql.TSVECTOR(), sa.Computed("to_tsvector('english', text)", persisted=True), nullable=False),
    sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=384), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('citation_key')
    )
    op.create_index('ix_chunks_embedding', 'chunks', ['embedding'], unique=False, postgresql_using='hnsw', postgresql_ops={'embedding': 'vector_cosine_ops'})
    op.create_index('ix_chunks_tsv', 'chunks', ['tsv'], unique=False, postgresql_using='gin')
    op.create_table('incidents',
    sa.Column('tweet_id', sa.String(), nullable=True),
    sa.Column('text', sa.String(), nullable=False),
    sa.Column('event', sa.String(), nullable=True),
    sa.Column('source', sa.String(), nullable=False),
    sa.Column('gold_label', sa.String(), nullable=True),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('predicted_label', sa.String(), nullable=True),
    sa.Column('confidence', sa.Double(), nullable=True),
    sa.Column('screening_score', sa.Double(), nullable=True),
    sa.Column('model_version_id', sa.Integer(), nullable=True),
    sa.Column('reviewed_label', sa.String(), nullable=True),
    sa.Column('reviewed_by', sa.Integer(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('review_source', sa.String(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['model_version_id'], ['model_versions.id'], ),
    sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('jobs',
    sa.Column('kind', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('log', sa.String(), nullable=False),
    sa.Column('error', sa.String(), nullable=True),
    sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('orders',
    sa.Column('order_id', sa.Integer(), nullable=False),
    sa.Column('order_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('market', sa.String(), nullable=False),
    sa.Column('order_region', sa.String(), nullable=False),
    sa.Column('shipping_mode', sa.String(), nullable=False),
    sa.Column('customer_segment', sa.String(), nullable=False),
    sa.Column('order_total', sa.Double(), nullable=False),
    sa.Column('item_count', sa.Integer(), nullable=False),
    sa.Column('features', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('block', sa.String(), nullable=False),
    sa.Column('released', sa.Boolean(), nullable=False),
    sa.Column('late', sa.Boolean(), nullable=True),
    sa.Column('risk_score', sa.Double(), nullable=True),
    sa.Column('risk_band', sa.String(), nullable=True),
    sa.Column('factors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('model_version_id', sa.Integer(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['model_version_id'], ['model_versions.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('order_id')
    )
    op.create_table('investigations',
    sa.Column('incident_id', sa.Integer(), nullable=False),
    sa.Column('scope', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('degraded', sa.Boolean(), nullable=False),
    sa.Column('state', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('report', sa.String(), nullable=True),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['incident_id'], ['incidents.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('investigation_actions',
    sa.Column('investigation_id', sa.Integer(), nullable=False),
    sa.Column('rule_code', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('eligible', sa.Boolean(), nullable=False),
    sa.Column('reason', sa.String(), nullable=False),
    sa.Column('rank', sa.Integer(), nullable=True),
    sa.Column('rationale', sa.String(), nullable=True),
    sa.Column('decision', sa.String(), nullable=False),
    sa.Column('decided_by', sa.Integer(), nullable=True),
    sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['decided_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['investigation_id'], ['investigations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('investigation_steps',
    sa.Column('investigation_id', sa.Integer(), nullable=False),
    sa.Column('node', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('output', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('error', sa.String(), nullable=True),
    sa.Column('duration_ms', sa.Integer(), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['investigation_id'], ['investigations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('investigation_steps')
    op.drop_table('investigation_actions')
    op.drop_table('investigations')
    op.drop_table('orders')
    op.drop_table('jobs')
    op.drop_table('incidents')
    op.drop_index('ix_chunks_tsv', table_name='chunks', postgresql_using='gin')
    op.drop_index('ix_chunks_embedding', table_name='chunks', postgresql_using='hnsw', postgresql_ops={'embedding': 'vector_cosine_ops'})
    op.drop_table('chunks')
    op.drop_index(op.f('ix_chat_messages_session_id'), table_name='chat_messages')
    op.drop_table('chat_messages')
    op.drop_table('audit_log')
    op.drop_table('users')
    op.drop_table('model_versions')
    op.drop_table('llm_cache')
    op.drop_table('eval_runs')
    op.drop_table('documents')
    op.drop_table('action_rules')
