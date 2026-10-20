#!/bin/bash
# Rebuild the dashboard, commit and push. The live link updates in about a minute.
# Usage: ./publish.sh "what changed"
set -e
cd "$(dirname "$0")"
python3 sync.py
git add -A
if git diff --cached --quiet; then echo "Nothing to publish."; exit 0; fi
git commit -m "${1:-Update dashboard data}"
git push
echo "Pushed. https://0xfaizan19.github.io/ai-portfolio-trades/ updates in about a minute."
