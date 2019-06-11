import time
import random
import string
from io import BytesIO
from dataclasses import dataclass
from typing import List

from telethon import events
from telethon.tl import types


class StatusMessage:
    def __init__(self, message):
        self.message = message
        self.last_edit = time.time()
    
    async def update(self, text, important=True):
        current_time = time.time()
        if not important and current_time - self.last_edit < 5:
            return
        self.last_edit = current_time
        await self.message.edit(text)


@dataclass
class Sticker:
    file: BytesIO
    emoji: str


@dataclass
class Job:
    # Common
    id: str
    owner: types.InputUser
    event: events.NewMessage
    status: StatusMessage


@dataclass
class StickerJob(Job):
    # Downloader
    sticker_set: types.messages.StickerSet

    # Resizer, Uploader
    stickers: List[Sticker] = None 


@dataclass
class PhotoJob(Job):
    # Downloader
    photo: types.Photo

    # Resizer? Uploader?
    result: BytesIO = None


def find_instance(items, class_or_tuple):
    for item in items:
        if isinstance(item, class_or_tuple):
            return item
    return None


def get_pack_url(short_name):
    return f'https://t.me/addstickers/{short_name}'


def get_rand_letters(k):
    return ''.join(random.choices(string.ascii_uppercase, k=k))
