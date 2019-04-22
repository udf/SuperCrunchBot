"""
Handles spawning an executor to liquid rescale the stickers
"""
import asyncio
import concurrent.futures
from io import BytesIO

from wand.image import Image

from util import Job, Sticker
from proxy import logger, JOB_MODULES

queue = asyncio.Queue(3)
executor = concurrent.futures.ThreadPoolExecutor()


def crunch(sticker: Sticker):
    sticker.file.seek(0)
    with Image(file=sticker.file) as i:
        i.resize(width=i.width * 2, height=i.height * 2, filter='sinc')
        i.liquid_rescale(i.width // 2, i.height // 2, delta_x=1, rigidity=5)
        sticker.file = BytesIO()
        i.save(file=sticker.file)


def do_crunch(loop, job: Job):
    futures = [executor.submit(crunch, sticker) for sticker in job.stickers]
    for i, future in enumerate(concurrent.futures.as_completed(futures)):
        asyncio.run_coroutine_threadsafe(
            job.status.update(f'Rescaled {i+1}/{len(futures)}', important=False),
            loop
        ).result()


async def run_job(job: Job):
    logger.info(f'[{job.id}] Running rescale job')
    await job.status.update('Crunching...')

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: do_crunch(loop, job))

    logger.info(f'[{job.id}] Finished running rescale job')
    await job.status.update('Waiting for upload slot...')
    await JOB_MODULES['uploader'].queue.put(job)
    await job.status.update('Queued for upload.')
