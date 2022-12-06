from __future__ import annotations

import logging

import pytest
from pytest_mock import MockerFixture

from dialog_agent_service.df_utils import get_df_response
from dialog_agent_service.df_utils import parse_df_response

logger = logging.getLogger()


@pytest.mark.asyncio
async def test_get_df_response(campaign_req, campaign_user_contexts, mocker: MockerFixture):
    mocked_df_response: dict = {}
    mock_detect_intent = mocker.patch(
        'dialog_agent_service.df_utils.dialogflow_v2.SessionsAsyncClient.detect_intent',
        return_value=mocked_df_response,
    )
    df_response = await get_df_response(campaign_req, campaign_user_contexts)
    logger.info(df_response)
    mock_detect_intent.assert_called()


def test_parse_df_response_none():
    response = parse_df_response(None, vendor_id=3)
    logger.info(response)


def test_parse_df_response(df_template_response):
    response = parse_df_response(df_template_response, vendor_id=1)
    logger.info(response)
