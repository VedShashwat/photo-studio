# Project Progress Checkpoint

Last updated: 2026-09-13 UTC

## Repository

- Local project folder: `/home/user/photo-studio`.
- GitHub repository: `https://github.com/VedShashwat/photo-studio` on branch `main`.
- Compose uses the stable project name `photo-studio`; the existing PostgreSQL data
  was dumped and restored into `photo-studio_postgres_data` during the folder rename.
- `.gitignore` excludes `.env`, Python/Node caches, the 32 GB model cache, generated
  storage, logs, IDE files, and local agent metadata. Only storage/cache sentinels are
  tracked. `.env.example`, `.gitattributes`, MIT license, CI, and a safe generated demo
  output are included for a complete public portfolio repository.

## Quality Acceptance Completed - 2026-09-13

The runtime completion state below remains valid, but visual review and user feedback
identified weak prompt adherence in the old accepted outputs. Investigation found that
the img2img seed contained the complete product, Canny retained interior label edges,
the default negative prompt suppressed `extra object` scene details, and frontend
inference settings were hardcoded. The implementation now uses a product-free preset
scene plate, silhouette-only Canny for generation, the roadmap's static photography
style suffix through SDXL's second text encoder, non-conflicting preset prompts, and
visible/restorable inference controls. Same-seed luxury and outdoor benchmarks proved
that prompts now materially change the generated environment while the final composite
preserves the original product exactly.

Current durable acceptance run:

- New photorealistic serum source asset: `storage/demo-assets/source-serum.png`.
- Uploaded image: `a8b1e8d5-17a0-4541-a1c7-0233b5e777dc`.
- BiRefNet job `d06da3b7-e5b3-4322-99c9-a4dcc90f6447` succeeded.
- Three-output luxury generation job `a9274d9f-40dc-46fc-969f-4c3e764eccc6`
  succeeded `3/3`. Outputs are `542f7ce5-cc0b-4942-845e-f9d21cd033c9`
  (ribbed charcoal/reflection), `bd89cbe7-b581-4247-bea7-645ded89794b`
  (warm spotlight/stone), and `093db273-c773-43ad-95b4-2b016cc2cea2`
  (dark studio/pedestal), with deterministic seeds 31415-31417.
- An interruption after those outputs exposed a queue recovery gap. Stale generation
  jobs are now requeued and the processor skips already-successful deterministic seeds;
  stale preprocessing remains failed for safety. Worker tests pass `28 passed, 1 skipped`.
- Native worker exec session `29623` recovered this job and rendered only missing seed
  `31417` in 373 seconds, proving restart-safe continuation. That worker was stopped.
- The obsolete illustrated demo and its artifacts were deleted. The database retains
  exactly this one polished history job. Refreshed frontend and worker images are built,
  and the Docker worker is now the sole queue consumer.
- Browser acceptance and visual review passed at 1440 px and 390 px. History restore
  now also shows the restored source image and refreshes after a newly completed job.

## Authoritative State

The rescoped AI Product Photography Studio is feature-complete and running as a
single-machine Docker demo. The implemented scope is exactly:

- validated JPEG/PNG/WebP upload and durable local artifact storage;
- BiRefNet background removal;
- SDXL image-to-image with Canny ControlNet;
- original-product compositing;
- PostgreSQL queue with one serialized GPU worker;
- before/after comparison, downloads, and generation history; and
- Docker deployment for PostgreSQL, FastAPI, Next.js, and the CUDA worker.

There is no inpainting, additional ControlNet, prompt optimizer, synthetic contact
shadow, mask editor, cloud scaling, authentication, or billing.

## Running Demo

- Studio: `http://localhost:3001`
- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- PostgreSQL: host port `5432`
- Containers `db`, `api`, `frontend`, and `worker` are running.
- Alembic is current and API health/readiness both return 200.
- The worker is the only queue consumer. Do not start a native worker alongside it.
- Docker worker image: `photo-studio-worker:latest` (13.1 GB).
- Container CUDA check: Torch `2.8.0+cu128`, CUDA available, RTX 4060 Laptop GPU,
  Diffusers `0.35.2`, Accelerate `1.10.1`.
- Host model cache is bind-mounted at `/models` (117 files currently present).
- Host artifacts are bind-mounted at `/app/storage`.

Start or recover the demo with:

```bash
FRONTEND_PORT=3001 docker compose up -d db api frontend
docker compose run --rm api alembic upgrade head
docker compose --profile gpu up -d --no-deps worker
```

## Live ML Acceptance

Real BiRefNet and real SDXL/Canny inference have both completed on the local GPU.
The final acceptance job is `a9274d9f-40dc-46fc-969f-4c3e764eccc6`:

- status `succeeded`, progress `3/3`;
- 512 px, 25 steps, strength `0.9`, guidance `8.0`, ControlNet scale `0.3`;
- deterministic seeds 31415, 31416, and 31417;
- all three output rows and downloadable PNG artifacts are present;
- all three were visually reviewed for prompt adherence and product preservation.

The demo database was cleaned of experimental generation jobs and retains this one
successful history entry. Use **Restore job** in Workspace History for an immediate
interview demo without waiting for inference.

On this 8 GB GPU / constrained WSL host, a quality-default 512 px variation takes
about 5-6 minutes in the warm native environment, so allow roughly 15-20 minutes for
three. A cold Docker run may take longer. The UI persists and displays each variation
as soon as it finishes, and an interrupted generation resumes only missing seeds.

The production Docker worker was also validated with a temporary duplicate upload on
2026-09-12: real BiRefNet completed in 2.86 seconds, then the same worker completed
real SDXL/Canny generation `3/3` without restart or OOM. The cold first variation took
706.6 seconds; warm variations took 253.3 and 193.2 seconds. The duplicate database
rows and artifacts were removed after acceptance, leaving the demo history clean.

## Important ML Decisions

- BiRefNet is released after preprocessing so it cannot retain VRAM while SDXL loads.
- `SDXL_OFFLOAD_MODE=auto` selects disk-backed group offload below 12 GiB available
  host RAM. Supported modes are `auto`, `model`, `sequential`, and `disk`.
- Disk mode applies block-level Diffusers group offload to both text encoders, UNet,
  and ControlNet. The VAE stays on CUDA because encode/decode bypass top-level group
  hooks. Host allocations are trimmed between variations.
- The initial image for img2img is a product-free, preset-aware deterministic two-plane
  scene plate. It gives SDXL useful wall/surface context without anchoring it to the
  uploaded scene or product. It is not contact-shadow synthesis.
- Canny conditions only the product silhouette and alpha boundary, avoiding label and
  texture edges that previously made SDXL redraw the source. The untouched BiRefNet
  cutout is composited last, preserving product labels, geometry, and pixels.
- User scene text is paired with a static commercial-photography suffix through SDXL's
  second text encoder. Negative prompts avoid suppressing legitimate scene props.
- Each variation is stored immediately through a generation callback. A later OOM or
  process interruption therefore does not discard already completed outputs.
- PostgreSQL `FOR UPDATE SKIP LOCKED` plus guarded state transitions provides a
  durable queue without Redis/Celery. Deployment intentionally permits one GPU job.

## Defects Fixed During Completion

- Prevented WSL OOM kills caused by keeping the complete SDXL stack in host memory.
- Fixed VAE CPU/CUDA device mismatch in disk-offload mode.
- Fixed black/flat generated backgrounds caused by RGBA-to-RGB conversion.
- Added incremental output persistence and observable `1/3`, `2/3`, `3/3` progress.
- Added stale-generation requeue and successful-seed skipping, so interrupted jobs
  resume without regenerating outputs already persisted in PostgreSQL.
- Reworked the seed plate and Canny input for scene prompt adherence, curated seven
  distinct presets, and exposed/restored quality, strength, guidance, and structure.
- Added deterministic BiRefNet model release and CUDA cleanup.
- Corrected worker package imports, cache permissions, and image failure transitions.
- Pinned Next `16.3.4` and React `19.2.8`; committed the frontend lockfile and moved
  the frontend image to a warning-free multi-stage standalone build.
- Fixed desktop top alignment, mobile layout, overflow, and stable image dimensions.
- Fixed history refresh after completion and restored-source rendering in the upload UI.
- Fixed an uploaded-state placeholder that incorrectly said a cutout was being prepared
  before the user submitted background removal. It now shows `ACTION NEEDED` and names
  the required action; actual processing retains the progress message.
- Restored the roadmap's 512 px minimum upload dimension (the backend had drifted to
  64 px) and surfaced `512PX+` in the upload requirements. The API now rejects smaller
  images immediately with `INVALID_IMAGE_DIMENSIONS`.
- Added a dependency-free Chrome DevTools Protocol browser smoke test.
- Added Starlette's supported `httpx2` test dependency, removing its test warning.
- Rebased the worker image on `pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime` so the
  container uses the same verified CUDA stack without reinstalling Torch.

## Verification

Latest completed checks:

- Backend: `30 passed` with no warnings.
- Worker: `28 passed, 1 skipped` in the project test environment.
- Python `compileall`: passed for backend, worker, and shared code.
- `docker compose config`: passed with and without the `gpu` profile.
- Docker migration and `infra/scripts/smoke_test.sh`: passed against the live stack.
- Worker container: queue loop started, CUDA visible, model/artifact mounts present.
- Frontend: Next production build and TypeScript checks passed; npm production audit
  reports zero vulnerabilities.
- API output streaming and attachment download routes return valid PNG responses.
- Generation and prompt history filters return valid persisted data.
- Browser smoke passed at 1440 px desktop and 390 px mobile with no horizontal
  overflow, three decoded output images, three downloads, comparison UI, and success
  status. Final one-job captures are in `C:\Temp\studio-browser-quality-desktop.png`
  and `C:\Temp\studio-browser-quality-mobile.png`.

Run the core regression again with:

```bash
PYTHONPATH=backend:. .venv/bin/python -m pytest -q backend/app/tests
PYTHONPATH=worker:. .venv/bin/python -m pytest -q worker/app/tests
.venv/bin/python -m compileall -q backend/app worker/app shared/python
docker compose config >/dev/null
docker compose --profile gpu config >/dev/null
API_BASE_URL=http://localhost:8000 bash infra/scripts/smoke_test.sh
```

## Handoff Rules

1. Read this file before changing runtime or model settings.
2. Keep scope aligned with `implementation_roadmap.md`; do not reintroduce dropped
   product features.
3. Keep exactly one worker active. Check `docker compose ps -a` and host Python
   processes before launching another.
4. Preserve `.env`, `storage/`, and `model_cache/`; they are ignored runtime state.
5. Record every substantial change, test result, active process, and remaining issue
   here before ending a work session.
6. Prefer restoring the accepted history job for a fast demo. Run live generation
   only when there is enough time for the low-memory offload path.

## Remaining Risk

There are no known project-breaking defects. The principal constraint is performance:
disk-backed group offload is deliberately slow so the complete real model stack fits
an 8 GB GPU and limited WSL RAM. The one skipped worker test is environment-specific
OpenCV coverage; OpenCV/Canny has passed in the native ML environment and in live
generation. Diffusers `0.35.2` emits a harmless nested `torch_dtype` deprecation while
loading; direct compatibility testing showed that replacing it with `dtype` breaks or
is ignored by the pinned loaders, so retain the proven keyword until the ML stack is
upgraded and requalified as a unit.
