"""restricciones de costos y avance

Revision ID: 0b0f61ca6e70
Revises: 201d94aaf339
Create Date: 2026-10-19 19:36:31.055950

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0b0f61ca6e70"
down_revision: Union[str, Sequence[str], None] = "201d94aaf339"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_check_constraint(
        op.f("ck_tasks_percent_range"),
        "tasks",
        "percent_complete BETWEEN 0 AND 100",
    )
    op.create_check_constraint(
        op.f("ck_tasks_costs_non_negative"),
        "tasks",
        "fixed_cost >= 0 AND actual_cost >= 0",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f("ck_tasks_costs_non_negative"), "tasks", type_="check")
    op.drop_constraint(op.f("ck_tasks_percent_range"), "tasks", type_="check")
