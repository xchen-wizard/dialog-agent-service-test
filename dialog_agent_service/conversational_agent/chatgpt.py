import os
import re
from textwrap import dedent
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
    return [turn_to_chatgpt_format(turn) for turn in cnv_obj.turns[-k: ]]


def answer_with_prompt(cnv_obj: Conversation, prompt):
    messages = [
        {"role": "system", "content": prompt}
    ] + conv_to_chatgpt_format(cnv_obj, 5)
    logger.debug(f"LLM REQUEST - Model: {MODEL}, Temp: {TEMPERATURE}, Prompt: {messages}")
    resp = openai.ChatCompletion.create(
        model=MODEL,
        temperature=TEMPERATURE,
        messages=messages
    )
    llm_response = resp.choices[0].message.content
    return validate_response(llm_response)


def product_qa(cnv_obj: Conversation, data: str, vendor: str):
    prompt = dedent(f"""
    You are a helpful salesperson for {vendor} and are trying to answer questions about products.
    Use the following "Product Data" delimited by ``` to answer the Customer's question in a concise manner.
    If the question can't be answered based on the "Product Data" alone, respond only with "HANDOFF TO CX".
    Limit responses to no more than 50 words.
    
    Product Data:
    ```{data}```
    """).strip('\n')
    return answer_with_prompt(cnv_obj, prompt)


def merchant_qa(cnv_obj: Conversation, data: str, vendor: str):
    prompt = dedent(f"""
    You are a kind and helpful e-commerce customer support agent that works for {vendor}.
    
    Your task is to help find the answer to the Customer's question using these steps:
    1. Use each of the following POLICIES delimited by ``` to answer the Customer's question in a concise manner.
    2. If the question can't be answered based on the POLICIES alone, response "HANDOFF TO CX".
    3. Use the provided INSTRUCTIONS sections to further refine your answer.
    4. Limit the answer to no more than 50 words.

    INSTRUCTIONS:
    - if you are responding to the first Customer message, respond with a greeting like "Hi there!" or "Thanks for your question!" before answering the question. Otherwise if we're in the middle of a conversation answer the question directly.
    - unless the Customer indicates otherwise, we should assume they are asking about shipping to the USA
        
    POLICIES: 
    ```{data}```
    """).strip('\n')
    return answer_with_prompt(cnv_obj, prompt)


def recommend(cnv_obj: Conversation, data: str, vendor: str):
    prompt = dedent(f"""
    You are a salesperson for {vendor} 
    Use the following "Context" delimited by ``` to make a recommendation for a product that matches the Customer's requirements.
    If there is not enough information in the "Context" to make a recommendation, feel free to ask the Customer for more information.
    Limit responses to no more than 50 words. 
    
    Context:
    ```{data}```
    """).strip('\n')
    return answer_with_prompt(cnv_obj, prompt)

def validate_response(llm_response):
    resp = {}
    logger.info(f"LLM Response: {llm_response}")

    if re.search(HANDOFF_TO_CX, llm_response):
        logger.warn("LLM Failed Validation: handing off to CX")
        resp = {'handoff': True, 'response': None}
    else:
        resp = {'handoff': False, 'response': llm_response}

    return resp