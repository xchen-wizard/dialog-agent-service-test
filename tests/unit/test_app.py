from __future__ import annotations

import logging

import pytest
from google.cloud.dialogflow_v2.types import DetectIntentResponse
from google.protobuf.json_format import MessageToDict
from pytest_mock import MockerFixture

from dialog_agent_service.app import handle_request
from dialog_agent_service.conversational_agent.conversation import handle_conversation_response

logger = logging.getLogger()


@pytest.mark.asyncio
async def test_handle_request_existing_user(
    campaign_req: dict, campaign_user_contexts: dict,
    df_response_webhook_success: DetectIntentResponse, mocker: MockerFixture,
):
    mocker.patch(
        'dialog_agent_service.app.get_user_contexts',
        return_value=campaign_user_contexts,
    )
    mocker.patch(
        'dialog_agent_service.app.get_df_response',
        return_value=MessageToDict(
            df_response_webhook_success._pb, preserving_proto_field_name=True,
        ),
    )
    mocker.patch(
        'dialog_agent_service.app.update_user_contexts',
        return_value=None,
    )
    resp = await handle_request(campaign_req)
    logger.info(resp)


@pytest.mark.asyncio
async def test_handle_conversation_response(mocker: MockerFixture):
    """
    ToDo:
    1. test this in a different module, not test_app
    2. currently i mocked the db calls, but not the call to vertex ai. ideally this should be mocked out as well.

    """
    past_k_turns = [
        ('outbound', 'reply yes to buy'),
        ('inbound', 'yes'),
        ('outbound', 'are we shipping to 123 Green st. Seattle?'),
        ('inbound', 'yes'),
    ]
    vendor_name = 'test vendor'
    mocker.patch(
        'dialog_agent_service.conversational_agent.conversation.get_past_k_turns',
        return_value=(past_k_turns, vendor_name),
    )
    # mocker.patch(
    #     'dialog_agent_service.conversational_agent.conversation.run_inference',
    #     return_value={
    #         'response': 'test response',
    #         'responseType': 'suggestion',
    #     },
    # )
    response = await handle_conversation_response(merchant_id=6, user_id=58789, service_channel_id=5)
    logger.info(response)
    assert response is not None
