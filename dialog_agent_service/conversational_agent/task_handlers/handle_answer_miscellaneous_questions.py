import json
from dialog_agent_service.retrievers.merchant_retriever import merchant_semantic_search
from .default_handler import default_handler
from ..chatgpt import answer_with_prompt
from textwrap import dedent
import logging
from dialog_agent_service.constants import OpenAIModel, DATA_LIMIT
from dialog_agent_service.utils.utils import handler_to_task_name
from dialog_agent_service.das_exceptions import RetrieverFailure
from dialog_agent_service.conversational_agent.chatgpt import llm_retrieval
logger = logging.getLogger(__name__)
TURNS = 4


def gen_prompt(vendor, data):
    return dedent(f"""
    Read the conversation above and then do the following step-by-step.
    DATA: \"\"\"{data[:DATA_LIMIT]}\"\"\"
    Answer the buyer's question in Conversation using only the DATA section delimited by triple quotes. Call it RESPONSE. Follow the following guidelines when crafting your response:
        - Answer as a kind and empathetic AI agent built by {vendor} and Wizard
        - End your answer with a short follow up question that continues the conversation. Vary follow-up questions each time by offering assistance, asking about the customer's needs or preferences, or just letting the customer know you're here to help.
        - Keep your answer under 50 words.
    RESPONSE:""").strip()


def handle_answer_miscellaneous_questions(cnv_obj=None, merchant_id=None, vendor=None, current_cart=None, llm_model=None, **kwargs):
    task = handler_to_task_name()
    query = cnv_obj.turns[-1].formatted_text
    context = merchant_semantic_search(merchant_id, query)
    if not context:
        logger.warning("Can't retrieve context. Handing off")
        raise RetrieverFailure
    context = f"Cart: {serialize_cart_for_prompt(current_cart)}" + "\n" + context
    logger.debug(f"Prompt Context: {context}")
    prompt = llm_retrieval(query, context) and gen_prompt(vendor, context)
    return {'task': task} | answer_with_prompt(cnv_obj, prompt, model=llm_model, turns=TURNS, json_output=True)


def serialize_cart_for_prompt(cart):
    return json.dumps(
        {
            'items': [{'name': lineItem['productName'] + ' - ' + lineItem['variantName'], 'price': lineItem['currentPrice'], 'quantity': lineItem['quantity']} for lineItem in cart.get('lineItems', [])]
        } | {
            k: cart[k] if cart[k] is not None else "Not Available"
            for k in ["cartDiscountsTotal", "itemsTotal", "taxTotal", "totalPrice", "shippingDiscountsTotal", "subtotal", "shippingSavings"]
            if k in cart
        }
    )
