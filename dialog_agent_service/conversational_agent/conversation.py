from __future__ import annotations

import logging
import os
from enum import Enum
from dialog_agent_service.actions.cart_actions import cart_get
from dialog_agent_service.utils.cart_utils import create_or_update_active_cart, sync_virtual_cart
from .conversation_utils import get_past_k_turns
from .conversation_utils import run_inference
from collections import defaultdict

logger = logging.getLogger(__name__)

ENDPOINT_ID = os.getenv('T5_VERTEX_AI_ENDPOINT_ID', '1012733772065406976')
PROJECT_ID = os.getenv('VERTEX_AI_PROJECT_ID', '105526547909')
cached_cart = defaultdict(dict)


class ResponseType(Enum):
    CX = 'cx'
    ASSISTED = 'assisted'
    AUTOMATED = 'automated'


async def handle_conversation_response(
    merchant_id: str, user_id: int, service_channel_id: int,
    k: int, window: int, test_merchant: str, task_routing_config: dict = {}, test_args: dict = {}
):
    """
    Handler to retrieve, process messages and obtain response from Vertex AI endpoint
    Args:
        merchant_id: vendorId
        user_id: userId
        service_channel_id: serviceChannelId
        k: the last k messages (We don't yet process turns, which could include multiple messages). Default to 5.
        window: the window of last n hours to retrieve data from. Default to 12 hrs.
        test_merchant: the merchant you want to test - for testing purposes only
    Returns:
        a dict containing the model response with {task: str, cart: list[tuple] | [], response: str | ''}
        if the endpoint was called
        else return an empty json
    """
    if test_args:
        docs = test_args['docs']
        vendor_name = test_args['vendor_name']
        clear_history = test_args['clear_history']
    else:
        docs, vendor_name, clear_history = await get_past_k_turns(user_id, service_channel_id, merchant_id, k=k, window=window)
    if clear_history:
        create_or_update_active_cart(merchant_id, user_id, [])

    # Temp: for testing purposes, as not all merchants exist in dev or stage
    # ToDo: remove after we have come up with better e2e testing ideas
    if test_merchant:
        # set vendor to a test brand under test_data
        vendor_name = test_merchant
        logger.info(f'Testing with {vendor_name}')
    if len(docs) > 0:
        current_cart = sync_virtual_cart(merchant_id, user_id)
        response = await run_inference(
            docs, vendor_name, merchant_id, project_id=PROJECT_ID, endpoint_id=ENDPOINT_ID,
            current_cart=current_cart, task_routing_config=task_routing_config)
        cart = response.get('cart', None)
        if cart is not None:
            if not response['suggested']:
                success = create_or_update_active_cart(
                    merchant_id, user_id, cart)
                response['suggested'] = not success
            updated_cart = cart_get(merchant_id, user_id)
            response['cart'] = updated_cart
        return response
    logger.warning(f"""
        no messages retrieved for userId {user_id}, serviceChannelId {service_channel_id}, vendorId {merchant_id}.
        Skip calling the model endpoint
    """)
    return {}
