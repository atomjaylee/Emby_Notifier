from __future__ import annotations

import asyncio
import re
import traceback

from aiohttp import web


UNICODE_ESCAPE_RE = re.compile(r"\\u[0-9a-fA-F]{4}")


async def worker(msg_queue: asyncio.Queue, processor, logger) -> None:
    logger.info("Emby Notifier started.")
    while True:
        raw = await msg_queue.get()
        try:
            if UNICODE_ESCAPE_RE.search(raw):
                raw = raw.encode("utf-8").decode("unicode_escape")
            result = processor.process_raw_message(raw)
            logger.info(f"Message processed with result: {result}")
        except Exception:
            logger.error(traceback.format_exc())
        finally:
            msg_queue.task_done()


async def handle_post(request: web.Request) -> web.Response:
    logger = request.app.get("logger")
    if request.content_type != "application/json":
        if logger:
            logger.warning(f"Rejected webhook from {request.remote} with content type {request.content_type}")
        return web.Response(
            status=415,
            text="Unsupported content type. Please use application/json.",
        )

    raw = await request.text()
    if logger:
        logger.info(f"Webhook received from {request.remote}: {request.content_type}, {len(raw)} bytes")
    await request.app["msg_queue"].put(raw)
    return web.Response(status=200)


async def run_server(config, processor, logger) -> None:
    msg_queue: asyncio.Queue = asyncio.Queue()
    app = web.Application()
    app["msg_queue"] = msg_queue
    app["logger"] = logger
    app.router.add_post("/", handle_post)

    worker_task = asyncio.create_task(worker(msg_queue, processor, logger))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.host, config.port)
    await site.start()
    logger.info(f"HTTP server started at http://{config.host}:{config.port}")
    await worker_task
