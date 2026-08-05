import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Image(Base):
    __tablename__ = "images"
    __table_args__ = (Index("ix_images_created_at", "created_at"), Index("ix_images_status", "status"))

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_path: Mapped[str] = mapped_column(String(512))
    mask_path: Mapped[str | None] = mapped_column(String(512))
    cutout_path: Mapped[str | None] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(100))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="uploaded", index=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    generation_jobs: Mapped[list["GenerationJob"]] = relationship(back_populates="image")
    prompt_history: Mapped[list["PromptHistory"]] = relationship(back_populates="image")


class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    __table_args__ = (
        Index("ix_generation_jobs_status_created", "status", "created_at"),
        Index("ix_generation_jobs_image_created", "image_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("images.id"), index=True)
    job_type: Mapped[str] = mapped_column(String(64), default="background_generation")
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    scene_preset: Mapped[str | None] = mapped_column(String(64))
    prompt: Mapped[str | None] = mapped_column(Text)
    negative_prompt: Mapped[str | None] = mapped_column(Text)
    variation_count: Mapped[int | None] = mapped_column(Integer)
    base_seed: Mapped[int | None] = mapped_column(Integer)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    image: Mapped[Image] = relationship(back_populates="generation_jobs")
    outputs: Mapped[list["GeneratedOutput"]] = relationship(back_populates="generation_job")
    prompt_history: Mapped[list["PromptHistory"]] = relationship(back_populates="generation_job")


class GeneratedOutput(Base):
    __tablename__ = "generated_outputs"
    __table_args__ = (Index("ix_generated_outputs_created_at", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generation_job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("generation_jobs.id"), index=True)
    output_path: Mapped[str] = mapped_column(String(512))
    background_path: Mapped[str | None] = mapped_column(String(512))
    control_path: Mapped[str | None] = mapped_column(String(512))
    seed: Mapped[int | None] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    generation_job: Mapped[GenerationJob] = relationship(back_populates="outputs")


class PromptHistory(Base):
    __tablename__ = "prompt_history"
    __table_args__ = (Index("ix_prompt_history_created_at", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("images.id"), index=True)
    generation_job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("generation_jobs.id"), index=True)
    scene_preset: Mapped[str | None] = mapped_column(String(64))
    prompt: Mapped[str] = mapped_column(Text)
    negative_prompt: Mapped[str | None] = mapped_column(Text)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    image: Mapped[Image] = relationship(back_populates="prompt_history")
    generation_job: Mapped[GenerationJob | None] = relationship(back_populates="prompt_history")
