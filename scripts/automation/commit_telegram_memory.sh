#!/usr/bin/env bash
set -euo pipefail

PATHS="${1:-data/telegram_memory}"
MESSAGE="${2:-Update telegram memory}"

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

git add ${PATHS}

if git diff --cached --quiet; then
  exit 0
fi

git commit -m "${MESSAGE}"
git push
