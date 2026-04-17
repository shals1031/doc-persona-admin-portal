# GCP Deployment Guide: Admin App

This guide provides a comprehensive walkthrough for deploying this application to an existing Google Cloud Platform (GCP) project.

---

## 1. Architecture Overview

To achieve a production-grade, scalable, and manageable deployment on GCP, we recommend the following managed services:

| Component        | GCP Service                   | Description                                                                 |
|------------------|-------------------------------|-----------------------------------------------------------------------------|
| **API/Web**      | Cloud Run (Service)           | Managed serverless compute for the FastAPI application.                    |
| **Worker**       | Cloud Run (Service)           | Managed compute for the Celery worker (with Always-on CPU).                 |
| **Beat**         | Cloud Run (Service)           | Managed compute for Celery Beat (with Always-on CPU).                       |
| **Database**     | Cloud SQL for PostgreSQL      | Fully managed PostgreSQL instance (supports `pgvector`).                   |
| **Cache/Queue**  | Cloud Memorystore for Redis   | Fully managed Redis instance for Celery and application caching.            |
| **Secrets**      | Secret Manager                | Secure storage for environment variables and sensitive keys.                |
| **Networking**   | Direct VPC Egress             | Connects Cloud Run to private Cloud SQL and Redis instances.                |
| **Registry**     | Container Registry (GCR)      | Docker image storage and management.                                        |
| **CI/CD**        | Cloud Build                   | Automated build and deployment pipelines.                                   |

---

## 2. Prerequisites

1.  **GCP Project**: An existing project with billing enabled.
2.  **gcloud CLI**: Installed and authenticated locally (`gcloud auth login`).
3.  **Required APIs**: Enable the following APIs:
    ```bash
    gcloud services enable \
        run.googleapis.com \
        sqladmin.googleapis.com \
        redis.googleapis.com \
        secretmanager.googleapis.com \
        cloudbuild.googleapis.com
    ```

---

## 3. Infrastructure Setup

### 3.1 Network Configuration (VPC & Subnet)
Cloud Run uses **Direct VPC Egress** to talk to Cloud SQL and Redis via their private IPs. This removes the need for a separate VPC Access Connector.

1.  Create a VPC (if not already present).
2.  Create a Subnet (if not already present) in the same region as your Cloud Run service.
3.  Ensure the subnet has at least 4 available IP addresses.

### 3.2 Database (Cloud SQL)
This application uses `pgvector`, which is supported in Cloud SQL for PostgreSQL (version 15+ recommended).

1.  Create a Cloud SQL instance:
    ```bash
    gcloud sql instances create admin-db \
        --database-version=POSTGRES_15 \
        --tier=db-custom-2-7680 \
        --region=[REGION] \
        --no-assign-ip \
        --network=[VPC_NAME]
    ```
2.  Create the database and user:
    ```bash
    gcloud sql databases create doc_persona --instance=admin-db
    gcloud sql users create admin_user_doc --instance=admin-db --password=[PASSWORD]
    ```
3.  **Note**: Ensure you enable the `vector` extension in your database:
    ```sql
    CREATE EXTENSION IF NOT EXISTS vector;
    ```

### 3.3 Redis (Cloud Memorystore)
1.  Create a Redis instance:
    ```bash
    gcloud redis instances create admin-cache \
        --size=1 \
        --region=[REGION] \
        --network=[VPC_NAME] \
        --connect-mode=private-service-access
    ```

### 3.4 Secrets (Secret Manager)
Store your sensitive environment variables in Secret Manager:
- `DATABASE_PASSWORD`
- `JWT_SECRET`
- `REDIS_URL`

---

## 4. Database Migrations
Before deploying the application, run database migrations. You can use **Cloud Run Jobs** for this.

1.  Create a Cloud Run Job for migrations:
    ```bash
    # Capture instance connection name
    INSTANCE_CONNECTION_NAME=$(gcloud sql instances describe admin-db --format="value(connectionName)")

    gcloud run jobs create migration-job \
        --image=gcr.io/[PROJECT_ID]/admin-app:latest \
        --region=[REGION] \
        --network=[VPC_NAME] \
        --subnet=[SUBNET_NAME] \
        --add-cloudsql-instances=$INSTANCE_CONNECTION_NAME \
        --set-env-vars="ENVIRONMENT=production" \
        --set-secrets="DATABASE_PASSWORD=DB_PASS:latest" \
        --command="alembic,upgrade,head"
    ```
2.  Execute the job:
    ```bash
    gcloud run jobs execute migration-job --region=[REGION]
    ```

---

## 5. Containerization & Registry

### 5.1 Registry (GCR)
Google Container Registry (`gcr.io`) is enabled by default. It is the legacy alternative to Artifact Registry but remains simple to use.

### 5.2 Build and Push
Tag and push your images to GCR:
- `gcr.io/[PROJECT_ID]/admin-app:latest` (Web/API)
- `gcr.io/[PROJECT_ID]/worker:latest`
- `gcr.io/[PROJECT_ID]/beat:latest`

---

## 6. Deployment to Cloud Run

### 6.1 FastAPI App (API)
```bash
# Capture instance connection name
INSTANCE_CONNECTION_NAME=$(gcloud sql instances describe admin-db --format="value(connectionName)")

gcloud run deploy admin-api \
    --image=gcr.io/[PROJECT_ID]/admin-app:latest \
    --region=[REGION] \
    --network=[VPC_NAME] \
    --subnet=[SUBNET_NAME] \
    --add-cloudsql-instances=$INSTANCE_CONNECTION_NAME \
    --set-env-vars="ENVIRONMENT=production,LOG_LEVEL=INFO" \
    --set-secrets="DATABASE_PASSWORD=DB_PASS:latest,JWT_SECRET=JWT_KEY:latest" \
    --command="uvicorn,main:app,--host,0.0.0.0,--port,8080" \
    --allow-unauthenticated
```

### 6.2 Celery Worker
```bash
gcloud run deploy admin-worker \
    --image=gcr.io/[PROJECT_ID]/worker:latest \
    --region=[REGION] \
    --network=[VPC_NAME] \
    --subnet=[SUBNET_NAME] \
    --add-cloudsql-instances=$INSTANCE_CONNECTION_NAME \
    --no-cpu-throttling \
    --min-instances=1 \
    --command="celery,-A,workers.celery_app,worker,--loglevel=info,-Q,default,ai-processing,analytics-refresh"
```

### 6.3 Celery Beat (Scheduler)
```bash
gcloud run deploy admin-beat \
    --image=gcr.io/[PROJECT_ID]/beat:latest \
    --region=[REGION] \
    --network=[VPC_NAME] \
    --subnet=[SUBNET_NAME] \
    --add-cloudsql-instances=$INSTANCE_CONNECTION_NAME \
    --no-cpu-throttling \
    --min-instances=1 \
    --max-instances=1 \
    --command="celery,-A,workers.celery_app,beat,--loglevel=info"
```

---

## 7. Environment Variables Mapping

| Variable                | Value for GCP                                                                 |
|-------------------------|-------------------------------------------------------------------------------|
| `DATABASE_HOST`         | Private IP of Cloud SQL Instance                                             |
| `DATABASE_PORT`         | `5432` (Standard Postgres port)                                               |
| `REDIS_URL`             | `redis://[REDIS_PRIVATE_IP]:6379/0`                                          |
| `DATABASE_SCHEMA`       | `admin_portal_ai`                                                            |
| `ENVIRONMENT`           | `production`                                                                  |

---

## 8. Best Practices & Security

1.  **IAM Roles**: Assign a dedicated Service Account to each Cloud Run service with only the necessary permissions (Secret Manager Access, Cloud SQL Client).
2.  **Monitoring**: Use Cloud Logging and Cloud Monitoring to track application health and Celery task execution.
3.  **Migration**: Use Cloud Build to run database migrations (Alembic) as a one-off job or before deployment.
4.  **Auto-scaling**: Configure Cloud Run auto-scaling based on CPU/Request metrics for the API, but manage worker scaling based on queue depth if using GKE.
