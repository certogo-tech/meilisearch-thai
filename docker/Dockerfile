# Multi-stage Dockerfile for Thai tokenizer service
# Placeholder for task 7.1

FROM python:3.12-slim as base

# Build stage
FROM base as builder
WORKDIR /app
# Dependencies will be added in task 7.1

# Production stage  
FROM base as production
WORKDIR /app
# Production setup will be completed in task 7.1

EXPOSE 8000
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]