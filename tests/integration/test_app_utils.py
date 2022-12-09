from __future__ import annotations

import logging

import pytest

from dialog_agent_service.app_utils import create_user_contexts
from dialog_agent_service.app_utils import generate_session_id
from dialog_agent_service.app_utils import generate_uuid

logger = logging.getLogger()


@pytest.mark.asyncio
async def test_create_user_contexts(campaign_req):
    session_id = generate_session_id(campaign_req)
    doc_id = generate_uuid(session_id)
    new_contexts = await create_user_contexts(campaign_req, session_id, doc_id)
    logger.info(f'New Contexts:\n{new_contexts}')
    expected_contexts = {
        '_id': 'ef115500-25a9-5d38-a715-ed51ceed656d', 'sessionStr': 'projects/campaign-prototype-oxtt/agent/environments/draft/users/1/sessions/campaign-1-5-123', 'contexts': [
            {'name': 'projects/campaign-prototype-oxtt/agent/environments/draft/users/1/sessions/campaign-1-5-123/contexts/45-followup', 'lifespan_count': 2}, {
                'name': 'projects/campaign-prototype-oxtt/agent/environments/draft/users/1/sessions/campaign-1-5-123/contexts/session-vars', 'lifespan_count': 50, 'parameters': {
                    'products': [{'isSelected': False, 'productId': '62b4d500713740c7c8950914', 'retailerId': 1, 'defaultQuantity': 1, 'maxQuantity': 10}, {'isSelected': False, 'productId': '62b4d49d713740c7c8950913', 'retailerId': 1, 'defaultQuantity': 1, 'maxQuantity': 10}, {'isSelected': False, 'productId': '62b4d3b3713740c7c8950912', 'retailerId': 1, 'defaultQuantity': 1, 'maxQuantity': 10}],
                },
            },
        ],
    }
    assert new_contexts == expected_contexts
