import pytest

from dialog_agent_service.conversational_agent.infer import T5InferenceService
import logging


logger = logging.getLogger()


@pytest.fixture
def inference_service():
    return T5InferenceService("../test_data")


def test_transfer_to_agent(inference_service, predict_fn):
    tests = ["I need to speak to a real person right now. Your automated system is not helping me",
     "This is ridiculous. I've been texting back and forth for hours. Can I please talk to a human?.",
     "I'm tired of getting automated responses. I want to speak to a real person who can help me with my issue.",
     "Your text service is not working. I need to talk to a human to resolve my problem.",
     "I'm frustrated with this text service. I demand to speak to a human representative immediately.",
     "Can you just put me in touch with a real person",
     "I don’t want to talk to a bot anymore. How do I get real help"]
    for test in tests:
        docs = [('inbound', test)]
        ret_dict = inference_service.infer(docs, "GOATFUEL", '29', predict_fn)
        logger.info(ret_dict)
        assert ret_dict.get('task') == 'TransferToAgent'


