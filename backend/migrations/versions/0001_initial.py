"""Create initial studio tables."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("original_path", sa.String(length=512), nullable=False),
        sa.Column("mask_path", sa.String(length=512)),
        sa.Column("cutout_path", sa.String(length=512)),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_images_created_at", "images", ["created_at"])
    op.create_index("ix_images_status", "images", ["status"])
    op.create_index("ix_images_sha256", "images", ["sha256"])

    op.create_table(
        "generation_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("image_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("images.id"), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("scene_preset", sa.String(length=64)),
        sa.Column("prompt", sa.Text()),
        sa.Column("negative_prompt", sa.Text()),
        sa.Column("variation_count", sa.Integer()),
        sa.Column("base_seed", sa.Integer()),
        sa.Column("settings", postgresql.JSONB(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_generation_jobs_status_created", "generation_jobs", ["status", "created_at"])
    op.create_index("ix_generation_jobs_image_created", "generation_jobs", ["image_id", "created_at"])

    op.create_table(
        "generated_outputs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("generation_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("generation_jobs.id"), nullable=False),
        sa.Column("output_path", sa.String(length=512), nullable=False),
        sa.Column("background_path", sa.String(length=512)),
        sa.Column("control_path", sa.String(length=512)),
        sa.Column("seed", sa.Integer()),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_generated_outputs_generation_job_id", "generated_outputs", ["generation_job_id"])
    op.create_index("ix_generated_outputs_created_at", "generated_outputs", ["created_at"])

    op.create_table(
        "prompt_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("image_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("images.id"), nullable=False),
        sa.Column("generation_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("generation_jobs.id")),
        sa.Column("scene_preset", sa.String(length=64)),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("negative_prompt", sa.Text()),
        sa.Column("settings", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_prompt_history_image_id", "prompt_history", ["image_id"])
    op.create_index("ix_prompt_history_generation_job_id", "prompt_history", ["generation_job_id"])
    op.create_index("ix_prompt_history_created_at", "prompt_history", ["created_at"])


def downgrade() -> None:
    op.drop_table("prompt_history")
    op.drop_table("generated_outputs")
    op.drop_table("generation_jobs")
    op.drop_table("images")
