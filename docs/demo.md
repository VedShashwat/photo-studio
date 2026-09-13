# Demo and Interview Notes

## One-minute summary

AI Product Photography Studio is a single-user, single-GPU application that turns a
product photo into marketing scenes. It validates an upload, removes the background
with BiRefNet, generates three or four backgrounds with SDXL img2img plus Canny
ControlNet, composites the original product cutout over each scene, and durably stores
jobs and artifacts for comparison, download, and history restore.

## Architecture

```text
Next.js studio
    -> FastAPI API + PostgreSQL-backed queue
        -> one serialized CUDA worker
            -> BiRefNet
            -> scene seed plate + Canny
            -> SDXL img2img + Canny ControlNet
            -> original-cutout compositing
        -> bind-mounted artifact and model storage
```

The worker claims jobs using PostgreSQL `FOR UPDATE SKIP LOCKED`. Per-output rows are
written immediately, so completed variations survive a later failure. On restart,
stale generation work is requeued and successful deterministic seeds are skipped.
Request IDs, model settings, seeds, timing, and error classifications are persisted.

## Product preservation

1. BiRefNet creates the alpha mask and transparent product cutout.
2. A padded canvas gives the scene room around the product; a product-free preset
   plate lets the prompt establish an entirely new environment.
3. Canny preserves only the silhouette and alpha boundary during diffusion, without
   anchoring SDXL to label or texture edges.
4. The untouched product cutout is composited over every generated background last.

This preserves identity-critical labels and pixels while SDXL changes the environment.

## Demo flow

1. Open `http://localhost:3001`.
2. For an instant demonstration, select the successful job in Workspace History and
   choose **Restore job**.
3. Select each output, drag the before/after comparison, and download a PNG.
4. To show the full workflow, upload a 512-4096 px JPEG/PNG/WebP under 15 MB, remove
   its background, choose a scene, and generate three variations.

At the quality defaults, the low-memory path takes about 5-6 minutes per 512 px output
when warm on the current RTX 4060 laptop GPU; allow roughly 15-20 minutes for three and
longer when Docker is cold. Progress changes as each image is persisted; use history
restore for a short demo.

## Engineering tradeoffs

- PostgreSQL replaces Redis/Celery to keep this MVP durable and inspectable with one
  fewer distributed system.
- One worker avoids GPU contention and VRAM fragmentation.
- Canny is deterministic, CPU-friendly, and directly protects silhouette contours.
- Disk-backed group offload trades speed for reliable SDXL inference with constrained
  WSL memory and 8 GB VRAM.
- Local bind-mounted storage avoids cloud credentials and keeps artifacts inspectable.
- Scope intentionally excludes inpainting, extra ControlNets, prompt optimization,
  synthetic contact shadows, manual mask editing, cloud scaling, auth, and billing.

## Verified state

- Real BiRefNet and real SDXL/Canny inference: passed, including 3/3 outputs.
- Backend: 30 tests passed cleanly.
- Worker: 28 tests passed, 1 environment-specific skip.
- Compose config, migrations, API health/readiness, upload smoke, and CUDA worker: passed.
- Docker worker sees Torch 2.8.0+cu128 and the RTX 4060; real BiRefNet followed by
  real SDXL/Canny completed `3/3` in the production container without OOM or restart.
- Next production build, TypeScript checks, and production dependency audit: passed.
- Browser acceptance passed on desktop and mobile with decoded outputs, downloads,
  comparison UI, inference controls, history restore, expected status, and no
  horizontal overflow.

## Interview talking points

- Why preservation is a layered image-processing contract rather than a prompt trick.
- Why guarded transitions, immediate output writes, and seed-aware resume improve
  restart safety.
- How lazy loading, BiRefNet release, and disk group offload make real SDXL fit locally.
- Why this design optimizes for a polished single-machine MVP rather than SaaS scale.
