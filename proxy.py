from logging import Logger
from typing import Dict
from types import ModuleType

from telethon import TelegramClient
from telethon.tl import types

client: TelegramClient = None
logger: Logger = None
JOB_MODULES: Dict[str, ModuleType] = {}
me: types.User = None
