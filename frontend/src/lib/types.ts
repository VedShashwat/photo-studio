export type ImageStatus = "uploaded" | "processing" | "ready" | "failed";

export type ImageUploadResponse = {
  image_id: string;
  status: ImageStatus;
  original_url: string;
  width: number;
  height: number;
  mime_type: string;
};

export type ImageMetadataResponse = {
  image_id: string;
  status: ImageStatus;
  original_url: string;
  mask_url: string | null;
  cutout_url: string | null;
  width: number;
  height: number;
  mime_type: string;
  metadata: Record<string, unknown>;
};

export type JobResponse = {
  job_id: string;
  image_id: string;
  job_type: string;
  status: "pending" | "running" | "succeeded" | "partially_succeeded" | "failed" | "cancelled";
};

export type GenerationSettings = {
  steps: number;
  guidance_scale: number;
  strength: number;
  controlnet_conditioning_scale: number;
  canvas_size: number;
};

export type GenerationJobRequest = {
  image_id: string;
  scene_preset: string;
  prompt?: string;
  negative_prompt?: string;
  variation_count: 3 | 4;
  seed?: number;
  settings?: Partial<GenerationSettings>;
};

export type GenerationJobCreateResponse = {
  job_id: string;
  status: "pending";
};

export type GenerationOutput = {
  output_id: string;
  status: "pending" | "running" | "succeeded" | "failed";
  url: string;
  download_url: string;
  seed: number | null;
};

export type GenerationJobStatusResponse = {
  job_id: string;
  image_id: string;
  status: "pending" | "running" | "succeeded" | "partially_succeeded" | "failed" | "cancelled";
  progress: {
    completed_outputs: number;
    total_outputs: number;
  };
  outputs: GenerationOutput[];
  error_message: string | null;
};

export type GenerationHistoryOutput = {
  output_id: string;
  status: GenerationOutput["status"];
  thumbnail_url: string | null;
  url: string | null;
  download_url: string | null;
  seed: number | null;
};

export type GenerationHistoryItem = {
  job_id: string;
  image_id: string;
  status: GenerationJobStatusResponse["status"];
  scene_preset: string | null;
  prompt: string | null;
  negative_prompt: string | null;
  variation_count: number | null;
  base_seed: number | null;
  settings: Record<string, unknown>;
  created_at: string | null;
  original_url: string;
  width: number | null;
  height: number | null;
  mime_type: string | null;
  cutout_url: string | null;
  outputs: GenerationHistoryOutput[];
  error_message: string | null;
};

export type GenerationHistoryResponse = {
  items: GenerationHistoryItem[];
  page: number;
  limit: number;
  total: number;
  has_next: boolean;
};

export type ApiError = {
  error?: {
    code?: string;
    message?: string;
    details?: Record<string, unknown>;
  };
};
