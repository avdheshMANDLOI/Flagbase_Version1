"""
In-memory event queue — producer-consumer pattern for analytics ingestion.

Why a central queue instead of per-request BackgroundTasks?
  Each HTTP request spawning its own DB write works fine at low volume.
  Under load, hundreds of concurrent background tasks hit the DB simultaneously.
  A single worker draining a queue serializes DB writes and prevents pile-ups.

Why asyncio.Queue instead of threading.Queue?
  The entire FastAPI app runs in an asyncio event loop. asyncio.Queue is
  native to that loop — no thread safety issues, no GIL concerns.

Why not Redis/Celery?
  For a portfolio project, an in-memory queue demonstrates the pattern
  without operational overhead. The architecture is intentionally designed
  so this queue can be swapped for Redis later without touching the
  analytics route or the repository.
"""
import asyncio
import logging
import uuid

logger = logging.getLogger(__name__)

_event_queue: asyncio.Queue = asyncio.Queue()


def get_event_queue() -> asyncio.Queue:
    """Return the global event queue. Used by the ingestion route."""
    return _event_queue


async def enqueue_events(project_id: uuid.UUID, events: list[dict]) -> None:
    """
    Put a batch of events onto the queue.
    Called from the analytics route — never blocks.
    """
    await _event_queue.put((project_id, events))


async def event_worker(session_factory) -> None:
    """
    Single async worker that drains the event queue and writes to DB.

    Runs as a background asyncio task for the lifetime of the app.
    Receives None as a shutdown signal — drains remaining items then exits.

    Why a single worker?
      Simplicity. One writer means no concurrent UPSERT conflicts.
      If throughput becomes a bottleneck, you can scale to N workers —
      but that requires distributed locking, which is a v3 problem.
    """
    from app.repositories.event_repo import EventRepository

    logger.info("Event worker started")

    while True:
        item = await _event_queue.get()

        if item is None:
            logger.info("Event worker received shutdown signal — exiting")
            _event_queue.task_done()
            break

        project_id, events = item

        try:
            async with session_factory() as db:
                repo = EventRepository(db)
                processed = await repo.ingest_batch(project_id, events)
                logger.debug(
                    f"Worker processed {processed}/{len(events)} events "
                    f"for project {project_id}"
                )
        except Exception as e:
            logger.error(f"Event worker failed to process batch: {e}")
            # Don't re-raise — worker must keep running even if one batch fails
        finally:
            _event_queue.task_done()