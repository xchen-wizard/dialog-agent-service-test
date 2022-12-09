from __future__ import annotations

import logging

import pytest
from google.cloud.dialogflow_v2.types import DetectIntentResponse
from google.protobuf.json_format import MessageToDict
from pytest_mock import MockerFixture

from dialog_agent_service.app import handle_request

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
