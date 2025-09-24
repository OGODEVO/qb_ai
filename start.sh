#!/bin/bash
python -m reki.grpc.server &
uvicorn reki.api:app --host 0.0.0.0 --port 8000