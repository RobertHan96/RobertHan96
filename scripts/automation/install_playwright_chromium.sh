#!/usr/bin/env bash
set -euo pipefail

# GitHub-hosted runners occasionally keep a stale azure-cli apt source that
# breaks `playwright install --with-deps` during apt update. Remove only that
# source; keep the broader Microsoft prod repo because other packages may use it.
if [[ "${RUNNER_OS:-}" == "Linux" ]] && command -v sudo >/dev/null 2>&1; then
  while IFS= read -r source_file; do
    echo "Removing stale azure-cli apt source: ${source_file}"
    sudo rm -f "${source_file}"
  done < <(
    grep -Rsl "packages.microsoft.com/repos/azure-cli" /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null || true
  )
fi

if python -m playwright install --with-deps chromium; then
  exit 0
fi

echo "::warning::Playwright dependency install failed; retrying browser-only install."
python -m playwright install chromium
