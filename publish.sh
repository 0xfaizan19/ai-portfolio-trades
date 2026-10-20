#!/bin/bash
# Rebuilds index.html from the dashboard, commits everything and pushes to GitHub.
# Usage: ./publish.sh "what changed"
set -e
cd "$(dirname "$0")"
cp dashboard/standalone.html index.html
git add -A
if git diff --cached --quiet; then echo "Nothing to publish."; exit 0; fi
git commit -m "${1:-Update dashboard data}"
git push
echo "Pushed. The live dashboard updates in about a minute."
