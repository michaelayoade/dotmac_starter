"""add branding setting domain

Revision ID: 006_branding_setting_domain
Revises: 005_mfa_totp_replay_counter
Create Date: 2026-05-04 00:00:00.000000

"""

from alembic import op

revision = "006_branding_setting_domain"
down_revision = "005_mfa_totp_replay_counter"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE settingdomain ADD VALUE IF NOT EXISTS 'branding'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely without rebuilding the type.
    pass
