from __future__ import annotations

import json

import pytest
from google.cloud.dialogflow_v2.types import DetectIntentResponse


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
        '_id': '3f994047-51c3-5a94-a6da-fe63aba8f757',
        'sessionStr': 'projects/campaign-prototype-oxtt/agent/environments/dev/users/123/sessions/campaign-123-6-146',
        'contexts': [
            {
                'name': 'projects/campaign-prototype-oxtt/agent/environments/dev/users/123/sessions/campaign-123-6-146/contexts/46-followup',
                'lifespan_count': 2,
            }, {
                'name': 'projects/campaign-prototype-oxtt/agent/environments/dev/users/123/sessions/campaign-123-6-146/contexts/session-vars',
                'lifespan_count': 50, 'parameters': {
                    'products': [
                        {
                            'isSelected': False, 'productId': 'mongo_doc_id_01', 'retailerId': 12, 'defaultQuantity': 1,
                            'maxQuantity': 100,
                        },
                        {
                            'isSelected': False, 'productId': 'mongo_doc_id_02', 'retailerId': 12, 'defaultQuantity': 1,
                            'maxQuantity': 100,
                        },
                        {
                            'isSelected': False, 'productId': 'mongo_doc_id_03', 'retailerId': 12, 'defaultQuantity': 1,
                            'maxQuantity': 100,
                        },
                    ],
                },
            },
        ],
    }
    return contexts


@pytest.fixture()
def df_response_no_webhook():
    resp_dict = {
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
        },
    }
    return DetectIntentResponse.from_json(json.dumps(resp_dict))


@pytest.fixture()
def df_response_webhook_error():
    resp_dict = \
        {
            'responseId': 'ba695d0d-dbc1-4624-bbe4-2cdbedc9220d-5c04e5ec',
            'queryResult': {
                'queryText': 'test test', 'action': '2.2-fallback', 'parameters': {},
                'allRequiredParamsPresent': True,
                'fulfillmentText': "Sorry, if you intend to make a pick, simply type the letter for the option you'd like.",
                'fulfillmentMessages': [{
                    'text': {
                        'text': [
                            "Sorry, if you intend to make a pick, simply type the letter for the option you'd like.",
                        ],
                    },
                }],
                'outputContexts': [
                    {
                        'name': 'projects/campaign-prototype-oxtt/agent/environments/dev/users/1/sessions/campaign-1-5-123/contexts/45-followup',
                        'lifespanCount': 1,
                    }, {
                        'name': 'projects/campaign-prototype-oxtt/agent/environments/dev/users/1/sessions/campaign-1-5-123/contexts/session-vars',
                        'lifespanCount': 49, 'parameters': {
                            'products': [
                                {
                                    'defaultQuantity': 1.0, 'maxQuantity': 10.0,
                                    'productId': '62b4d500713740c7c8950914', 'isSelected': False,
                                    'retailerId': 1.0,
                                },
                                {
                                    'maxQuantity': 10.0, 'productId': '62b4d49d713740c7c8950913',
                                    'retailerId': 1.0, 'isSelected': False, 'defaultQuantity': 1.0,
                                },
                                {
                                    'defaultQuantity': 1.0, 'retailerId': 1.0, 'isSelected': False,
                                    'productId': '62b4d3b3713740c7c8950912', 'maxQuantity': 10.0,
                                },
                            ],
                        },
                    }, {
                        'name': 'projects/campaign-prototype-oxtt/agent/environments/dev/users/1/sessions/campaign-1-5-123/contexts/__system_counters__',
                        'lifespanCount': 1,
                        'parameters': {'no-match': 10.0, 'no-input': 0.0},
                    },
                ], 'intent': {
                    'name': 'projects/campaign-prototype-oxtt/agent/intents/e4deb782-29df-538d-bc2d-f9aa08fe5c79',
                    'displayName': '45 - fallback', 'isFallback': True,
                }, 'intentDetectionConfidence': 1.0,
                'diagnosticInfo': {'webhook_latency_ms': 87.0}, 'languageCode': 'en',
            },
            'webhookStatus': {
                'code': 14,
                'message': 'Webhook call failed. Error: UNAVAILABLE, State: URL_UNREACHABLE, Reason: UNREACHABLE_5xx, HTTP status code: 500.',
            },
        }
    return DetectIntentResponse.from_json(json.dumps(resp_dict))


@pytest.fixture()
def df_response_webhook_timeout():
    resp_dict = \
        {
            'responseId': 'ba695d0d-dbc1-4624-bbe4-2cdbedc9220d-5c04e5ec',
            'queryResult': {
                'queryText': 'test test', 'action': '2.2-fallback', 'parameters': {},
                'allRequiredParamsPresent': True,
                'fulfillmentText': "Sorry, if you intend to make a pick, simply type the letter for the option you'd like.",
                'fulfillmentMessages': [{
                    'text': {
                        'text': [
                            "Sorry, if you intend to make a pick, simply type the letter for the option you'd like.",
                        ],
                    },
                }],
                'outputContexts': [
                    {
                        'name': 'projects/campaign-prototype-oxtt/agent/environments/dev/users/1/sessions/campaign-1-5-123/contexts/45-followup',
                        'lifespanCount': 1,
                    }, {
                        'name': 'projects/campaign-prototype-oxtt/agent/environments/dev/users/1/sessions/campaign-1-5-123/contexts/session-vars',
                        'lifespanCount': 49, 'parameters': {
                            'products': [
                                {
                                    'defaultQuantity': 1.0, 'maxQuantity': 10.0,
                                    'productId': '62b4d500713740c7c8950914', 'isSelected': False,
                                    'retailerId': 1.0,
                                },
                                {
                                    'maxQuantity': 10.0, 'productId': '62b4d49d713740c7c8950913',
                                    'retailerId': 1.0, 'isSelected': False, 'defaultQuantity': 1.0,
                                },
                                {
                                    'defaultQuantity': 1.0, 'retailerId': 1.0, 'isSelected': False,
                                    'productId': '62b4d3b3713740c7c8950912', 'maxQuantity': 10.0,
                                },
                            ],
                        },
                    }, {
                        'name': 'projects/campaign-prototype-oxtt/agent/environments/dev/users/1/sessions/campaign-1-5-123/contexts/__system_counters__',
                        'lifespanCount': 1,
                        'parameters': {'no-match': 10.0, 'no-input': 0.0},
                    },
                ], 'intent': {
                    'name': 'projects/campaign-prototype-oxtt/agent/intents/e4deb782-29df-538d-bc2d-f9aa08fe5c79',
                    'displayName': '45 - fallback', 'isFallback': True,
                }, 'intentDetectionConfidence': 1.0,
                'diagnosticInfo': {'webhook_latency_ms': 87.0}, 'languageCode': 'en',
            },
            'webhookStatus': {
                'code': 4,
                'message': 'Webhook call failed. Error: DEADLINE_EXCEEDED',
            },
        }
    return DetectIntentResponse.from_json(json.dumps(resp_dict))


@pytest.fixture()
def df_response_webhook_success():
    resp_dict = {
        'response_id': 'bcb0adf6-4dd8-4c1d-ab1b-d066284f1caa-5c04e5ec',
        'query_result': {
            'query_text': 'yes',
            'action': '46-create_order',
            'parameters': {'number': ''},
            'all_required_params_present': True,
            'fulfillment_text': 'Thank you for your text! Someone from our support team will be with you shortly.',
            'fulfillment_messages': [{
                'text': {
                    'text': [
                        'Thank you for your text! Someone from our support team will be with you shortly.',
                    ],
                },
            }],
            'webhook_payload': {
                'vendorId': 6.0,
                'autoResponse': False,
                'templateMessages': [{'templateTypeId': 'autoresponder'}],
            },
            'output_contexts': [
                {
                    'name': 'projects/campaign-prototype-oxtt/agent/environments/dev/users/58272/sessions/campaign-46-58272/contexts/46-yes-followup',
                    'lifespan_count': 2,
                    'parameters': {'number.original': '', 'number': ''},
                },
                {
                    'name': 'projects/campaign-prototype-oxtt/agent/environments/dev/users/58272/sessions/campaign-46-58272/contexts/session-vars',
                    'lifespan_count': 48,
                    'parameters': {
                        'number': '',
                        'number.original': '',
                        'products': [{
                            'defaultQuantity': 1.0,
                            'maxQuantity': 10.0,
                            'productId': '62d5d7e1a17f01ffec65fbf4',
                            'isSelected': False,
                            'retailerId': 54.0,
                        }],
                    },
                },
            ],
            'intent': {
                'name': 'projects/campaign-prototype-oxtt/agent/intents/4c5fc9c2-8c5e-52b5-9d47-994e0e81c8f6',
                'display_name': '46 - yes',
            },
            'intent_detection_confidence': 1.0,
            'diagnostic_info': {'webhook_latency_ms': 746.0},
            'language_code': 'en',
        },
        'webhook_status': {'message': 'Webhook execution successful'},
    }
    return DetectIntentResponse.from_json(json.dumps(resp_dict))


@pytest.fixture()
def df_response_welcome():
    resp_dict = {
        'response_id': 'f9fd94d7-2de2-4cd1-ab5f-024afe452272-5c04e5ec',
        'query_result': {
            'query_text': 'hi',
            'action': 'input.welcome',
            'parameters': {},
            'all_required_params_present': True,
            'fulfillment_text': 'Hi! How are you doing?',
            'fulfillment_messages': [{'text': {'text': ['Hi! How are you doing?']}}],
            'output_contexts': [{
                'name': 'projects/campaign-prototype-oxtt/agent/environments/dev/users/58272/sessions/campaign-46-58272/contexts/session-vars',
                'lifespan_count': 48,
                'parameters': {
                    'products': [{
                        'isSelected': False,
                        'retailerId': 54.0,
                        'defaultQuantity': 1.0,
                        'productId': '62d5d7e1a17f01ffec65fbf4',
                        'maxQuantity': 10.0,
                    }],
                    'number': '',
                    'number.original': '',
                },
            }],
            'intent': {
                'name': 'projects/campaign-prototype-oxtt/agent/intents/4fbbcef3-936d-4c47-b0ca-5ada9e398571',
                'display_name': 'Default Welcome Intent',
            },
            'intent_detection_confidence': 1.0,
            'language_code': 'en',
        },
    }
    return DetectIntentResponse.from_json(json.dumps(resp_dict))
