#!/usr/bin/env bash
set -euo pipefail

python -m src.cli etl
python -m src.cli schema
python -m src.cli import
