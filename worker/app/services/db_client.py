from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


CLAIM_NEXT_JOB_SQL = text(
    """
    WITH next_job AS (
        SELECT id
        FROM generation_jobs
        WHERE status = 'pending'
        ORDER BY created_at ASC
        FOR UPDATE SKIP LOCKED
        LIMIT 1
    )
    UPDATE generation_jobs AS job
    SET status = 'running', started_at = now(), updated_at = now()
    FROM next_job
    WHERE job.id = next_job.id
    RETURNING job.id, job.image_id, job.job_type, job.scene_preset, job.prompt,
              job.negative_prompt, job.variation_count, job.base_seed, job.settings, job.metrics
    """
)

RECOVER_STALE_GENERATION_JOBS_SQL = text(
    """
    UPDATE generation_jobs
    SET status = 'pending', error_message = NULL, started_at = NULL,
        completed_at = NULL, updated_at = now()
    WHERE status = 'running'
      AND job_type = 'background_generation'
      AND started_at < now() - make_interval(secs => :timeout_seconds)
    RETURNING id
    """
)


@dataclass(frozen=True)
class ClaimedJob:
    id: UUID
    image_id: UUID
    job_type: str
    scene_preset: str | None
    prompt: str | None
    negative_prompt: str | None
    variation_count: int | None
    base_seed: int | None
    settings: dict
    metrics: dict = field(default_factory=dict)


class WorkerDatabase:
    def __init__(self, database_url: str, engine: Engine | None = None):
        self.engine = engine or create_engine(database_url, pool_pre_ping=True)

    def claim_next_job(self) -> ClaimedJob | None:
        with self.engine.begin() as connection:
            row = connection.execute(CLAIM_NEXT_JOB_SQL).mappings().first()
        return ClaimedJob(**row) if row else None

    def recover_stale_jobs(self, timeout_seconds: int) -> tuple[int, int]:
        if timeout_seconds <= 0:
            raise ValueError("Job timeout must be positive")
        message = "Worker restarted after the job exceeded its execution timeout. Retry the job."
        with self.engine.begin() as connection:
            requeued = connection.execute(
                RECOVER_STALE_GENERATION_JOBS_SQL,
                {"timeout_seconds": timeout_seconds},
            ).mappings().all()
            failed = connection.execute(
                text(
                    """
                    UPDATE generation_jobs
                    SET status = 'failed', error_message = :message,
                        completed_at = now(), updated_at = now()
                    WHERE status = 'running'
                      AND job_type != 'background_generation'
                      AND started_at < now() - make_interval(secs => :timeout_seconds)
                    RETURNING id, image_id, job_type
                    """
                ),
                {"message": message, "timeout_seconds": timeout_seconds},
            ).mappings().all()
            preprocessing_image_ids = [row["image_id"] for row in failed if row["job_type"] == "background_removal"]
            if preprocessing_image_ids:
                connection.execute(
                    text("UPDATE images SET status = 'failed', updated_at = now() WHERE id = ANY(:image_ids)"),
                    {"image_ids": preprocessing_image_ids},
                )
        return len(requeued), len(failed)

    def get_succeeded_output_seeds(self, job_id: UUID) -> set[int]:
        with self.engine.begin() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT seed
                    FROM generated_outputs
                    WHERE generation_job_id = :job_id
                      AND status = 'succeeded'
                      AND seed IS NOT NULL
                    """
                ),
                {"job_id": job_id},
            ).scalars().all()
        return set(rows)

    def mark_failed(self, job_id: UUID, message: str) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE generation_jobs AS job
                    SET status = 'failed', error_message = :message,
                        completed_at = now(), updated_at = now()
                    WHERE id = :job_id
                    """
                ),
                {"job_id": job_id, "message": message},
            )
            connection.execute(
                text(
                    """
                    UPDATE images
                    SET status = 'failed', updated_at = now()
                    WHERE id = (
                        SELECT image_id FROM generation_jobs
                        WHERE id = :job_id AND job_type = 'background_removal'
                    )
                    """
                ),
                {"job_id": job_id},
            )

    def get_image(self, image_id: UUID) -> dict | None:
        with self.engine.begin() as connection:
            row = connection.execute(
                text("SELECT id, original_path, mask_path, cutout_path, width, height, status FROM images WHERE id = :image_id"),
                {"image_id": image_id},
            ).mappings().first()
        return dict(row) if row else None

    def save_generation_output(
        self,
        output_id: UUID,
        job_id: UUID,
        output_path: str,
        seed: int,
        width: int,
        height: int,
        status: str = "succeeded",
        background_path: str | None = None,
        control_path: str | None = None,
        metrics: dict | None = None,
        error_message: str | None = None,
    ) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO generated_outputs
                        (id, generation_job_id, output_path, background_path, control_path,
                         seed, width, height, status, metrics, error_message)
                    VALUES
                        (:output_id, :job_id, :output_path, :background_path, :control_path,
                         :seed, :width, :height, :status, CAST(:metrics AS jsonb), :error_message)
                    """
                ),
                {
                    "output_id": output_id,
                    "job_id": job_id,
                    "output_path": output_path,
                    "seed": seed,
                    "width": width,
                    "height": height,
                    "status": status,
                    "background_path": background_path,
                    "control_path": control_path,
                    "metrics": _json(metrics or {}),
                    "error_message": error_message,
                },
            )

    def complete_generation_job(
        self,
        job_id: UUID,
        status: str,
        error_message: str | None = None,
        metrics: dict | None = None,
    ) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE generation_jobs
                    SET status = :status,
                        error_message = :error_message,
                        metrics = COALESCE(metrics, '{}'::jsonb) || CAST(:metrics AS jsonb),
                        completed_at = now(), updated_at = now()
                    WHERE id = :job_id
                    """
                ),
                {
                    "job_id": job_id,
                    "status": status,
                    "error_message": error_message,
                    "metrics": _json(metrics or {}),
                },
            )

    def complete_background_removal(
        self,
        job_id: UUID,
        image_id: UUID,
        mask_path: str,
        cutout_path: str,
        metadata: dict,
    ) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE images
                    SET status = 'ready', mask_path = :mask_path, cutout_path = :cutout_path,
                        metadata = COALESCE(metadata, '{}'::jsonb) || CAST(:metadata AS jsonb),
                        updated_at = now()
                    WHERE id = :image_id
                    """
                ),
                {"image_id": image_id, "mask_path": mask_path, "cutout_path": cutout_path, "metadata": _json(metadata)},
            )
            connection.execute(
                text(
                    """
                    UPDATE generation_jobs
                    SET status = 'succeeded', completed_at = now(), updated_at = now()
                    WHERE id = :job_id
                    """
                ),
                {"job_id": job_id},
            )


def _json(value: dict) -> str:
    import json

    return json.dumps(value)
