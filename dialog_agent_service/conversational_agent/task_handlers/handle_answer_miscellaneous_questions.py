import json
from dialog_agent_service.retrievers.merchant_retriever import merchant_semantic_search
from .default_handler import default_handler
from ..chatgpt import answer_with_prompt
from textwrap import dedent
import logging
from dialog_agent_service.constants import OpenAIModel
from dialog_agent_service.utils.utils import handler_to_task_name
from dialog_agent_service.das_exceptions import RetrieverFailure
logger = logging.getLogger(__name__)
TURNS = 4


def gen_prompt(vendor, data):
    return dedent(f"""
Read the conversation above and then do the following step-by-step.
1. Go through the DATA section below and decide whether there is enough information in DATA to answer buyer's question satisfactorily with a high degree of certainty. Call this ANSWER_POSSIBLE.
DATA
```{data}```
2. Answer the buyer's question using only the DATA section. Call it RESPONSE. Follow the following guidelines when crafting your response:
    - Answer as a kind and empathetic AI agent built by {vendor} and Wizard
    - Unless the Customer indicates otherwise, assume they are asking about shipping to the USA.
    - End your answer with a short follow up question that continues the conversation. Vary follow-up questions each time by checking if the customer wants to start an order, offering assistance, asking about the customer's needs or preferences, or just letting the customer know you're here to help.
    - Keep your answer under 50 words.
3. Set CONTAINED to true if every information present in RESPONSE is also present in DATA.
4. Output a json in the following format: {{"ANSWER_POSSIBLE": true/false, "RESPONSE": "...", "CONTAINED": true/false}}
Output:""").strip('\n')


def handle_answer_miscellaneous_questions(cnv_obj=None, merchant_id=None, vendor=None, current_cart=None, **kwargs):
    task = handler_to_task_name()
    query = cnv_obj.turns[-1].formatted_text
    context = merchant_semantic_search(merchant_id, query)
    if not context:
        logger.warning("Can't retrieve context. Handing off")
        raise RetrieverFailure
    context = f"Cart: {serialize_cart_for_prompt(current_cart)}" + "\n" + context
    logger.debug(f"Prompt Context: {context}")
    return {'task': task} | answer_with_prompt(cnv_obj, gen_prompt(vendor, context), model=OpenAIModel.GPT4, turns=TURNS, json_output=True)


def serialize_cart_for_prompt(cart):
    return json.dumps(
        {
            'items': [{'name': lineItem['productName'] + ' - ' + lineItem['variantName'], 'price': lineItem['currentPrice'], 'quantity': lineItem['quantity']} for lineItem in cart.get('lineItems', [])]
        } | {
            k: cart[k]
            for k in ["cartDiscountsTotal", "itemsTotal", "taxTotal", "totalPrice", "shippingDiscountsTotal", "subtotal", "shippingSavings"]
            if k in cart
        }
    )
