from __future__ import annotations

import logging

import pytest

from dialog_agent_service.app_utils import create_user_contexts
from dialog_agent_service.app_utils import generate_session_id
from dialog_agent_service.app_utils import generate_uuid
from dialog_agent_service.db import get_campaign_products
from dialog_agent_service.db import get_campaign_variant_type
from dialog_agent_service.db import get_user_contexts
from dialog_agent_service.db import update_user_contexts

logger = logging.getLogger()


@pytest.mark.asyncio
async def test_get_campaign_products():
    campaign_id = 123
    products = await get_campaign_products(campaign_id)
    logger.info(products)
    expected_products = [
        {'productId': '62b4d500713740c7c8950914', 'retailerId': 1, 'defaultQuantity': 1, 'maxQuantity': 10}, {
            'productId': '62b4d49d713740c7c8950913',
            'retailerId': 1, 'defaultQuantity': 1, 'maxQuantity': 10,
        }, {'productId': '62b4d3b3713740c7c8950912', 'retailerId': 1, 'defaultQuantity': 1, 'maxQuantity': 10},
    ]
    assert products == expected_products


@pytest.mark.asyncio
async def test_get_campaign_variant_type():
    campaign_id = 123
    variant = await get_campaign_variant_type(campaign_id)
    logger.info(variant)
    assert variant == 45


@pytest.mark.asyncio
async def test_update_user_contexts(campaign_user_contexts):
    campaign_user_contexts['contexts'][-1]['lifespan_count'] += 1
    logger.info(f'New Contexts:\n{campaign_user_contexts}')
    orig_contexts = await update_user_contexts(campaign_user_contexts['_id'], campaign_user_contexts['contexts'])
    logger.info(f'Orig Contexts:\n{orig_contexts}')
    assert len(orig_contexts) == 3


@pytest.mark.asyncio
async def test_get_user_contexts():
    contexts = await get_user_contexts(doc_id='ef115500-25a9-5d38-a715-ed51ceed656d')
    logger.info(contexts)
    assert len(contexts) == 3
