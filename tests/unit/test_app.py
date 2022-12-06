from dialog_agent_service.app import handle_request
import pytest
from pytest_mock import MockerFixture


@pytest.mark.asyncio
async def test_handle_request_existing_user(campaign_req: dict, campaign_user_contexts: dict, mocker: MockerFixture):
    mocker.patch("dialog_agent_service.app.get_user_contexts", return_value=campaign_user_contexts)
    await handle_request(campaign_req)