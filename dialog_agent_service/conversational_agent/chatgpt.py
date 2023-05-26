import ast
import os
import re
import timeit
from typing import List
import logging
import openai
from .conversation_parser import Conversation, Turn
from dialog_agent_service.constants import OpenAIModel

TEMPERATURE = 0.0
HANDOFF_TO_CX = 'HANDOFF TO CX|OpenAI|language model|I\'m sorry, but I don\'t have that information on hand'

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
    start_time = timeit.default_timer()
    resp = openai.ChatCompletion.create(
        model=model,
        temperature=TEMPERATURE,
        messages=messages
    )
    duration = timeit.default_timer() - start_time
    logger.info(f"LLM REQUEST - Model: {model}: request time: {duration}")
    llm_response = resp.choices[0].message.content
    return validate_response(model, llm_response)


def generate_cart_mentions(cnv_obj: Conversation, current_cart: List, products: List):
    context = "\n".join([str(t) for t in cnv_obj.turns[:-2]]) if cnv_obj.n_turns > 2 else ""
    last_seller_utt = str(cnv_obj.turns[-2]) if cnv_obj.n_turns > 1 else ""

    prompt = f"""
BEGIN EXAMPLES
List of products: ["Wizard Shampoo - 8 oz", "Wizard Shampoo - 16 oz", "Wizard Conditioner - 8 oz", "Wizard Conditioner - 16 oz", "Vanilla Ice Cream - 12 pk", "Chocolate Ice Cream - 12 pk"]
Buyer: how much does wizard shampoo cost?
Cart: []
Seller: $12
Buyer: Can you add wizard shampoo and conditioner to my cart?
Cart: [("Wizard Shampoo - 8 oz || Wizard Shampoo - 16 oz", 1), ("Wizard Conditioner - 8 oz || Wizard Conditioner - 16 oz", 1)].
Seller: 8 oz or 16 oz?
Buyer: 8 oz
Cart: [("Wizard Shampoo - 8 oz", 1), ("Wizard Conditioner - 8 oz", 1)]
Seller: Done! Anything else?
Buyer: Add two
Cart: [("Wizard Shampoo - 8 oz", 2), ("Wizard Conditioner - 8 oz", 2)] 
Seller: Of course! would you like to checkout now?
Buyer: two of the ice creams?
Cart: [("Wizard Shampoo - 8 oz", 2), ("Wizard Conditioner - 8 oz", 2), ("Vanilla Ice Cream - 12 pk || Chocolate Ice Cream - 12 pk", 2)]
Seller: Did you want chocolate or vanilla?
Buyer: both
Cart: [("Wizard Shampoo - 8 oz", 2), ("Wizard Conditioner - 8 oz", 2), ("Vanilla Ice Cream - 12 pk", 2), ("Chocolate Ice Cream - 12 pk", 2)]
Seller: Sure. Are you ready to checkout now?
Buyer: Actually remove the shampoo and conditioner.
Cart: [("Vanilla Ice Cream - 12 pk", 2), ("Chocolate Ice Cream - 12 pk", 2)]]
Seller: done. Your cart has been updated.
Buyer: just one of each please.
Cart: ("Vanilla Ice Cream - 12 pk", 1), ("Chocolate Ice Cream - 12 pk", 1)] 
END EXAMPLES
A Cart consists of the products that the buyer wants to purchase. To create the cart go through the conversation below and create a create a list of tuples of product X quantity, e.g. [("product1", quantity1), ("product2", quantity2), ...] where products are the names of products that the buyer has asked to buy or add to their cart and quantity is an integer. 
The product names have to come from a give list of products. The buyer does not always provide the exact product name, so you have to infer the product name from the list below based on their utterance. If there are multiple products from the list that are equally likely to be a match, you can output them all separated by delimiter "||".
Here is the list of all possible products: {products}
BEGIN CONVERSATION
{context}
Cart: {current_cart}
{last_seller_utt}
{cnv_obj.turns[-1]}
Cart:"""
    messages = [
        {"role": "user", "content": prompt}
    ]
    resp = openai.ChatCompletion.create(
        model=OpenAIModel.GPT35,
        temperature=TEMPERATURE,
        messages=messages
    )
    llm_response = resp.choices[0].message.content
    st = llm_response.find('[')
    en = llm_response.find(']', st)
    return ast.literal_eval(llm_response[st:en+1])


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