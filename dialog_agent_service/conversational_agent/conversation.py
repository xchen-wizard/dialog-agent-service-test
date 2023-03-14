from __future__ import annotations

import logging
import os
from enum import Enum

from .conversation_utils import get_past_k_turns
from .conversation_utils import run_inference

logger = logging.getLogger(__name__)

K = 5  # past k turns
WINDOW = 12  # past hrs
ENDPOINT_ID = '1012733772065406976'
PROJECT_ID = '105526547909'


class Response(Enum):
    SUGGESTION = 'suggestion'


async def handle_conversation_response(merchant_id: str, user_id: int, service_channel_id: str):
    """
    Returns:
        a dict containing the model response with {task: str, cart: list[tuple] | [], response: str | ''}
        if the endpoint was called
        else return an empty json
    """
    docs, vendor_name = await get_past_k_turns(user_id, service_channel_id, merchant_id, k=K, window=WINDOW)
    # Temp: for testing purposes, as not all merchants exist in dev or stage
    # ToDo: remove after we have come up with better e2e testing ideas
    if vendor_name == 'Wizard - Shopify':
        # set vendor to a test brand under test_data
        vendor_name = os.getenv('TEST_MERCHANT', 'AAVRANI')
        logger.info(f'Testing with {vendor_name}')
    if len(docs) > 0:
        response = await run_inference(docs, vendor_name, project_id=PROJECT_ID, endpoint_id=ENDPOINT_ID)
        return {
            'task': response.get('task', ''),
            'cart': response.get('cart', []),
            'response': response.get('response', ''),
        }
    logger.warning('skip calling the model endpoint')
    return {}
