import ast
import json
import os
import re
from typing import List
import logging
import openai
from .conversation_parser import Conversation, Turn
from dialog_agent_service.constants import OpenAIModel

TEMPERATURE = 0.2
HANDOFF_TO_CX = 'HANDOFF TO CX|OpenAI|language model'

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


def answer_with_prompt(cnv_obj: Conversation, prompt, model=OpenAIModel.GPT35, turns=10):
    messages = [
        {"role": "system", "content": prompt}
    ] + conv_to_chatgpt_format(cnv_obj, turns)
    logger.debug(f"LLM REQUEST - Model: {model}, Temp: {TEMPERATURE}, Prompt: {messages}")
    resp = openai.ChatCompletion.create(
        model=model,
        temperature=TEMPERATURE,
        messages=messages
    )
    llm_response = resp.choices[0].message.content
    return validate_response(model, llm_response)


def generate_cart_mentions(cnv_obj: Conversation, current_cart: List, products: List):
    context = "\n".join([str(t) for t in cnv_obj.turns[:-2]]) if cnv_obj.n_turns > 2 else ""
    last_seller_utt = str(cnv_obj.turns[-2]) if cnv_obj.n_turns > 1 else ""
    current_cart_json = json.dumps([{"product": t[0], "quantity": t[1]} for t in current_cart])
    prompt = f"""
BEGIN EXAMPLES
List of products: ["Wizard Shampoo - 8 oz", "Wizard Shampoo - 16 oz", "Wizard Conditioner - 8 oz", "Wizard Conditioner - 16 oz", "Vanilla Ice Cream - 12 pk"]
Buyer: how much does wizard shampoo cost?
Cart: []
Seller: $12
Buyer: Can you add wizard conditioner to my cart?
Cart: [{{"product_mention": "wizard shampoo", "product": "Wizard Conditioner - 8 oz || Wizard Conditioner - 16 oz", "quantity": 1}}].
Seller: 8 oz or 16 oz?
Buyer: 8 oz
Cart: [{{"product_mention": "wizard shampoo 8 oz", "product": "Wizard Conditioner - 8 oz", "quantity": 1}}]
Seller: Done! Anything else?
Buyer: Add two
Cart: [{{"product_mention": "wizard shampoo 8 oz", "product": "Wizard Conditioner - 8 oz", "quantity": 2}}]
Seller: Of course! would you like to checkout now?
Buyer: two of the ice cream?
Cart: [{{"product_mention": "wizard shampoo 8 oz", "product": "Wizard Conditioner - 8 oz", "quantity": 2}}, {{"product_mention": "ice cream", "product": "Vanilla Ice Cream - 12 pk", "quantity": 2}}].
Seller: Sure. Are you ready to checkout now?
Buyer: Actually make that one. and remove the conditioner.
Cart: [{{"product_mention": "ice cream", "product": "Vanilal Ice Cream - 12 pk", "quantity": 1}}]
Seller: done. Your cart has been updated.
Buyer: i will get the shampoo
Cart: [{{"product_mention": "ice cream", "product": "Vanilla Ice Cream - 12 pk", "quantity": 1}}, {{"product_mention": "shampoo", "product": "Wizard Shampoo - 8 oz || Wizard Shampoo - 16 oz", "quantity": 1}}].
END EXAMPLES
A Cart consists of the products that the buyer wants to purchase. To create the cart go through the conversation below
 and create a list of dictionaries with keys "product_mention", "product" and "quantity" where:
 - product_mention is the phrase used by the buyer to refer to the product. This may not be same as the product name
 - product is the name of the product that the buyer has asked to buy which has to come from the list provided below.The buyer does not always provide the exact product name, so you have to infer the product name from the list below based on their utterance. If there are multiple products from the list that are equally likely to be a match, you can output them all separated by delimiter "||".
 - quantity is an integer.
Here is the list of all possible products: {products}
BEGIN CONVERSATION
{context}
Cart: {current_cart_json}
{last_seller_utt}
{cnv_obj.turns[-1]}
Cart:"""
    messages = [
        {"role": "user", "content": prompt}
    ]
    resp = openai.ChatCompletion.create(
        model=OpenAIModel.GPT4,
        messages=messages
    )
    llm_response = resp.choices[0].message.content
    st = llm_response.find('[')
    en = llm_response.find(']', st)
    cart_json = ast.literal_eval(llm_response[st:en+1])
    return cart_json


def validate_response(model, llm_response):
    resp = {}
    logger.info(f"LLM Response: {llm_response}")

    if re.search(HANDOFF_TO_CX, llm_response):
        logger.warning(f"LLM Validation failed for response: {llm_response}. Handing off to CX")
        resp = {
            'handoff': True,
            'response': f"Model: {model}, Issue: LLM Validation failed for response: {llm_response}"
        }
    else:
        resp = {'handoff': False, 'response': llm_response}

    return resp
