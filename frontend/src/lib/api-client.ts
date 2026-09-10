import type {
  ApiError,
  GenerationJobCreateResponse,
  GenerationJobRequest,
  GenerationHistoryResponse,
  GenerationJobStatusResponse,
  ImageMetadataResponse,
  ImageUploadResponse,
  JobResponse,
} from "./types";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function apiUrl(path: string): string {
  if (/^https?:\/\//.test(path)) return path;
  return `${apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`;
}

export class ApiClientError extends Error {
  code: string;
  status: number;

  constructor(message: string, status: number, code = "API_ERROR") {
    super(message);
    this.name = "ApiClientError";
    this.code = code;
    this.status = status;
  }
}

async function parseError(response: Response): Promise<ApiClientError> {
  let payload: ApiError = {};
  try {
    payload = (await response.json()) as ApiError;
  } catch {
    // Keep a useful fallback when a proxy or server returns non-JSON text.
  }
  return new ApiClientError(
    payload.error?.message ?? `Request failed with status ${response.status}.`,
    response.status,
    payload.error?.code,
  );
}

export async function uploadImage(file: File, signal?: AbortSignal): Promise<ImageUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(apiUrl("/api/images"), {
    method: "POST",
    body: formData,
    signal,
  });
  if (!response.ok) throw await parseError(response);
  return (await response.json()) as ImageUploadResponse;
}

export async function requestBackgroundRemoval(imageId: string, force = false): Promise<JobResponse> {
  const response = await fetch(apiUrl(`/api/images/${imageId}/remove-background`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ force }),
  });
  if (!response.ok) throw await parseError(response);
  return (await response.json()) as JobResponse;
}

export async function getImage(imageId: string, signal?: AbortSignal): Promise<ImageMetadataResponse> {
  const response = await fetch(apiUrl(`/api/images/${imageId}`), { signal });
  if (!response.ok) throw await parseError(response);
  return (await response.json()) as ImageMetadataResponse;
}

export async function createGenerationJob(request: GenerationJobRequest): Promise<GenerationJobCreateResponse> {
  const response = await fetch(apiUrl("/api/generation-jobs"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw await parseError(response);
  return (await response.json()) as GenerationJobCreateResponse;
}

export async function getGenerationJob(jobId: string, signal?: AbortSignal): Promise<GenerationJobStatusResponse> {
  const response = await fetch(apiUrl(`/api/generation-jobs/${jobId}`), { signal });
  if (!response.ok) throw await parseError(response);
  return (await response.json()) as GenerationJobStatusResponse;
}

export async function getGenerationHistory(signal?: AbortSignal): Promise<GenerationHistoryResponse> {
  const response = await fetch(apiUrl("/api/generation-jobs?limit=20"), { signal });
  if (!response.ok) throw await parseError(response);
  return (await response.json()) as GenerationHistoryResponse;
}
