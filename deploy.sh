#!/usr/bin/env bash
# Sync dit project naar de Pi via SSH en herstart de service.
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
  ./ "$REMOTE:$REMOTE_DIR/"

ssh "$REMOTE" "sudo systemctl restart $SERVICE"
echo "Gedeployed naar $REMOTE:$REMOTE_DIR, service $SERVICE herstart."
