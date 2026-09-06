import logging
import time
from collections.abc import Callable
from io import BytesIO
from uuid import uuid4

from PIL import Image

from shared.python.storage_paths import artifact_path
from app.pipelines.canny_control import create_canny_control
from app.pipelines.postprocessing import composite_original_cutout, compose_product_canvas, prepare_generation_canvas
from app.pipelines.sdxl_generation import SDXLModelStack, VariationResult, generate_variations, release_cuda_memory
from app.services.db_client import ClaimedJob, WorkerDatabase
from app.services.storage_client import WorkerStorage

logger = logging.getLogger("studio.worker")
GPU_FAILURE_MARKERS = ("cuda", "out of memory", "cublas", "from_pretrained", "diffusers", "weights")


def is_gpu_failure(error: Exception) -> bool:
    if isinstance(error, MemoryError):
        return True
    message = str(error).lower()
    return any(marker in message for marker in GPU_FAILURE_MARKERS)


def durable_failure_message(error: Exception) -> str:
    if is_gpu_failure(error):
        return f"GPU/model failure ({type(error).__name__}): {error}"
    return str(error)


class GenerationProcessor:
    def __init__(self, database: WorkerDatabase, storage: WorkerStorage, stack: SDXLModelStack):
        self.database = database
        self.storage = storage
        self.stack = stack

    def process(self, job: ClaimedJob) -> None:
        started_at = time.perf_counter()
        request_id = job.metrics.get("request_id")
        logger.info(
            "generation processing started",
            extra={"job_id": str(job.id), "job_type": job.job_type, "request_id": request_id},
        )
        image_record = self.database.get_image(job.image_id)
        if image_record is None or not image_record.get("cutout_path"):
            raise ValueError(f"Ready cutout for image {job.image_id} was not found")
        cutout = Image.open(BytesIO(self.storage.read_bytes(image_record["cutout_path"]))).convert("RGBA")
        composition = compose_product_canvas(
            cutout,
            canvas_size=int(job.settings.get("canvas_size", 1024)),
        )
        control = create_canny_control(
            composition.canvas,
            alpha=composition.product_mask,
            include_luminance=False,
        )
        init_image = prepare_generation_canvas(composition.canvas, job.scene_preset or "luxury_studio")
        control_buffer = BytesIO()
        control.save(control_buffer, format="PNG")
        control_bytes = control_buffer.getvalue()
        completed_seeds = self.database.get_succeeded_output_seeds(job.id)
        successes = len(completed_seeds)
        failures: list[str] = []

        def persist_result(index: int, result: VariationResult) -> None:
            nonlocal successes
            output_id = uuid4()
            output_path = artifact_path("outputs", output_id, "png")
            control_path = artifact_path("control", output_id, "png")
            self.storage.write_bytes(control_path, control_bytes)
            variation_metrics = {
                "variation_index": index,
                "duration_ms": result.duration_ms,
                "settings": job.settings,
            }
            if result.image is None:
                failures.append(result.error_message or "Variation failed")
                self.database.save_generation_output(
                    output_id,
                    job.id,
                    output_path,
                    result.seed,
                    composition.canvas.width,
                    composition.canvas.height,
                    status="failed",
                    control_path=control_path,
                    metrics=variation_metrics,
                    error_message=result.error_message,
                )
                return

            background_path = artifact_path("diagnostics", output_id, "png")
            background_buffer = BytesIO()
            result.image.save(background_buffer, format="PNG")
            self.storage.write_bytes(background_path, background_buffer.getvalue())
            final_image = composite_original_cutout(result.image, composition.canvas)
            output_buffer = BytesIO()
            final_image.save(output_buffer, format="PNG")
            self.storage.write_bytes(output_path, output_buffer.getvalue())
            self.database.save_generation_output(
                output_id,
                job.id,
                output_path,
                result.seed,
                final_image.width,
                final_image.height,
                background_path=background_path,
                control_path=control_path,
                metrics=variation_metrics,
            )
            successes += 1

        results = generate_variations(
            self.stack,
            prompt=job.prompt or "professional product photography",
            negative_prompt=job.negative_prompt,
            init_image=init_image,
            control_image=control,
            variation_count=job.variation_count or 3,
            base_seed=job.base_seed,
            settings=job.settings,
            on_result=persist_result,
            skip_seeds=completed_seeds,
        )

        requested = job.variation_count or 3
        status = "succeeded" if successes == requested else "partially_succeeded" if successes else "failed"
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        self.database.complete_generation_job(
            job.id,
            status,
            error_message="; ".join(failures) if failures else None,
            metrics={
                "completed_outputs": successes,
                "total_outputs": requested,
                "duration_ms": duration_ms,
                "settings": job.settings,
            },
        )
        logger.info(
            "generation processing completed",
            extra={
                "job_id": str(job.id),
                "job_type": job.job_type,
                "duration_ms": duration_ms,
                "request_id": request_id,
            },
        )


class JobRunner:
    def __init__(self, database: WorkerDatabase, handlers: dict[str, Callable[[ClaimedJob], None]] | None = None):
        self.database = database
        self.handlers = handlers or {}

    def run_once(self) -> ClaimedJob | None:
        job = self.database.claim_next_job()
        if job is None:
            return None
        handler = self.handlers.get(job.job_type)
        if handler is None:
            message = f"No worker handler registered for job type '{job.job_type}'."
            self.database.mark_failed(job.id, message)
            logger.error(message)
            return job
        started_at = time.perf_counter()
        request_id = job.metrics.get("request_id")
        logger.info(
            "claimed job",
            extra={"job_id": str(job.id), "job_type": job.job_type, "request_id": request_id},
        )
        try:
            handler(job)
            logger.info(
                "completed job",
                extra={
                    "job_id": str(job.id),
                    "job_type": job.job_type,
                    "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
                    "request_id": request_id,
                },
            )
        except Exception as exc:
            message = durable_failure_message(exc)
            if is_gpu_failure(exc):
                release_cuda_memory()
            self.database.mark_failed(job.id, message)
            logger.exception(
                "job failed",
                extra={"job_id": str(job.id), "job_type": job.job_type, "request_id": request_id},
            )
        return job
