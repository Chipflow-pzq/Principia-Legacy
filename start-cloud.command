#!/bin/sh
cd "$(dirname "$0")" || exit 1
exec "${PRINCIPIA_PYTHON:-python3}" start-cloud.py
