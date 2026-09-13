#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
COMPOSE_COMMAND="${COMPOSE_COMMAND:-docker compose}"
SMOKE_IMAGE="${SMOKE_IMAGE:-}"
TEMP_IMAGE=""
GENERATOR_IMAGE=""
WSL_IMAGE_MODE=0
CURL_COMMAND=(curl)

cleanup() {
  if [[ -z "${TEMP_IMAGE}" ]]; then
    return
  fi
  if [[ "${WSL_IMAGE_MODE}" -eq 1 ]]; then
    wsl.exe -d Ubuntu -- rm -f "${TEMP_IMAGE}" >/dev/null 2>&1 || true
  elif [[ -f "${TEMP_IMAGE}" ]]; then
    rm -f "${TEMP_IMAGE}"
  fi
}
trap cleanup EXIT

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

require_command curl
PYTHON_COMMAND=(python3)
if ! python3 -c "import sys" >/dev/null 2>&1; then
  require_command wsl.exe
  export MSYS_NO_PATHCONV=1
  PYTHON_COMMAND=(wsl.exe -d Ubuntu -- python3)
  CURL_COMMAND=(wsl.exe -d Ubuntu -- curl)
  WSL_IMAGE_MODE=1
fi

check_json_field() {
  local payload="$1"
  local field="$2"
  "${PYTHON_COMMAND[@]}" - "$payload" "$field" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
field = sys.argv[2]
value = payload.get(field)
if not value:
    raise SystemExit(f"Response field '{field}' is missing or empty")
print(value)
PY
}

echo "Checking API liveness..."
health_payload="$("${CURL_COMMAND[@]}" --fail --silent --show-error "${API_BASE_URL}/api/health")"
[[ "$(check_json_field "$health_payload" status)" == "ok" ]] || {
  echo "API liveness check returned a non-ok status" >&2
  exit 1
}

echo "Checking API readiness..."
ready_payload="$("${CURL_COMMAND[@]}" --fail --silent --show-error "${API_BASE_URL}/api/ready")"
[[ "$(check_json_field "$ready_payload" status)" == "ready" ]] || {
  echo "API readiness check returned a non-ready status" >&2
  exit 1
}

echo "Applying database migrations..."
${COMPOSE_COMMAND} run --rm api alembic upgrade head

if [[ -z "${SMOKE_IMAGE}" ]]; then
  if [[ "${WSL_IMAGE_MODE}" -eq 1 ]]; then
    GENERATOR_IMAGE="/home/user/photo-studio/storage/.smoke-image.png"
    SMOKE_IMAGE="${GENERATOR_IMAGE}"
    TEMP_IMAGE="${SMOKE_IMAGE}"
    wsl.exe -d Ubuntu -- mkdir -p /home/user/photo-studio/storage
  else
    TEMP_IMAGE="$(mktemp --suffix=.png)"
    GENERATOR_IMAGE="${TEMP_IMAGE}"
    SMOKE_IMAGE="${TEMP_IMAGE}"
  fi
  "${PYTHON_COMMAND[@]}" - "${GENERATOR_IMAGE}" <<'PY'
import struct
import sys
import zlib

path = sys.argv[1]
width = height = 512
row = bytes([255, 240, 230]) * width
raw = b"".join(b"\x00" + row for _ in range(height))

def chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

png = b"\x89PNG\r\n\x1a\n"
png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
png += chunk(b"IDAT", zlib.compress(raw, 9))
png += chunk(b"IEND", b"")
with open(path, "wb") as handle:
    handle.write(png)
PY
fi

if [[ "${WSL_IMAGE_MODE}" -eq 1 ]]; then
  wsl.exe -d Ubuntu -- test -f "${SMOKE_IMAGE}"
else
  test -f "${SMOKE_IMAGE}"
fi || {
  echo "Smoke image does not exist: ${SMOKE_IMAGE}" >&2
  exit 1
}

echo "Checking image upload..."
upload_payload="$("${CURL_COMMAND[@]}" --fail --silent --show-error -F "file=@${SMOKE_IMAGE}" "${API_BASE_URL}/api/images")"
image_id="$(check_json_field "$upload_payload" image_id)"
echo "Uploaded smoke image ${image_id}"

echo "Checking worker container..."
if ${COMPOSE_COMMAND} ps --status running worker | grep -q "worker"; then
  echo "Docker worker is running."
elif [[ "${WSL_IMAGE_MODE}" -eq 1 ]] && wsl.exe -d Ubuntu -- pgrep -f '[p]ython.*-m app.main' >/dev/null; then
  echo "Native WSL worker is running."
elif [[ "${WSL_IMAGE_MODE}" -eq 0 ]] && pgrep -f '[p]ython.*-m app.main' >/dev/null; then
  echo "Native worker is running."
else
  echo "No worker is running; start the Docker GPU worker or the documented native CUDA worker." >&2
  exit 1
fi

echo "Smoke test passed."
