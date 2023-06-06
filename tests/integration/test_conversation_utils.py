from dialog_agent_service.conversational_agent.conversation_utils import get_past_k_turns
import logging
import pytest

logger = logging.getLogger()


@pytest.mark.asyncio
async def test_get_past_k_turns():
    docs, vendor_name, clear_history = await get_past_k_turns(
        user_id=198330,
        service_channel_id=50,
        vendor_id='29',
        k=12
    )
    assert len(docs) <= 12
    assert vendor_name == 'G.O.A.T. Fuel'
    assert not clear_history