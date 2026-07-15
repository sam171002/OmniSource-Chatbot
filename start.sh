#!/bin/bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
streamlit run frontend/app.py \
  --server.port ${PORT:-10000} \
  --server.address 0.0.0.0 \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false
