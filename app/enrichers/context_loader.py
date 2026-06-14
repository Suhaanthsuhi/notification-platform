# app/enrichers/context_loader.py
"""
Context Loader Orchestration Module

This module is responsible for orchestrating the execution of all
registered context loaders during the enrichment phase of the
notification pipeline.

It dynamically instantiates each loader registered in the
CONTEXT_LOADERS registry and executes them concurrently using
asyncio.gather.

Each loader contributes a partial context dictionary (e.g.,
user profile, preferences, segmentation data). The results
are aggregated into a single unified context object which is
attached to the enriched event.

Failure Handling:
- Loader exceptions are caught and logged
- Failed loaders do not interrupt other loaders
- Partial context is still returned

This design ensures:
- Extensibility (new loaders can be added via registry)
- Fault tolerance
- Non-blocking parallel enrichment
"""

import asyncio
from app.enrichers.context.registry import CONTEXT_LOADERS

async def load_context(event) -> dict:

    loaders = [loader_cls() for loader_cls in CONTEXT_LOADERS]

    results = await asyncio.gather(
        *[loader.load(event) for loader in loaders],
        return_exceptions=True,
    )

    full_context = {}

    for result in results:
        if isinstance(result, Exception):
            print("Loader failed:", result)
            continue

        if result:
            full_context.update(result)

    return full_context