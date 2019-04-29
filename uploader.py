"""
Handles uploading the rescaled stickers and figuring out an unused url
"""
import asyncio
import re

from telethon import utils
from telethon.errors import ShortnameOccupyFailedError, PackShortNameOccupiedError
from telethon.tl import types
from telethon.tl.functions.messages import UploadMediaRequest
from telethon.tl.functions.stickers import CreateStickerSetRequest

from util import Job, Sticker, get_pack_url, get_rand_letters
from proxy import client, logger, me


queue = asyncio.Queue(5)
re_by_us = re.compile(f'(?i)_[a-z]+_by_{me.username}$')
re_by_bot = re.compile(r'(?i)_by_\w+bot$')


async def upload_sticker(sticker: Sticker):
    sticker.file.seek(0)
    file = await client.upload_file(sticker.file, part_size_kb=512)
    file = types.InputMediaUploadedDocument(file, 'image/png', [])
    media = await client(UploadMediaRequest('me', file))
    return types.InputStickerSetItem(
        document=utils.get_input_document(media),
        emoji=sticker.emoji
    )


async def run_job(job: Job):
    logger.info(f'[{job.id}] Running upload job')
    await job.status.update('Uploading...')

    pending_tasks = []
    for sticker in job.stickers:
        pending_tasks.append(
            asyncio.create_task(upload_sticker(sticker))
        )

    await asyncio.wait(pending_tasks)
    stickers = [task.result() for task in pending_tasks]

    # Create sticker pack
    # We use a unique id at the end of the original name because the
    # the stickers belong to the user, which means they can be deleted
    id_len = 2
    title = f'Distorted {job.sticker_set.set.title}'[:64]
    original_short_name = re_by_us.sub('', job.sticker_set.set.short_name)
    original_short_name = re_by_bot.sub('', original_short_name)
    while 1:
        try:
            suffix = f'_{get_rand_letters(id_len)}_by_{me.username}'
            short_name = f'{original_short_name}'[:62 - len(suffix)] + suffix
            logger.info('Trying to create pack %s', short_name)
            await client(CreateStickerSetRequest(
                user_id=job.owner,
                title=title,
                short_name=short_name,
                stickers=stickers
            ))
            break
        except (ShortnameOccupyFailedError, PackShortNameOccupiedError):
            id_len = min(7, id_len + 1)
            continue

    logger.info(f'[{job.id}] Finished running upload job')
    await job.event.reply('Done! ' + get_pack_url(short_name))
    await job.status.message.delete()
