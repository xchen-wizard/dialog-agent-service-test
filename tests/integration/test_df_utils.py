from __future__ import annotations

import logging

import pytest

from dialog_agent_service.df_utils import get_df_response

logger = logging.getLogger()


@pytest.mark.asyncio
async def test_get_df_response(campaign_req_hi, campaign_user_contexts):
    resp = await get_df_response(campaign_req_hi, campaign_user_contexts)
    logger.info(resp)
    assert resp is not None
