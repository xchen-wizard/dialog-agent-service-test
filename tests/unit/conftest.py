from __future__ import annotations

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
        'payload': {'campaignId': '146'},
    }


@pytest.fixture
def welcome_flow_req():
    return


@pytest.fixture()
def campaign_products():
    products = [
        {
            'productId': 'mongo_doc_id_01',
            'retailerId': 12,
            'defaultQuantity': 1,
            'maxQuantity': 100,
        },
        {
            'productId': 'mongo_doc_id_02',
            'retailerId': 12,
            'defaultQuantity': 1,
            'maxQuantity': 100,
        },
        {
            'productId': 'mongo_doc_id_03',
            'retailerId': 12,
            'defaultQuantity': 1,
            'maxQuantity': 100,
        },
    ]
    return products


@pytest.fixture()
def campaign_user_contexts():
    contexts = {
        '_id': '3f994047-51c3-5a94-a6da-fe63aba8f757', 'sessionStr': 'projects/campaign-prototype-oxtt/agent/environments/dev/users/123/sessions/campaign-123-6-146', 'contexts': [
            {'name': 'projects/campaign-prototype-oxtt/agent/environments/dev/users/123/sessions/campaign-123-6-146/contexts/46-followup', 'lifespan_count': 2}, {
                'name': 'projects/campaign-prototype-oxtt/agent/environments/dev/users/123/sessions/campaign-123-6-146/contexts/session-vars', 'lifespan_count': 50, 'parameters': {
                    'products': [{'isSelected': False, 'productId': 'mongo_doc_id_01', 'retailerId': 12, 'defaultQuantity': 1, 'maxQuantity': 100}, {'isSelected': False, 'productId': 'mongo_doc_id_02', 'retailerId': 12, 'defaultQuantity': 1, 'maxQuantity': 100}, {'isSelected': False, 'productId': 'mongo_doc_id_03', 'retailerId': 12, 'defaultQuantity': 1, 'maxQuantity': 100}],
                },
            },
        ],
    }
    return contexts


@pytest.fixture()
def df_template_response():
    return {
        'response_id': '1ee83f6b-aac2-4ac5-a7bf-555b27c4ec95-5c04e5ec',
        'query_result': {
            'query_text': 'yes',
            'action': '44.44-yes',
            'parameters': {'number': ''},
            'all_required_params_present': True,
            'fulfillment_text': 'template',
            'fulfillment_messages': [{
                'text': {
                      'text': [
                          'template',
                      ],
                },
            }],
            'output_contexts': [
                {
                    'name': 'projects/campaign-prototype-oxtt/agent/environments/dev/users/58272/sessions/campaign-44-58272/contexts/44-yes-followup',
                    'lifespan_count': 2,
                    'parameters': {'number.original': '', 'number': ''},
                },
                {
                    'name': 'projects/campaign-prototype-oxtt/agent/environments/dev/users/58272/sessions/campaign-44-58272/contexts/session-vars',
                    'lifespan_count': 48,
                    'parameters': {
                        'number': '',
                        'number.original': '',
                        'products': [{
                            'maxQuantity': 10.0,
                            'defaultQuantity': 1.0,
                            'retailerId': 54.0,
                            'isSelected': False,
                            'productId': '62d5d7e1a17f01ffec65fbf4',
                        }],
                    },
                },
            ],
            'intent': {
                'name': 'projects/campaign-prototype-oxtt/agent/intents/a3b04e9b-419f-556a-b9d3-52430fc6cb3a',
                'display_name': '44 - yes',
            },
            'intent_detection_confidence': 1.0,
            'language_code': 'en',
            'webhook_payload': {
                'vendorId': 1,
                'templateMessages': [
                    {
                        'templateTypeId': 'test-template-id', 'templateVariables': {
                             'name': 'testUser',
                             'vendorName': 'testVendor',
                        },
                    },
                ],
                'autoResponse': False,
            },
        },
    }
