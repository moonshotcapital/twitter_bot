#!/bin/sh

set -o errexit
set -o pipefail
set -o nounset

mkdir -p /app/logs/
cd /app/ && celery -A bot worker -B -l info -f /app/logs/celery_beat

