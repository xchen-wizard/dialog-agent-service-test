import os
import logging
import pytest

from dialog_agent_service.conversational_agent.conversation_utils import run_inference
logger = logging.getLogger()

ENDPOINT_ID = os.getenv('T5_VERTEX_AI_ENDPOINT_ID')
PROJECT_ID = os.getenv('VERTEX_AI_PROJECT_ID')


@pytest.mark.asyncio
async def test_answer_product_question():
    merchant_id = "29"
    vendor_name = "G.O.A.T Fuel"
    docs = [
        ('inbound', 'How much is blueberry?')
    ]
    task_routing_config = {}
    expected_response = {
        'task': 'AnswerProductQuestions',
        'response': 'Blueberry Lemonade is priced at $35.99 for a 12 pack.',
        'suggested': True,
    }

    response = await run_inference(docs, vendor_name, merchant_id, project_id=PROJECT_ID, endpoint_id=ENDPOINT_ID, task_routing_config=task_routing_config)
    assert response == expected_response


@pytest.mark.asyncio
async def test_answer_miscellaneous_question():
    merchant_id = "29"
    vendor_name = "G.O.A.T Fuel"
    docs = [
        ('inbound', 'How much do you charge for shipping and how long does it usually take?')
    ]
    task_routing_config = {}
    expected_response = {
        'task': 'AnswerMiscellaneousQuestions',
        'response': 'Thanks for your question! Shipping is always FREE and orders take approximately 3-5 business days to arrive.',
        'suggested': True
    }

    response = await run_inference(docs, vendor_name, merchant_id, project_id=PROJECT_ID, endpoint_id=ENDPOINT_ID, task_routing_config=task_routing_config)
    assert response == expected_response


@pytest.mark.asyncio
async def test_create_or_update_order_cart():
    merchant_id = "29"
    vendor_name = "G.O.A.T Fuel"
    docs = [
        ('inbound', 'Can you tell me more about the Mango Passion Fruit?'),
        ('outbound', '''
        Mango Passion Fruit is a 12 pack of G.O.A.T. Fuel with powerful, tropical flavors that taste like a vacation. It is priced at $35.99 and has a subscription option with a 10% discount. The subscription ID is 254332, and the shipping interval is every 30 days. The product is not subscription-only and falls under the Google product category 422.
        '''),
        ('inbound', ' Can I add Acai Mixed Berry')
    ]
    task_routing_config = {}
    response = await run_inference(docs, vendor_name, merchant_id, project_id=PROJECT_ID, endpoint_id=ENDPOINT_ID,
                               task_routing_config=task_routing_config)
    assert response['cart'] == [('Acai Mixed Berry - 12 Pack', 1)]


@pytest.mark.asyncio
async def test_recommend_product():
    merchant_id = "29"
    vendor_name = "G.O.A.T Fuel"
    docs = [
        ("inbound", "What do you recommend for someone with a sweet tooth?")
    ]
    task_routing_config = {}
    response = await run_inference(docs, vendor_name, merchant_id, project_id=PROJECT_ID, endpoint_id=ENDPOINT_ID,
                               task_routing_config=task_routing_config)
    assert len(response['response']) > 0
