from __future__ import annotations

import logging
from dialog_agent_service.conversational_agent.conversation_parser import Conversation
from dialog_agent_service.conversational_agent.task_handlers.handle_answer_product_questions import handle_answer_product_questions


logger = logging.getLogger()


def test_handle_answer_product_questions(predict_fn):
    convo = Conversation(docs=[('inbound', 'Is GOATFUEL 0 calorie?')])
    vendor = 'G.O.A.T Fuel'
    response = handle_answer_product_questions(
        predict_fn=predict_fn, merchant_id='29', cnv_obj=convo, vendor=vendor)
    logger.info(response)
    assert response is not None
