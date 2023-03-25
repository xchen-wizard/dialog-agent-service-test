from dialog_agent_service.conversational_agent.conversation_utils import encode_sentence
import logging

logger = logging.getLogger()

def test_encode_sentence():
    resp = encode_sentence(
        query='this is a test',
        project_id='prod-us-333918',
        endpoint_id='1561716274'
    )
    logger.info(resp)
    assert isinstance(resp, list)
    assert len(resp) == 768