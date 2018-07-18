#!/bin/sh

set -o errexit
set -o pipefail
set -o nounset

mkdir -p /app/logs/
cd /app/ && celery -A bot worker -B -l debug -f /app/logs/celery_beat

