from __future__ import annotations

import logging

import pytest
from google.protobuf.json_format import MessageToDict
from pytest_mock import MockerFixture

from dialog_agent_service.df_utils import get_df_response
from dialog_agent_service.df_utils import parse_df_response

logger = logging.getLogger()


@pytest.mark.asyncio
async def test_get_df_response_webhook_success(campaign_req, campaign_user_contexts, df_response_webhook_success, mocker: MockerFixture):
    mock_detect_intent = mocker.patch(
        'dialog_agent_service.df_utils.dialogflow_v2.SessionsAsyncClient.detect_intent',
        return_value=df_response_webhook_success,
    )
    df_response = await get_df_response(campaign_req, campaign_user_contexts)
    logger.info(df_response)
    mock_detect_intent.assert_called()
    assert mock_detect_intent.call_count == 1


@pytest.mark.asyncio
async def test_get_df_response_webhook_failure(
    campaign_req, campaign_user_contexts, df_response_webhook_success,
    df_response_webhook_error, mocker: MockerFixture,
):
    mock_detect_intent = mocker.patch(
        'dialog_agent_service.df_utils.dialogflow_v2.SessionsAsyncClient.detect_intent',
        side_effect=[df_response_webhook_error, df_response_webhook_success],
    )
    df_response = await get_df_response(campaign_req, campaign_user_contexts)
    logger.info(df_response)
    mock_detect_intent.assert_called()
    assert mock_detect_intent.call_count == 2


@pytest.mark.asyncio
async def test_get_df_response_webhook_timeout(
    campaign_req, campaign_user_contexts, df_response_webhook_timeout,
    mocker: MockerFixture,
):
    mock_detect_intent = mocker.patch(
        'dialog_agent_service.df_utils.dialogflow_v2.SessionsAsyncClient.detect_intent',
        return_value=df_response_webhook_timeout,
    )
    df_response = await get_df_response(campaign_req, campaign_user_contexts)
    logger.info(df_response)
    mock_detect_intent.assert_called_once()
    expected_df_response = {
        'query_result': {
            'fulfillment_text': 'no response', 'webhook_payload': {'autoResponse': False},
        },
    }
    assert df_response == expected_df_response


@pytest.mark.asyncio
async def test_get_df_response_no_webhook(
    campaign_req, campaign_user_contexts, df_response_no_webhook,
    mocker: MockerFixture,
):
    mock_detect_intent = mocker.patch(
        'dialog_agent_service.df_utils.dialogflow_v2.SessionsAsyncClient.detect_intent',
        return_value=df_response_no_webhook,
    )
    df_response = await get_df_response(campaign_req, campaign_user_contexts)
    logger.info(df_response)
    assert mock_detect_intent.call_count == 3


@pytest.mark.asyncio
async def test_get_df_response_welcome(
    campaign_req, campaign_user_contexts, df_response_welcome,
    mocker: MockerFixture,
):
    mock_detect_intent = mocker.patch(
        'dialog_agent_service.df_utils.dialogflow_v2.SessionsAsyncClient.detect_intent',
        return_value=df_response_welcome,
    )
    df_response = await get_df_response(campaign_req, campaign_user_contexts)
    logger.info(df_response)
    mock_detect_intent.assert_called_once()


def test_parse_df_response_none():
    response = parse_df_response(None, vendor_id=3)
    logger.info(response)
    expected_response = {
        'vendorId': 3, 'templateMessages': [
            {'templateTypeId': 'autoresponder', 'templateVariables': {}},
        ], 'message': 'template', 'autoResponse': False,
    }
    assert response == expected_response


def test_parse_df_response(df_response_webhook_success):
    response = parse_df_response(
        MessageToDict(
            df_response_webhook_success._pb, preserving_proto_field_name=True,
        ), vendor_id=1,
    )
    logger.info(response)
    expected_response = {
        'vendorId': 1, 'templateMessages': [{
            'templateTypeId': 'autoresponder', 'templateVariables': {
            },
        }], 'message': 'Thank you for your text! Someone from our support team will be with you shortly.', 'autoResponse': False,
    }
    assert response == expected_response
