"""
Handles spawning an executor to liquid rescale the stickers
"""
import asyncio
import concurrent.futures
from io import BytesIO

from wand.image import Image

from util import Job, StickerJob, PhotoJob, Sticker
from proxy import logger, JOB_MODULES

queue = asyncio.Queue(3)


def crunch(index, image_data):
    with Image(blob=image_data) as i:
        i.resize(width=i.width * 2, height=i.height * 2, filter='sinc')
        i.liquid_rescale(i.width // 2, i.height // 2, delta_x=1, rigidity=5)
        image = BytesIO()
        i.save(file=image)
    image.seek(0)
    return index, image.read()


def crunch_stickers(loop, job: StickerJob):
    executor = concurrent.futures.ProcessPoolExecutor()

    futures = []
    for i, sticker in enumerate(job.stickers):
        sticker.file.seek(0)
        data = sticker.file.read()
        sticker.file = None
        futures.append(executor.submit(crunch, i, data))

    for n_done, future in enumerate(concurrent.futures.as_completed(futures)):
        i, sticker = future.result()
        job.stickers[i].file = BytesIO(sticker)
        asyncio.run_coroutine_threadsafe(
            job.status.update(f'Rescaled {n_done+1}/{len(futures)}', important=False),
            loop
        ).result()


def crunch_photo(loop, job: PhotoJob):
    executor = concurrent.futures.ProcessPoolExecutor()

    job.result.seek(0)
    data = job.result.read()
    job.result.file = None
    i, photo = executor.submit(crunch, 0, data).result()
    job.result.file = BytesIO(photo)
    asyncio.run_coroutine_threadsafe(
        job.status.update('Rescaled 1', important=False),
        loop
    ).result()


async def run_job(job: Job):
    logger.info(f'[{job.id}] Running rescale job')
    await job.status.update('Crunching...')

    loop = asyncio.get_running_loop()

    if isinstance(job, StickerJob):
        await loop.run_in_executor(None, lambda: crunch_stickers(loop, job))
    elif isinstance(job, PhotoJob):
        await loop.run_in_executor(None, lambda: crunch_photo(loop, job))
    else:
        raise TypeError('Unknown job type {}'.format(type(job)))

    logger.info(f'[{job.id}] Finished running rescale job')
    await job.status.update('Waiting for upload slot...')
    await JOB_MODULES['uploader'].queue.put(job)
    await job.status.update('Queued for upload.')
