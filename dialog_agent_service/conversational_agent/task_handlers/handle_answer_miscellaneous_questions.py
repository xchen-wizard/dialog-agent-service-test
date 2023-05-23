from dialog_agent_service.retrievers.merchant_retriever import merchant_semantic_search
from .default_handler import default_handler
from ..chatgpt import answer_with_prompt
from textwrap import dedent
import logging
from dialog_agent_service.constants import OpenAIModel
logger = logging.getLogger(__name__)
TURNS = 4


def gen_prompt(vendor, data):
    return dedent(f"""
    You are a kind and helpful e-commerce customer support agent that works for {vendor}.
    
    Your task is to help find the answer to the Customer's question using these steps:
    1. Use each of the following POLICIES delimited by ``` to answer the Customer's question in a concise manner.
    2. If the question can't be answered based on the POLICIES alone, response "HANDOFF TO CX".
    3. Use the provided INSTRUCTIONS sections to further refine your answer.
    4. Limit the answer to no more than 50 words.

    INSTRUCTIONS:
    - if you are responding to the first Customer message, respond with a greeting like "Hi there!" or "Thanks for your question!" before answering the question. Otherwise if we're in the middle of a conversation answer the question directly.
    - unless the Customer indicates otherwise, we should assume they are asking about shipping to the USA
    - if the question is about promotions or discounts, then reply only with "HANDOFF TO CX".
        
    POLICIES: 
    ```{data}```
    """).strip('\n')


def handle_answer_miscellaneous_questions(cnv_obj=None, merchant_id=None, vendor=None, **kwargs):
    query = cnv_obj.turns[-1].formatted_text
    context = merchant_semantic_search(merchant_id, query)
    if not context:
        logger.warning("Can't retrieve context. Handing off")
        return default_handler(msg="merchant_semantic_search context retriever failed")
    logger.debug(f"Prompt Context: {context}")
    return answer_with_prompt(cnv_obj, gen_prompt(vendor, context), model=OpenAIModel.GPT4, turns=TURNS)
