import os
from enum import Enum


ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))


class OpenAIModel(str, Enum):
    GPT4 = "gpt-4"
    GPT35 = "gpt-3.5-turbo"


HISTORY_CLEARED = 'HISTORY_CLEARED'
CLEAR_HISTORY = 'CLEAR_HISTORY'
