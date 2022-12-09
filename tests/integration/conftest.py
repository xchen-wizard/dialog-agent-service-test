from __future__ import annotations

import pytest


@pytest.fixture
def campaign_req():
    return {
        'text': 'test test',
        'userId': '1',
        'serviceChannelId': '5',
        'vendorId': '12',
        'vendorName': 'Test merchant',
        'flowType': 'campaign',  # variant as defined in campaigns.campaignFlowType
        'payload': {'campaignId': '123'},
    }


@pytest.fixture()
def campaign_user_contexts():
    return {'_id': 'ef115500-25a9-5d38-a715-ed51ceed656d', 'sessionStr': 'projects/campaign-prototype-oxtt/agent/environments/dev/users/1/sessions/campaign-1-5-123', 'contexts': [{'name': 'projects/campaign-prototype-oxtt/agent/environments/dev/users/1/sessions/campaign-1-5-123/contexts/45-followup', 'lifespan_count': 2}, {'name': 'projects/campaign-prototype-oxtt/agent/environments/dev/users/1/sessions/campaign-1-5-123/contexts/session-vars', 'lifespan_count': 50, 'parameters': {'products': [{'isSelected': False, 'productId': '62b4d500713740c7c8950914', 'retailerId': 1, 'defaultQuantity': 1, 'maxQuantity': 10}, {'isSelected': False, 'productId': '62b4d49d713740c7c8950913', 'retailerId': 1, 'defaultQuantity': 1, 'maxQuantity': 10}, {'isSelected': False, 'productId': '62b4d3b3713740c7c8950912', 'retailerId': 1, 'defaultQuantity': 1, 'maxQuantity': 10}]}}]}


@pytest.fixture()
def campaign_req_hi():
    return {
        'text': 'hi',
        'userId': '1',
        'serviceChannelId': '5',
        'vendorId': '12',
        'vendorName': 'Test merchant',
        'flowType': 'campaign',  # variant as defined in campaigns.campaignFlowType
        'payload': {'campaignId': '123'},
    }
