# AI Product Photography Studio

An intentionally single-user, single-GPU MVP for turning product photos into marketing imagery. The planned pipeline is:

1. Validate and store an uploaded image.
2. Remove its background with BiRefNet.
3. Generate a scene with SDXL image-to-image and Canny ControlNet.
4. Composite the original product cutout over the generated scene.
5. Store outputs and job history in PostgreSQL.

## Current status

The rescoped roadmap is complete. Real BiRefNet and SDXL/Canny inference, prompt-responsive scene generation, exact product compositing, Docker GPU execution, restart-safe jobs, history restore, downloads, and responsive browser flows have all been validated. See [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md) for exact acceptance evidence and the recovery handoff.

## Demo output

![Generated luxury studio product scene](docs/assets/demo-output.png)

The original product pixels are composited over a prompt-generated SDXL scene after
BiRefNet isolation and silhouette-only Canny conditioning.

## Prerequisites

- Python 3.12+ for API development (the worker supports Python 3.10+)
- Docker Compose
- Node.js 20+ for the frontend
- NVIDIA Container Toolkit and a CUDA-capable GPU for ML worker work

## Start the foundation

```bash
cp .env.example .env
docker compose up --build db api
```

The API exposes `GET /api/health`, `GET /api/ready`, and `/docs` on port 8000.

Run the database migration explicitly during early development:

```bash
docker compose run --rm api alembic upgrade head
```

The frontend and serialized GPU worker are fully wired in Compose; the worker is enabled with the `gpu` profile and receives the only GPU reservation. Storage and model cache are bind-mounted from `./storage` and `./model_cache` so native worker experiments and Docker services share the same artifacts.

## Local backend checks

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
PYTHONPATH=.. .venv/bin/pytest
```

## Demo guide

### Configure the environment

Create a local, non-secret environment file from the checked-in template:

```bash
cp .env.example .env
```

The template contains the API, database, storage, frontend, worker device, model identifiers, cache, queue, upload, and logging settings. Change `DATABASE_URL`, `STORAGE_ROOT`, and model/cache paths only when running outside the supplied Compose topology. Never commit `.env` or model credentials.

### Run the API foundation

Start PostgreSQL and the API, then apply migrations explicitly:

```bash
docker compose up --build -d db api
docker compose run --rm api alembic upgrade head
curl http://localhost:8000/api/health
curl http://localhost:8000/api/ready
```

Start the frontend after the API is healthy:

```bash
docker compose up --build -d frontend
```

Open <http://localhost:3000>. The optional reverse proxy is available with:

```bash
docker compose --profile proxy up --build -d reverse-proxy
```

Then open <http://localhost:8080>.

If port 3000 is already in use, start the same frontend container on another host port:

```bash
FRONTEND_PORT=3001 docker compose up -d frontend
```

Then open <http://localhost:3001>.

### Run the GPU worker

The worker is intentionally the only GPU-enabled service and is serialized to one job. NVIDIA Container Toolkit and a compatible host driver are required:

```bash
docker compose --profile gpu up --build -d worker
```

The worker uses the persistent `model_cache` bind mount. On the first real preprocessing/generation job, it lazily downloads the configured BiRefNet, SDXL base, and SDXL Canny ControlNet weights. Downloads and the first disk-offload cache can consume several gigabytes.

`SDXL_OFFLOAD_MODE=auto` selects disk-backed group offload when available host memory is below 12 GiB. This is the reliable default for the tested 8 GB GPU/limited-WSL host. At the quality defaults, one 512 px variation takes about 5-6 minutes in the warm native environment; allow roughly 15-20 minutes for three and longer for a cold Docker run. Completed seeds persist immediately and an interrupted generation resumes only missing variations. Explicit modes are `model`, `sequential`, and `disk`.

### Run the smoke test

With `db`, `api`, and the GPU worker running, execute:

```bash
API_BASE_URL=http://localhost:8000 bash infra/scripts/smoke_test.sh
```

The script checks API liveness and readiness, runs `alembic upgrade head`, generates a valid 512x512 PNG when `SMOKE_IMAGE` is not supplied, exercises `POST /api/images`, and verifies that the worker container is running. To use a specific fixture:

```bash
SMOKE_IMAGE=/path/to/product.png bash infra/scripts/smoke_test.sh
```

### End-to-end demo workflow

1. Open the studio and choose a JPEG, PNG, or WebP product image at least 512x512 and no larger than 15 MB.
2. Upload the image and start background removal.
3. Wait for the cutout preview to reach `ready`.
4. Choose a scene preset or edit the positive/negative prompts and bounded inference controls.
5. Select 3 or 4 variations and start generation. Each completed variation appears immediately.
6. Review the generation grid, select a successful output, and download it.
7. Drag the before/after comparison slider to inspect the original/cutout against the generated scene.
8. Use Workspace History to restore an earlier job, prompt, and output set.

### Native ML development environment

For experiments outside Docker, use the documented native environment at `/home/user/miniconda3/envs/venv`. It already contains the verified Torch/CUDA, TorchVision, Transformers, Pillow, OpenCV, NumPy, Diffusers, Accelerate, Hugging Face Hub, and Safetensors versions listed in [DEVELOPMENT_ENVIRONMENTS.md](DEVELOPMENT_ENVIRONMENTS.md). Do not reinstall or replace Torch/CUDA packages. Use the project `.venv` for API tests and the native environment only for ML smoke tests or inference.

Example native worker import check:

```bash
MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- env PYTHONPATH=worker:. /home/user/miniconda3/envs/venv/bin/python -c 'from app.models.model_registry import ModelRegistry; print(ModelRegistry("ZhengPeng7/BiRefNet").runtime_settings)'
```

### Validation notes

The authoritative non-GPU checks are:

```bash
wsl.exe -d Ubuntu -- env PYTHONPATH=backend:. .venv/bin/python -m pytest -q backend/app/tests
wsl.exe -d Ubuntu -- env PYTHONPATH=worker:. .venv/bin/python -m pytest -q worker/app/tests
wsl.exe -d Ubuntu -- .venv/bin/python -m compileall -q backend/app worker/app shared/python
```

The current stack has passed these checks: backend `30 passed`; worker `28 passed, 1 skipped`; compileall; normal/GPU Compose config; migrations; Docker smoke test; CUDA visibility and real BiRefNet plus SDXL/Canny inference; Next production build and TypeScript; production npm audit; and desktop/mobile browser acceptance. Model weights remain runtime cache data and are not committed to the repository.
