#!/bin/sh
set -e

echo "Starting worker loop..."

while true; do
  echo "[$(date)] Running ingest-cr-data"
  flask --app backend.wsgi:app ingest-cr-data

  echo "[$(date)] Running ingest-registration-data"
  flask --app backend.wsgi:app ingest-registration-data

  echo "[$(date)] Running trigger-rebuild"
  flask --app backend.wsgi:app trigger-rebuild

  echo "[$(date)] Sleeping for 15 minutes..."
  sleep 900
done