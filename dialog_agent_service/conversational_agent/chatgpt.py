import ast
import os
import re
from typing import List
import logging
import openai
from .conversation_parser import Conversation, Turn

MODEL = "gpt-3.5-turbo"
TEMPERATURE = 0.2
HANDOFF_TO_CX = 'HANDOFF TO CX|OpenAI|AI language model'

logger = logging.getLogger(__name__)
openai.api_key = os.getenv('OPENAI_API_KEY')

def turn_to_chatgpt_format(turn: Turn):
    return {
        "role": "user" if turn.direction == 'inbound' else "assistant",
        "content": turn.formatted_text
    }


def conv_to_chatgpt_format(cnv_obj: Conversation, k):
    """
    exports last k turn to chatgpt format
    :param cnv_obj: Conversation
    :param k: k turns to include
    :return: list of dict with role/content
    """
    return [turn_to_chatgpt_format(turn) for turn in cnv_obj.turns[-k:]]


def answer_with_prompt(cnv_obj: Conversation, prompt, turns=10):
    messages = [
        {"role": "system", "content": prompt}
    ] + conv_to_chatgpt_format(cnv_obj, turns)
    logger.debug(f"LLM REQUEST - Model: {MODEL}, Temp: {TEMPERATURE}, Prompt: {messages}")
    resp = openai.ChatCompletion.create(
        model=MODEL,
        temperature=TEMPERATURE,
        messages=messages
    )
    llm_response = resp.choices[0].message.content
    return validate_response(llm_response)


def generate_cart_mentions(cnv_obj: Conversation, current_cart: List):
    context = "\n".join([str(t) for t in cnv_obj.turns[:-2]]) if cnv_obj.n_turns > 2 else ""
    last_seller_utt = str(cnv_obj.turns[-2]) if cnv_obj.n_turns > 1 else ""

    prompt = f"""
BEGIN EXAMPLES
Buyer: how does wizard shampoo cost?
Buyer's Cart: []
Seller: $12
Buyer: Can you add wizard conditioner to my cart?
Buyer's Cart: [("wizard conditioner", 1)]
Seller: Done! Anything else?
Buyer: Also add two gummy bears?
Buyer's Cart: [("wizard conditioner", 1), ("gummy bears", 2)]
Seller: Sure. Are you ready to checkout now?
Buyer: Actually make that one. and remove the conditioner.
Buyer's Cart: [("gummy bears", 1)] 
END EXAMPLES
A buyer's cart consists of the products that they want to purchase. To create a buyer's cart go through the conversation above
 and create a list of tuples of product X quantity, e.g. [("product1", quantity1), ("product2", quantity2), ...] where products are the products that the buyer has asked to buy or add to their cart and quantity is an integer.
    {context}
    Buyer's Cart: {current_cart}
    {last_seller_utt}
    {cnv_obj.turns[-1]}
    Buyer's Cart: 
    """
    messages = [
        {"role": "user", "content": prompt}
    ]
    resp = openai.ChatCompletion.create(
        model=MODEL,
        temperature=TEMPERATURE,
        messages=messages
    )
    llm_response = resp.choices[0].message.content
    st = llm_response.find('[')
    en = llm_response.find(']', st)
    return ast.literal_eval(llm_response[st:en+1])


def validate_response(llm_response):
    resp = {}
    logger.info(f"LLM Response: {llm_response}")

    if re.search(HANDOFF_TO_CX, llm_response):
        logger.warning(f"LLM Validation failed for response: {llm_response}. Handing off to CX")
        resp = {'handoff': True, 'response': None}
    else:
        resp = {'handoff': False, 'response': llm_response}

    return resp