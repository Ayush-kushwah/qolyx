# Qolyx Known Issues and Troubleshooting Guide

This document maintains a running register of known technical, environmental, and operational issues encountered during development and integration along with their verified workarounds.

---

### ERR-001: Alembic migration import errors inside Docker containers

- **Subsystem:** backend/database/migrations
- **Symptoms:** Running `make migrate` or starting backend containers fails with `ModuleNotFoundError: No module named 'backend'`
- **Root Cause:** When the backend folder is copied directly as the root of `/app` in python-slim base images, the absolute package namespace for `backend` gets lost.
- **Fix:** Mount the backend directory structure under `/app/backend` inside the Docker image and explicitly configure the `PYTHONPATH` environment variable as `/app` (`ENV PYTHONPATH=/app`).

---

### ERR-002: Docker health check fails on python:3.11-slim (no curl)

- **Subsystem:** infra/compose.yaml
- **Symptoms:** Backend container health check fails with "curl not found" error
- **Root Cause:** python:3.11-slim doesn't include curl
- **Fix:** Use Python urllib instead:
  ```yaml
  healthcheck:
    test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"]
  ```
