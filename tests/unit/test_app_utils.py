from __future__ import annotations

import logging

import pytest
from pytest_mock import MockerFixture

from dialog_agent_service.app_utils import create_user_contexts
from dialog_agent_service.app_utils import generate_session_id
from dialog_agent_service.app_utils import generate_uuid

logger = logging.getLogger(__name__)


def test_generate_session_id(campaign_req):
    actual_session_id = generate_session_id(campaign_req)
    logger.info(actual_session_id)
    assert actual_session_id == 'campaign-123-6-146'


def test_generate_uuid():
    uid = generate_uuid('campaign-123-6-146')
    logger.info(uid)
    assert uid == '3f994047-51c3-5a94-a6da-fe63aba8f757'


@pytest.mark.asyncio
async def test_create_user_contexts(campaign_req: dict, mocker: MockerFixture, campaign_products: list[dict]):
    mocker.patch(
        'dialog_agent_service.app_utils.get_campaign_products',
        return_value=campaign_products,
    )
    variant_type = 46
    mocker.patch(
        'dialog_agent_service.app_utils.get_campaign_variant_type',
        return_value=variant_type,
    )
    session_id = 'campaign-123-6-146'
    doc_id = '3f994047-51c3-5a94-a6da-fe63aba8f757'
    actual_contexts = await create_user_contexts(campaign_req, session_id, doc_id)
    logger.info(actual_contexts)
    expected_contexts = {
        '_id': '3f994047-51c3-5a94-a6da-fe63aba8f757', 'sessionStr': 'projects/campaign-prototype-oxtt/agent/environments/draft/users/123/sessions/campaign-123-6-146', 'contexts': [
            {'name': 'projects/campaign-prototype-oxtt/agent/environments/draft/users/123/sessions/campaign-123-6-146/contexts/46-followup', 'lifespan_count': 2}, {
                'name': 'projects/campaign-prototype-oxtt/agent/environments/draft/users/123/sessions/campaign-123-6-146/contexts/session-vars', 'lifespan_count': 50, 'parameters': {
                    'products': [{'isSelected': False, 'productId': 'mongo_doc_id_01', 'retailerId': 12, 'defaultQuantity': 1, 'maxQuantity': 100}, {'isSelected': False, 'productId': 'mongo_doc_id_02', 'retailerId': 12, 'defaultQuantity': 1, 'maxQuantity': 100}, {'isSelected': False, 'productId': 'mongo_doc_id_03', 'retailerId': 12, 'defaultQuantity': 1, 'maxQuantity': 100}],
                },
            },
        ],
    }
    assert actual_contexts == expected_contexts


@pytest.mark.asyncio
async def test_create_user_contexts_exceptions(campaign_req: dict, mocker: MockerFixture, campaign_products: list[dict]):
    session_id = 'campaign-123-6-146'
    doc_id = '3f994047-51c3-5a94-a6da-fe63aba8f757'
    mocker.patch(
        'dialog_agent_service.app_utils.get_campaign_products', return_value=None,
    )
    with pytest.raises(Exception):
        await create_user_contexts(campaign_req, session_id, doc_id)
    mocker.patch(
        'dialog_agent_service.app_utils.get_campaign_products',
        return_value=campaign_products,
    )
    variant_type = None
    mocker.patch(
        'dialog_agent_service.app_utils.get_campaign_variant_type',
        return_value=variant_type,
    )
    with pytest.raises(Exception):
        await create_user_contexts(campaign_req, session_id, doc_id)
