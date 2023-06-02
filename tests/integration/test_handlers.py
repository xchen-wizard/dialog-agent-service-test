from __future__ import annotations

import logging
import os

import pytest

from dialog_agent_service.app_utils import predict_custom_trained_model_sample
from dialog_agent_service.conversational_agent.conversation_parser import Conversation
from dialog_agent_service.conversational_agent.task_handlers.handle_answer_product_questions import handle_answer_product_questions


logger = logging.getLogger()


@pytest.fixture
def predict_fn():
    def predict_func(text: str | list[str]):
        if isinstance(text, str):
            text = [text]
        responses = predict_custom_trained_model_sample(
            project=os.getenv('VERTEX_AI_PROJECT_ID'),
            endpoint_id=os.getenv('T5_VERTEX_AI_ENDPOINT_ID'),
            location=os.getenv('VERTEX_AI_LOCATION', 'us-central1'),
            api_endpoint=os.getenv(
                'VERTEX_AI_ENDPOINT',
                'us-central1-aiplatform.googleapis.com',
            ),
            instances=[{'data': {'context': t}} for t in text],
        )
        return responses
    return predict_func


def test_handle_answer_product_questions(predict_fn):
    convo = Conversation(docs=[('inbound', 'Is GOATFUEL 0 calorie?')])
    vendor = 'G.O.A.T Fuel'
    response = handle_answer_product_questions(
        predict_fn=predict_fn, merchant_id='29', cnv_obj=convo, vendor=vendor)
    logger.info(response)
    assert response is not None
