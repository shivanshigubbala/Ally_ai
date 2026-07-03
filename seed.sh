#!/bin/bash
# Seed database using Docker network
# This script runs the seed script inside a container on the Docker network

docker run --rm \
  --network ally_ai_default \
  -e DATABASE_URL="postgresql+psycopg2://allyai:allyai@ally_ai-postgres-1:5432/allyai" \
  -v "$(pwd)/scripts:/scripts" \
  python:3.13 \
  bash -c "pip install -q sqlalchemy psycopg2-binary && python /scripts/seed.py"
