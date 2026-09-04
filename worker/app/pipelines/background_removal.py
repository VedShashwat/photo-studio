from __future__ import annotations

import gc
from io import BytesIO
from typing import TYPE_CHECKING

from PIL import Image

from shared.python.storage_paths import artifact_path
from app.pipelines.postprocessing import MaskMetrics, MaskQualityError, refine_mask

if TYPE_CHECKING:
    from worker.app.services.db_client import ClaimedJob, WorkerDatabase
    from worker.app.services.storage_client import WorkerStorage


def create_cutout(image: Image.Image, mask: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    rgba.putalpha(mask.convert("L"))
    return rgba


class BiRefNetAdapter:
    def __init__(
        self,
        model_name: str,
        device: str = "cuda",
        torch_dtype: str = "float16",
        cache_dir: str | None = None,
    ):
        self.model_name = model_name
        self.device = device
        self.torch_dtype = torch_dtype
        self.cache_dir = cache_dir
        self._processor = None
        self._model = None

    def _load(self) -> None:
        if self._model is not None:
            return
        import torch
        from torchvision import transforms
        from transformers import AutoModelForImageSegmentation

        load_kwargs: dict[str, object] = {"trust_remote_code": True}
        if self.cache_dir:
            load_kwargs["cache_dir"] = self.cache_dir
        model_kwargs = dict(load_kwargs)
        use_half = self.device.startswith("cuda") and self.torch_dtype == "float16"
        if use_half:
            model_kwargs["dtype"] = torch.float16
        elif self.device.startswith("cuda") and self.torch_dtype == "bfloat16":
            model_kwargs["dtype"] = torch.bfloat16
        self._model = AutoModelForImageSegmentation.from_pretrained(self.model_name, **model_kwargs)
        self._model.to(self.device).eval()
        if use_half:
            self._model.half()
        self._processor = transforms.Compose(
            [
                transforms.Resize((1024, 1024)),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            ]
        )
        self._torch = torch

    def predict_mask(self, image: Image.Image) -> Image.Image:
        self._load()
        source = image.convert("RGB")
        try:
            processed = self._processor(source)
        except TypeError:
            processed = self._processor(images=source, return_tensors="pt")
        if isinstance(processed, dict):
            inputs = {name: value.to(self.device) for name, value in processed.items()}
            if self.device.startswith("cuda") and self.torch_dtype == "float16":
                inputs = {name: value.half() for name, value in inputs.items()}
            model_args: tuple = ()
            model_kwargs = inputs
        else:
            image_input = processed.unsqueeze(0).to(self.device)
            if self.device.startswith("cuda") and self.torch_dtype == "float16":
                image_input = image_input.half()
            model_args = (image_input,)
            model_kwargs = {}
        with self._torch.inference_mode():
            output = self._model(*model_args, **model_kwargs)
        logits = output.logits if hasattr(output, "logits") else output[-1]
        probability = self._torch.sigmoid(logits).squeeze().float().clamp(0, 1)
        values = probability.mul(255).byte().detach().cpu().tolist()
        if not values or not values[0]:
            raise ValueError("BiRefNet returned an empty mask")
        mask = Image.new("L", (len(values[0]), len(values)))
        mask.putdata([pixel for row in values for pixel in row])
        return mask.resize(image.size, Image.Resampling.BILINEAR)

    def release(self) -> None:
        """Release BiRefNet weights so SDXL can use the single worker GPU safely."""
        if self._model is None:
            return
        self._model = None
        self._processor = None
        gc.collect()
        torch = getattr(self, "_torch", None)
        if torch is not None and torch.cuda.is_available():
            torch.cuda.empty_cache()


class BackgroundRemovalProcessor:
    def __init__(self, database: WorkerDatabase, storage: WorkerStorage, model: BiRefNetAdapter):
        self.database = database
        self.storage = storage
        self.model = model

    def process(self, job: ClaimedJob) -> None:
        try:
            image_record = self.database.get_image(job.image_id)
            if image_record is None:
                raise ValueError(f"Image {job.image_id} was not found")
            image = Image.open(BytesIO(self.storage.read_bytes(image_record["original_path"]))).convert("RGBA")
            raw_mask = self.model.predict_mask(image)
            refined_mask, metrics = refine_mask(raw_mask)
            cutout = create_cutout(image, refined_mask)
            mask_path = artifact_path("masks", job.image_id, "png")
            cutout_path = artifact_path("cutouts", job.image_id, "png")
            mask_buffer = BytesIO()
            cutout_buffer = BytesIO()
            refined_mask.save(mask_buffer, format="PNG")
            cutout.save(cutout_buffer, format="PNG")
            self.storage.write_bytes(mask_path, mask_buffer.getvalue())
            self.storage.write_bytes(cutout_path, cutout_buffer.getvalue())
            self.database.complete_background_removal(
                job.id,
                job.image_id,
                mask_path,
                cutout_path,
                {"foreground_coverage": metrics.coverage, "foreground_bbox": list(metrics.bbox or ())},
            )
        finally:
            release = getattr(self.model, "release", None)
            if callable(release):
                release()
