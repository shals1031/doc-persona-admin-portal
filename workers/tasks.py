import uuid

from celery import shared_task
from celery.utils.log import get_task_logger

from workers.celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(
    name="workers.tasks.refresh_dashboard_aggregates",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def refresh_dashboard_aggregates(self):
    """Refresh the dashboard_aggregates materialized view."""
    try:
        import asyncio

        from sqlalchemy import text

        from core.config import settings
        from core.database import AsyncSessionFactory

        async def _run():
            async with AsyncSessionFactory() as session:
                await session.execute(
                    text("REFRESH MATERIALIZED VIEW CONCURRENTLY core.dashboard_fact")
                )
                await session.execute(
                    text("REFRESH MATERIALIZED VIEW CONCURRENTLY core.doctor_profile_flat_table")
                )
                await session.execute(
                    text("REFRESH MATERIALIZED VIEW CONCURRENTLY core.dashboard_aggregates")
                )
                await session.commit()

        asyncio.run(_run())
        logger.info("dashboard_aggregates refreshed successfully")
    except Exception as exc:
        logger.error("Failed to refresh dashboard_aggregates: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="workers.tasks.process_embedding_job",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="ai-processing",
)
def process_embedding_job(self, submission_id: str):
    """
    Placeholder for AI embedding generation pipeline.
    Future: call embedding model, store result in doctor_ai_profile,
    update embedding_jobs status, write ai_processing_log.
    """
    logger.info("Processing embedding job for submission_id=%s", submission_id)
    # TODO: integrate with embedding model (e.g. sentence-transformers or Anthropic)
    pass
