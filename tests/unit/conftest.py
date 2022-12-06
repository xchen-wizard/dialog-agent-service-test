import pytest
from pytest_mock import MockerFixture


@pytest.fixture
def campaign_req():
    return {
        'text': 'test test',
        'userId': '123',
        'serviceChannelId': '6',
        'vendorId': '12',
        'vendorName': 'Test merchant',
        'flowType': 'campaign',  # variant as defined in campaigns.campaignFlowType
        'payload': {'campaignId': '146'}
    }


@pytest.fixture
def welcome_flow_req():
    return


@pytest.fixture()
def campaign_products():
    products = [
        {
            "productId": "mongo_doc_id_01",
            "retailerId": 12,
            "defaultQuantity": 1,
            "maxQuantity": 100
         },
        {
            "productId": "mongo_doc_id_02",
            "retailerId": 12,
            "defaultQuantity": 1,
            "maxQuantity": 100
        },
        {
            "productId": "mongo_doc_id_03",
            "retailerId": 12,
            "defaultQuantity": 1,
            "maxQuantity": 100
        }
    ]
    return products


@pytest.fixture()
def campaign_user_contexts():
    contexts = {'_id': '3f994047-51c3-5a94-a6da-fe63aba8f757', 'sessionStr': 'projects/campaign-prototype-oxtt/agent/environments/dev/users/123/sessions/campaign-123-6-146', 'contexts': [{'name': 'projects/campaign-prototype-oxtt/agent/environments/dev/users/123/sessions/campaign-123-6-146/contexts/46-followup', 'lifespanCount': 2}, {'name': 'projects/campaign-prototype-oxtt/agent/environments/dev/users/123/sessions/campaign-123-6-146/contexts/session-vars', 'lifespanCount': 50, 'parameters': [{'isSelected': False, 'productId': 'mongo_doc_id_01', 'retailerId': 12, 'defaultQuantity': 1, 'maxQuantity': 100}, {'isSelected': False, 'productId': 'mongo_doc_id_02', 'retailerId': 12, 'defaultQuantity': 1, 'maxQuantity': 100}, {'isSelected': False, 'productId': 'mongo_doc_id_03', 'retailerId': 12, 'defaultQuantity': 1, 'maxQuantity': 100}]}]}
    return contexts