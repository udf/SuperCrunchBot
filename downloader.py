"""
Handles downloading sticker packs to memory
Based on my gist here: https://gist.github.com/udf/e4e3dbb2e831c8b580d8fddd312714f7
"""
import asyncio
from io import BytesIO
from collections import defaultdict

from util import Job, Sticker
from proxy import client, logger, JOB_MODULES


queue = asyncio.Queue(5)


async def run_job(job: Job):
    logger.info(f'[{job.id}] Running download job')
    await job.status.update('Starting download...')

    sticker_set = job.sticker_set

    # Sticker emojis are retrieved as a mapping of
    # <emoji>: <list of document ids that have this emoji>
    # So we need to build a mapping of <document id>: <list of emoji>
    # Thanks, Durov
    emojis = defaultdict(str)
    for pack in sticker_set.packs:
        for document_id in pack.documents:
            emojis[document_id] += pack.emoticon

    pending_tasks = []
    stickers = []
    for i, document in enumerate(sticker_set.documents):
        file = BytesIO()
        task = asyncio.ensure_future(
            client.download_media(document, file=file)
        ) 
        pending_tasks.append(task)
        stickers.append(Sticker(file, emojis[document.id]))

    await job.status.update('Downloading...')
    await asyncio.wait(pending_tasks)

    errors = ''
    for i, task in reversed(tuple(enumerate(pending_tasks))):
        exception = task.exception()
        if not exception:
            continue
        errors += f'#{i}: {exception.__class__.__name__}\n'
        del stickers[i]

    if errors:
        await job.event.reply(
            f'Some errors occured when downloading these stickers:\n{errors}'
            "\nI'll continue to process the pack as normal, but the stickers "
            "which caused these errors won't be present in the new pack"
        )

    job.stickers = stickers
    logger.info(f'[{job.id}] Finished running download job')
    await job.status.update('Waiting for rescale slot...')
    await JOB_MODULES['rescaler'].queue.put(job)
    await job.status.update('Queued for rescaling.')
