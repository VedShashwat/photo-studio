import logging
import time

from app.config import get_worker_settings
from app.job_runner import GenerationProcessor, JobRunner
from app.logging import configure_logging
from app.models.model_registry import ModelRegistry
from app.pipelines.background_removal import BackgroundRemovalProcessor
from app.services.db_client import WorkerDatabase
from app.services.storage_client import WorkerStorage

logger = logging.getLogger("studio.worker")


def main() -> None:
    settings = get_worker_settings()
    configure_logging(settings.log_level)
    database = WorkerDatabase(settings.database_url)
    requeued_jobs, failed_jobs = database.recover_stale_jobs(settings.job_timeout_seconds)
    if requeued_jobs:
        logger.warning("requeued %s interrupted generation job(s)", requeued_jobs)
    if failed_jobs:
        logger.warning("marked %s stale preprocessing job(s) as failed", failed_jobs)
    storage = WorkerStorage(settings.storage_root)
    registry = ModelRegistry(
        settings.background_removal_model,
        settings.device,
        settings.torch_dtype,
        settings.model_cache_dir,
        settings.sdxl_base_model,
        settings.sdxl_canny_controlnet_model,
        settings.sdxl_offload_mode,
    )
    processor = BackgroundRemovalProcessor(database, storage, registry.birefnet)
    generation_processor = GenerationProcessor(database, storage, registry.sdxl)
    runner = JobRunner(
        database,
        {
            "background_removal": processor.process,
            "background_generation": generation_processor.process,
        },
    )
    logger.info("single-worker PostgreSQL queue loop started")
    while True:
        runner.run_once()
        time.sleep(settings.job_poll_interval_seconds)


if __name__ == "__main__":
    main()
