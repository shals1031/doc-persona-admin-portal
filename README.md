# Doc Persona - Admin Portal

A multi-tenant admin portal for managing doctor profiles, AI-enriched personas, and submission workflows. Built with FastAPI, PostgreSQL (with pgvector), Redis, and Celery.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Running the Application](#running-the-application)
- [Running with Docker](#running-with-docker)
- [API Documentation](#api-documentation)
- [End User Guide](#end-user-guide)
- [Background Workers](#background-workers)
- [Project Structure](#project-structure)
- [Debugging](#debugging)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
Client (Browser / API)
        |
   FastAPI App (port 8000)
   ├── API routes     (/api/dashboard, /api/submission, /api/internal)
   ├── Web routes     (/dashboard, /submission/{id})
   ├── Auth middleware (JWT bearer tokens)
   └── Tenant middleware (multi-tenant isolation)
        |
   ┌────┴────┐
PostgreSQL   Redis
(port 5433)  (port 6379)
             |
        Celery Workers
        ├── analytics-refresh queue
        └── ai-processing queue
```

**Key services:**
- **PostgreSQL** - Primary data store with pgvector extension for AI embeddings
- **Redis** - Caching layer, Celery message broker, and pub/sub events
- **Celery** - Background task processing (dashboard aggregation, embedding jobs)

---

## Prerequisites

- Python 3.11+
- PostgreSQL 13+ (with pgvector extension)
- Redis 6+
- Git

---

## Environment Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd admin_app
```

### 2. Create a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit the `.env` file and set the following variables with your actual values:

| Variable | Description | Default |
|---|---|---|
| `DATABASE_HOST` | PostgreSQL host | `localhost` |
| `DATABASE_PORT` | PostgreSQL port | `5433` |
| `DATABASE_USER` | Database username | *(set your own)* |
| `DATABASE_PASSWORD` | Database password | *(set your own)* |
| `DATABASE_NAME` | Database name | `doc_persona` |
| `DATABASE_SCHEMA` | PostgreSQL schema for AI tables | `ai` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `JWT_SECRET` | Secret key for JWT token signing | *(set a strong secret)* |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry duration | `30` |
| `ENVIRONMENT` | `development` or `production` | `development` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `RATE_LIMIT_PER_MINUTE` | API rate limit per client | `60` |

> **Important:** Never commit your `.env` file. It is excluded via `.gitignore`. The `.env.example` file contains placeholder values only.

### 5. Database setup

Ensure the database schema and tables are created. The SQL initialization scripts are maintained in the separate database scripts repository. Run them against your PostgreSQL instance before starting the application.

---

## Running the Application

### Start the FastAPI server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The `--reload` flag enables hot-reloading during development.

### Start Celery worker (separate terminal)

```bash
celery -A workers.celery_app worker --loglevel=info
```

### Start Celery Beat scheduler (separate terminal, optional)

Runs scheduled tasks such as dashboard aggregate refresh every 5 minutes.

```bash
celery -A workers.celery_app beat --loglevel=info
```

---

## Running with Docker

### Build the image

```bash
docker build -t doc-persona-admin:latest .
```

### Run the container

```bash
docker run -p 8000:8000 \
  -e DATABASE_HOST=<your-db-host> \
  -e DATABASE_PORT=<your-db-port> \
  -e DATABASE_USER=<your-db-user> \
  -e DATABASE_PASSWORD=<your-db-password> \
  -e DATABASE_NAME=doc_persona \
  -e REDIS_URL=redis://<your-redis-host>:6379/0 \
  -e JWT_SECRET=<your-jwt-secret> \
  -e ENVIRONMENT=production \
  doc-persona-admin:latest \
  uvicorn main:app --host 0.0.0.0 --port 8000
```

Ensure that PostgreSQL and Redis are accessible from the container network.

---

## API Documentation

Interactive API docs (Swagger UI) are available **only in development mode**:

```
http://localhost:8000/api/docs
```

### API Endpoints

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/api/dashboard/summary` | Dashboard summary counts | Required |
| `GET` | `/api/dashboard/list` | Paginated list with filters | Required |
| `GET` | `/api/dashboard/export` | Export filtered data as Excel | Required |
| `GET` | `/api/submission/{id}` | Submission detail with AI profile | Required |
| `POST` | `/api/internal/refresh-dashboard` | Trigger aggregate refresh | System Admin |

### Authentication

All API endpoints require a valid JWT bearer token in the `Authorization` header:

```
Authorization: Bearer <your-jwt-token>
```

**User roles:**
- **System Admin** - Full access, can select tenant context via cookie
- **Customer Admin** - Scoped to their assigned tenant

---

## End User Guide

### Dashboard

Navigate to `http://localhost:8000/dashboard` in your browser.

The dashboard provides:
- **Summary view** - Counts of submissions by status (draft, submitted, approved, rejected)
- **Filterable list** - Filter by geography, MR manager, form status, specialty, and tier
- **Sorting** - Click column headers to sort
- **Pagination** - Navigate through large datasets
- **Excel export** - Download filtered results as an `.xlsx` file

### Submission Detail

Click any submission in the dashboard list to view:
- Full doctor profile information
- AI-generated persona and enrichment data
- Submission metadata and status history

### Multi-Tenant Access

- **System Admins** select a tenant from the tenant switcher to view that tenant's data
- **Customer Admins** automatically see data scoped to their organization

---

## Background Workers

Celery handles two task queues:

| Queue | Task | Schedule |
|---|---|---|
| `analytics-refresh` | Refresh dashboard materialized views | Every 5 minutes (via Beat) |
| `ai-processing` | Process embedding generation jobs | On demand |

Both tasks include automatic retry logic (3 retries with exponential backoff).

---

## Project Structure

```
admin_app/
├── main.py                  # FastAPI application entry point
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container build configuration
├── .env.example             # Environment variable template
│
├── api/                     # REST API route handlers
│   ├── dashboard.py         #   Dashboard endpoints
│   ├── submission.py        #   Submission endpoints
│   └── internal.py          #   Internal admin endpoints
│
├── web/                     # Server-rendered HTML routes
│   └── dashboard.py         #   Jinja2 template routes
│
├── core/                    # Application core
│   ├── config.py            #   Settings and env var loading
│   ├── database.py          #   SQLAlchemy async engine setup
│   └── redis_client.py      #   Redis cache and pub/sub client
│
├── middleware/              # Request middleware
│   ├── auth.py              #   JWT authentication and authorization
│   └── tenant.py            #   Multi-tenant resolution
│
├── models/                  # SQLAlchemy ORM models
│   ├── doctor.py            #   Doctor profile and AI models
│   ├── dashboard.py         #   Dashboard fact table
│   └── control.py           #   Tenants, mappings, processing logs
│
├── repositories/            # Data access layer
│   ├── dashboard_repo.py    #   Dashboard queries
│   └── submission_repo.py   #   Submission queries
│
├── schemas/                 # Pydantic request/response models
│   ├── auth.py              #   Auth and role schemas
│   ├── dashboard.py         #   Dashboard schemas
│   └── submission.py        #   Submission schemas
│
├── services/                # Business logic
│   ├── dashboard_service.py #   Dashboard operations and caching
│   └── submission_service.py#   Submission retrieval
│
├── workers/                 # Celery background tasks
│   ├── celery_app.py        #   Celery configuration
│   └── tasks.py             #   Task definitions
│
└── templates/               # Jinja2 HTML templates
```

---

## Debugging

### Enable debug logging

Set in your `.env` file:

```
LOG_LEVEL=DEBUG
ENVIRONMENT=development
```

This enables:
- SQLAlchemy query logging (SQL echo)
- Swagger UI at `/api/docs`
- CORS open to all origins
- Structured debug logs via structlog

### Debugging with an IDE

**PyCharm:**
1. Create a new Run Configuration: `Python` > Module name: `uvicorn`
2. Parameters: `main:app --host 0.0.0.0 --port 8000 --reload`
3. Set working directory to the project root
4. Add `.env` file via the EnvFile plugin or set environment variables manually
5. Set breakpoints and run in Debug mode

**VS Code:**

Add to `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
      "envFile": "${workspaceFolder}/.env",
      "cwd": "${workspaceFolder}"
    }
  ]
}
```

### Debugging Celery workers

Run the worker with debug logging:

```bash
celery -A workers.celery_app worker --loglevel=debug
```

To test a task manually from a Python shell:

```python
from workers.tasks import refresh_dashboard_aggregates
refresh_dashboard_aggregates.delay()
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `Connection refused` on port 5433 | PostgreSQL not running | Start PostgreSQL and verify it listens on the configured port |
| `Connection refused` on port 6379 | Redis not running | Start Redis |
| `relation does not exist` | Database schema not initialized | Run the init SQL scripts from the database scripts repository |
| `401 Unauthorized` | Missing or expired JWT token | Obtain a fresh token and include it in the `Authorization` header |
| `403 Forbidden` | Insufficient role | Endpoint requires System Admin role |
| Swagger UI not loading | Running in production mode | Set `ENVIRONMENT=development` in `.env` |
| Celery tasks not executing | Worker not running or Redis unreachable | Start the Celery worker and verify Redis connectivity |
| Static files 404 | `static/` directory missing | Create a `static/` directory at project root (optional during early dev) |
