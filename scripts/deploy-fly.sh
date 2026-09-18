#!/usr/bin/env bash
# Deploy MongolWrite to Fly.io.
# Requires: FLY_API_TOKEN in the environment (https://fly.io/dashboard/personal/tokens)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -z "${FLY_API_TOKEN:-}" ]]; then
  echo "FLY_API_TOKEN байхгүй. Fly dashboard → Access Tokens дээр үүсгээд:"
  echo "  export FLY_API_TOKEN=..."
  echo "дараа нь дахин ажиллуулна."
  exit 1
fi

export PATH="${HOME}/.fly/bin:${PATH}"
if ! command -v flyctl >/dev/null 2>&1 && ! command -v fly >/dev/null 2>&1; then
  curl -fsSL https://fly.io/install.sh | sh
  export PATH="${HOME}/.fly/bin:${PATH}"
fi

FLY=(flyctl)
command -v flyctl >/dev/null 2>&1 || FLY=(fly)

"${FLY[@]}" auth whoami
"${FLY[@]}" deploy -a mongolwrite-ai --ha=false --yes

if [[ -n "${ADMIN_PASSWORD:-}" ]]; then
  "${FLY[@]}" secrets set \
    ADMIN_USERNAME="${ADMIN_USERNAME:-admin}" \
    ADMIN_PASSWORD="$ADMIN_PASSWORD" \
    -a mongolwrite-ai
fi

echo "Deploy OK → https://mongolwrite-ai.fly.dev/admin"
