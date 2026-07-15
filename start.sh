#!/bin/bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &

echo "Waiting for backend to come up..."
for i in $(seq 1 60); do
  if (echo > /dev/tcp/localhost/8000) 2>/dev/null; then
    echo "Backend is up."
    break
  fi
  sleep 1
done

streamlit run frontend/app.py \
  --server.port ${PORT:-10000} \
  --server.address 0.0.0.0 \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false
