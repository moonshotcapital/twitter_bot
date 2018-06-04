#!/bin/sh

set -o errexit
set -o pipefail
set -o nounset


cd /app/ && celery -A bot worker -B -l info

