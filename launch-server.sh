#!/bin/bash
cd "$(dirname "$0")"
.venv-server/bin/python3 run_server.py \
  --port 8181 \
  --config "$(dirname "$0")/config.server.yaml" \
  --ssl-cert ~/giselo.crt \
  --ssl-key ~/giselo.key
