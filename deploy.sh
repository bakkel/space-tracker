#!/usr/bin/env bash
# Sync this project to the Pi over SSH and restart the service.
set -euo pipefail

REMOTE=flight2
REMOTE_DIR=/home/bakkel/space-tracker
SERVICE=space-tracker

cd "$(dirname "$0")"

rsync -avz --delete \
  --exclude='.git/' \
  --exclude='.DS_Store' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='nasa_cache/' \
  --exclude='CLAUDE.md' \
  ./ "$REMOTE:$REMOTE_DIR/"

ssh "$REMOTE" "sudo systemctl restart $SERVICE"
echo "Deployed to $REMOTE:$REMOTE_DIR, service $SERVICE restarted."
