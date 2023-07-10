import ast
import os
import re
import timeit
from typing import List
import json
import logging
from textwrap import dedent
import openai
from .conversation_parser import Conversation, Turn
from dialog_agent_service.constants import OpenAIModel, DATA_LIMIT
from dialog_agent_service.das_exceptions import LLMOutputFormatIncorrect, LLMOutputValidationFailed, LLMRequestFailed


TEMPERATURE = 0.0
HANDOFF_TO_CX = r"HANDOFF TO CX|OpenAI|language model|I don't have that information|I didn't understand|doctor|medical|email|website|((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*|^\S+@\S+\.\S+$"
NO_DATA = r"insufficient info|no (sufficient )?info|not provide info"

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


def answer_with_prompt(cnv_obj: Conversation, prompt, model=None, turns=10, json_output=False):
    if model is None:
        model = OpenAIModel.GPT35OLD  # Default Model
    if json_output:
        # messages = [{"role": "user", "content": f"Conversation: ```{cnv_obj}```\n{prompt}"}]
        messages = conv_to_chatgpt_format(cnv_obj, k=turns)
        messages.append({"role": "system", "content": prompt})
    else:
        messages = [
            {"role": "system", "content": prompt}
        ] + conv_to_chatgpt_format(cnv_obj, turns)
    logger.debug(f"LLM REQUEST - Model: {model}, Temp: {TEMPERATURE}, Prompt: {messages}")
    start_time = timeit.default_timer()
    try:
        resp = openai.ChatCompletion.create(
            model=model,
            temperature=TEMPERATURE,
            messages=messages,
        )
    except Exception as e:
        logger.exception(f'LLM Request Failed: {e}')
        raise LLMRequestFailed from e

    duration = timeit.default_timer() - start_time
    logger.info(f"LLM REQUEST - Model: {model}: request time: {duration}")
    llm_response = resp.choices[0].message.content

    if json_output:
        try:
            st = llm_response.find(r'({)?"RESPONSE"') or 0
            en = llm_response.find('}', st) if st else len(llm_response) - 1
            logger.info(f"LLM Response: {llm_response}")
            response_dict = json.loads(llm_response[st:en + 1])
            if response_dict.get("ANSWER_POSSIBLE", True) and response_dict.get("CONTAINED", True):
                llm_response = response_dict["RESPONSE"]
            else:
                llm_response = "HANDOFF TO CX due to in-context guardrail"
        except Exception as e:
            logger.exception(f"LLM Output not formatted as expected: {llm_response}")
            raise LLMOutputFormatIncorrect from e

    return validate_response(model, llm_response)


def generate_cart_mentions(cnv_obj: Conversation, current_cart: List, products: List):
    context = "\n".join([str(t) for t in cnv_obj.turns[:-2]]) if cnv_obj.n_turns > 2 else ""
    last_seller_utt = str(cnv_obj.turns[-2]) if cnv_obj.n_turns > 1 else ""

    prompt = f"""
A Cart consists of the products that the buyer wants to purchase. To create the cart go through a conversation  and create a list of tuples of product X quantity, e.g. [("product1", quantity1), ("product2", quantity2), ...] where products are the names of products that the buyer has asked to buy or add to their cart and quantity is an integer. 
The product names have to come from a give list of products. The buyer does not always provide the exact product name, so you have to infer the product name from the list of product names. If you cannot, with complete certainty, infer a unique product name because there are multiple products from the list that are likely to be a match, you can output them all separated by delimiter "||". Unless you are absolutely sure, do not match to a product name and err on the side of generating multiple product names. Also, make sure you generate all likely product names.
Below are a few examples to illustrate how cart is built. Follow them closely when building the cart for the conversation given at the end.
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
Here is the list of all possible products: {json.dumps(products)}
BEGIN CONVERSATION
{context}
Cart: {current_cart}
{last_seller_utt}
{cnv_obj.turns[-1]}
END CONVERSATION
Cart:"""
    messages = [
        {"role": "user", "content": prompt}
    ]
    try:
        resp = openai.ChatCompletion.create(
            model=OpenAIModel.GPT35OLD,
            temperature=TEMPERATURE,
            messages=messages
        )
    except Exception as e:
        logger.exception(f"LLM Request failed for Cart Creation: {e}")
        raise LLMRequestFailed from e
    llm_response = resp.choices[0].message.content
    try:
        st = llm_response.find('[')
        en = llm_response.find(']', st)
        return ast.literal_eval(llm_response[st:en+1])
    except Exception as e:
        logger.exception(f"LLM Cart Output not formatted correctly: {e}")
        raise LLMOutputFormatIncorrect(f'failed to parse {llm_response}') from e


def validate_response(model, llm_response):
    if re.search(HANDOFF_TO_CX, llm_response):
        logger.warning(f"LLM Validation failed for response: {llm_response}. Handing off to CX")
        raise LLMOutputValidationFailed(f"Model: {model}. LLM Validation failed for response: {llm_response}")
    return {'handoff': False, 'response': llm_response}


def llm_retrieval(query: str, data: str) -> str:
    """
    Query the openai model to cite passages in response to query.
    Args:
         query: the query string
         data: the retrieved documents
    Returns:
        the relevant passage
    Raises
        LLMRequestFailed if openai request fails
        LLMOutputValidationFailed if the model determins there's no sufficient info in the data
    """
    messages = retrieval_prompt(query, data)
    try:
        resp = openai.ChatCompletion.create(
            model=OpenAIModel.GPT35OLD,
            temperature=TEMPERATURE,
            messages=messages  # for now, no convo context
        )
    except Exception as e:
        logger.exception(f"LLM Request failed for Cart Creation: {e}")
        raise LLMRequestFailed from e

    llm_response = resp.choices[0].message.content
    if re.search(pattern=NO_DATA, string=llm_response, flags=re.I):
        raise LLMOutputValidationFailed(f"No sufficient data to answer user query: {llm_response}")
    logger.info(f"retrieved passage: {llm_response}")
    return llm_response


def retrieval_prompt(query, data):
    """
    helper function to prep the openai prompt for llm_retrieval
    """
    citation_prompt = dedent("""
    You will be provided with a document delimited by triple quotes and a question. 
    Your task is to answer the question using only the provided document and to cite the passage(s) of the document used to answer the question. 
    If the document does not contain the information needed to answer any part of a question then simply write: "Insufficient information." 
    If an answer to the question is provided, it must be annotated with a citation. 
    Use the following format for to cite relevant passages {{"citation": …}}.
    """).strip()
    messages = [
        {'role': 'system', 'content': citation_prompt},
        {"role": "user", "content": f"\"\"\"{data[:DATA_LIMIT]}\"\"\"\nQuestion: {query}"}
    ]
    return messages