from __future__ import annotations

import logging

import pytest
from pytest_mock import MockerFixture

from dialog_agent_service.app import handle_request

logger = logging.getLogger()


@pytest.mark.asyncio
async def test_handle_request_existing_user(campaign_req: dict, campaign_user_contexts: dict, df_template_response: dict, mocker: MockerFixture):
    mocker.patch(
        'dialog_agent_service.app.get_user_contexts',
        return_value=campaign_user_contexts,
    )
    mocker.patch(
        'dialog_agent_service.app.get_df_response',
        return_value=df_template_response,
    )
    mocker.patch(
        'dialog_agent_service.app.update_user_contexts',
        return_value=df_template_response['query_result']['output_contexts'],
    )
    resp = await handle_request(campaign_req)
    logger.info(resp)
