# Development Environment Inventory

Checked: 2026-09-12

## Recommended local environments

### API and database work

Use the project-local `/home/user/photo-studio/.venv`.

It contains the pinned API development stack from `backend/pyproject.toml`, including FastAPI, SQLAlchemy, Alembic, psycopg, Pillow, httpx, and pytest.

Typical command:

```bash
PYTHONPATH=backend:. .venv/bin/pytest -q backend/app/tests
```

### ML worker work

Use `/home/user/miniconda3/envs/venv` for native worker experiments until the worker container is ready.

Verified packages:

- PyTorch `2.8.0+cu128`, CUDA available, one GPU visible.
- TorchVision `0.23.0+cu128`.
- Transformers `4.57.0`.
- Pillow `11.3.0`.
- OpenCV `4.12.0`.
- NumPy `2.2.6`.
- Hugging Face Hub `0.35.3`.
- Safetensors `0.6.2`.
- Diffusers `0.35.2`.
- Accelerate `1.10.1`.

The environment was revalidated during the final live-inference pass. PyTorch reports CUDA available, and real BiRefNet plus SDXL/Canny inference completed successfully. The model cache contains the downloaded weights and disk-group-offload files. Diffusers and Accelerate were added without changing the existing Torch/CUDA packages.

The Docker worker uses `pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime` and pins the matching Diffusers, Accelerate, NumPy, OpenCV, Safetensors, TorchVision, and Transformers versions. The built container sees the RTX 4060, shares the host model cache, and runs the PostgreSQL queue loop independently of the host Conda environment. BiRefNet uses the Transformers image-segmentation stack.

Do not reinstall PyTorch or CUDA packages into this environment. Keep it as a recovery and focused ML-development environment; the Docker worker is the authoritative demo worker.

## Other environments

- `/home/user/miniconda3/envs/myenv`: no relevant project packages detected.
- `/home/user/miniconda3/envs/webp`: no relevant project packages detected.
- `/home/user/pyspark_env`: Pillow and NumPy are present, but no Torch runtime.
- `/home/user/BDA_Project/hadoop-project/venv`: no relevant project packages detected.

## Resume rule

Record any package additions and their versions in this file and in `PROJECT_PROGRESS.md`. Keep the API test and native ML environments separate, and never run the native worker concurrently with the Docker worker.
