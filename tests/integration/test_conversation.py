import os
import logging
import pytest
from fuzzywuzzy import fuzz
from dialog_agent_service.conversational_agent.conversation_utils import run_inference
logger = logging.getLogger()

ENDPOINT_ID = os.getenv('T5_VERTEX_AI_ENDPOINT_ID')
PROJECT_ID = os.getenv('VERTEX_AI_PROJECT_ID')

HANDOFF_TESTS = [
    "Is there any scientific research or clinical trials conducted with G.O.A.T. Fuel products to measure their effectiveness?",
    "What are the manufacturing processes and quality measures in place to ensure the consistency and efficacy of G.O.A.T. Fuel products?",
    "How long does it take for the effects of G.O.A.T. Fuel to set in after consumption?",
    "Can customers customize their own '12 Pack' with a mix of different flavors?",
    "Are G.O.A.T. Fuel products dairy-free or gluten-free?",
    "I took the product past the short-sale date without opening it! Is it still safe to take?",
    "Hey, I'd like to order a surprise custom-pack for my cousin who's a fitness freak. Do you provide birthday packaging?",
    "Do I need to follow any specific storage instructions for your products?",
    "Are gift receipt options available?",
    "How do I buy over text?",
    "Are there specific guidelines for sending water/beverage intake for customers who regularly consume G.O.A.T. fuel to ensure proper bodily hydration?",
    "Is there a time limit for canceling an order?",
]

@pytest.mark.asyncio
async def test_answer_product_question():
    merchant_id = "29"
    vendor_name = "G.O.A.T Fuel"
    docs = [
        ('inbound', 'How much is blueberry lemonade?')
    ]
    task_routing_config = {}
    expected_response = {
        'task': 'AnswerProductQuestions',
        'response': 'The price for our Blueberry Lemonade Energy Drink 12-pack is $35.99. Would you like to add it to your cart?',
        'suggested': True,
        'handoff': False
    }

    response = await run_inference(docs, vendor_name, merchant_id, project_id=PROJECT_ID, endpoint_id=ENDPOINT_ID, task_routing_config=task_routing_config)
    assert fuzz.token_set_ratio(response['response'], expected_response['response']) > 70


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
        'response': "Hey there! Good news - shipping is always FREE at G.O.A.T Fuel orders! It typically takes around 3-5 business days for your order to arrive. Let me know if you'd like to start an order or if you have any other questions! 😊",
        'suggested': True
    }

    response = await run_inference(docs, vendor_name, merchant_id, project_id=PROJECT_ID, endpoint_id=ENDPOINT_ID, task_routing_config=task_routing_config)
    assert response['task'] == expected_response['task']
    assert fuzz.token_set_ratio(response['response'], expected_response['response']) > 70


@pytest.mark.asyncio
async def test_create_or_update_order_cart():
    merchant_id = "29"
    vendor_name = "G.O.A.T Fuel"
    docs = [
        ('inbound', 'Can you tell me more about the Mango Passion Fruit?'),
        ('outbound', '''
        Mango Passion Fruit is a 12 pack of G.O.A.T. Fuel with powerful, tropical flavors that taste like a vacation. It is priced at $35.99 and has a subscription option with a 10% discount. The subscription ID is 254332, and the shipping interval is every 30 days. The product is not subscription-only and falls under the Google product category 422.
        '''),
        ('inbound', 'Can I add Acai Mixed Berry')
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


@pytest.mark.asyncio
async def test_none():
    merchant_id = "29"
    vendor_name = "G.O.A.T Fuel"
    docs = [
        ("inbound", "hello?")
    ]
    task_routing_config = {"None": {"responseType": "automated"}}
    response = await run_inference(docs, vendor_name, merchant_id, project_id=PROJECT_ID, endpoint_id=ENDPOINT_ID,
                               task_routing_config=task_routing_config)
    assert response['task'] == 'None'


@pytest.mark.asyncio
async def test_handoffs():
    merchant_id = "29"
    vendor_name = "G.O.A.T Fuel"
    success = ct = 0
    for utt in HANDOFF_TESTS:
        docs = [("inbound", utt)]
        response = await run_inference(docs, vendor_name, merchant_id, project_id=PROJECT_ID, endpoint_id=ENDPOINT_ID,
                                       task_routing_config={})
        if response["handoff"]:
            success += 1
        else:
            print(f"{utt} failed to handoff")
        ct += 1
    assert success >= ct*0.66 #TODO: we should improve threshold
