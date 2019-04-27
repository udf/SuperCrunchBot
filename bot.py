import asyncio
import logging
import importlib
import uuid
import traceback

from telethon import TelegramClient
from telethon import events
from telethon.tl.types import DocumentAttributeSticker
from telethon.tl.functions.messages import GetStickerSetRequest

from util import StatusMessage, Job, find_instance
import proxy


proxy.JOB_MODULES = JOB_MODULES = {}


logging.basicConfig(level=logging.INFO)
logger: logging.Logger = logging.getLogger('main')
proxy.client = client = TelegramClient("bot", 6, "eb06d4abfb49dc3eeb1aeb98ae0f581e").start()
proxy.me = me = asyncio.get_event_loop().run_until_complete(client.get_me())


@client.on(events.NewMessage(pattern=r'/start'))
async def on_start(event):
    await event.respond('Send a sticker.')


@client.on(events.NewMessage)
async def on_message(event):
    if not event.message.sticker:
        return
    sticker = event.message.sticker
    sticker_attrib = find_instance(sticker.attributes, DocumentAttributeSticker)
    if not sticker_attrib.stickerset:
        await event.reply('That sticker is not part of a pack')
        return

    sticker_set = await client(GetStickerSetRequest(sticker_attrib.stickerset))

    status = StatusMessage(await event.reply('Pending'))
    job = Job(
        id=uuid.uuid1(),
        owner=await event.get_input_sender(),
        event=event,
        status=status,
        sticker_set=sticker_set
    )
    logger.info(
        '[%s] User %s requested sticker set %s',
        job.id,
        event.from_id,
        sticker_set.set.short_name
    )

    await status.update('Waiting for download slot.')
    await JOB_MODULES['downloader'].queue.put(job)
    await status.update('Queued for download.')


async def job_runner(mod):
    while 1:
        job: Job = await mod.queue.get()
        try:
            await mod.run_job(job)
        except Exception as e:
            logger.exception('Exception on job runner for %s', mod.__name__)
            try:
                await job.event.reply(
                    'Sorry, an unexpected error occurred.\n'
                    'Please contact the owner of this bot and give them this '
                    f'number: {job.uuid}'
                )
            except:
                pass  # everything is ok


def load_handler_module(name):
    proxy.logger = logging.getLogger(name)
    mod = importlib.import_module(name)
    asyncio.ensure_future(job_runner(mod))
    return mod


for name in ('downloader', 'rescaler', 'uploader'):
    JOB_MODULES[name] = load_handler_module(name)

client.run_until_disconnected()
