from __future__ import annotations

import logging
from textwrap import dedent

from ..chatgpt import answer_with_prompt, llm_retrieval
from dialog_agent_service.constants import OpenAIModel
from dialog_agent_service.retrievers.merchant_retriever import merchant_semantic_search
from dialog_agent_service.retrievers.product_retriever import product_lookup
from dialog_agent_service.retrievers.product_retriever import product_variants_to_context
from dialog_agent_service.utils.utils import handler_to_task_name
from dialog_agent_service.das_exceptions import RetrieverFailure
from dialog_agent_service.conversational_agent.resolve_cart import match_mentions_to_products
logger = logging.getLogger(__name__)
max_conversation_chars_products = 1000
DATA_LIMIT = 10000
TURNS = 4


def create_input_products(conversation, **kwargs):
    return f"""
    products the question is about:
    The below is an interaction between buyer and seller at the end of which buyer has a question about some products.
    {conversation[-max_conversation_chars_products:]}
    Write a comma separated list of products that the buyer has question(s) on.
    """


def gen_prompt(vendor, data):
    return dedent(f"""
Read the conversation above and then do the following step-by-step.
1. Go through the DATA section below and decide whether there is enough information in DATA to answer buyer's question satisfactorily with a high degree of certainty. Call this ANSWER_POSSIBLE.
DATA
```{data[:DATA_LIMIT]}```
2. Answer the buyer's question using only the DATA section. Call it RESPONSE. Follow the following guidelines when crafting your response:
    - Answer as a kind and empathetic AI agent built by {vendor} and Wizard
    - End your answer with a short follow up question that continues the conversation. Vary follow-up questions each time by checking if the customer wants to add the product they are talking about to cart(if its not already in the cart), offering assistance, asking about the customer's needs or preferences, or just letting the customer know you're here to help.
    - Keep your answer under 50 words.
3. Set CONTAINED to true if every information present in RESPONSE is also present in DATA.
4. Output a json in the following format: {{"ANSWER_POSSIBLE": true/false, "RESPONSE": "...", "CONTAINED": true/false}}
Output:
""").strip('\n')


def handle_answer_product_questions(predict_fn=None, merchant_id=None, cnv_obj=None, vendor=None, llm_model=None, **kwargs):
    task = handler_to_task_name()
    product_input = create_input_products(str(cnv_obj))
    product_mentions_output = predict_fn(product_input)[0].strip()
    logger.info(f'Product question about: {product_mentions_output}')
    context_data = []
    if product_mentions_output:
        product_mentions = product_mentions_output.split(',')
        product_mentions = match_mentions_to_products(merchant_id, product_mentions, limit=2)
        logger.info(f"Products list expanded to {product_mentions} based on fuzzy match.")
        context_data = [
            product_variants_to_context(
                product_lookup(merchant_id, product_mention, limit=1))
            for product_mention in product_mentions
        ]
    # ToDo: make this an async call along with the product_lookup so that they can be called at the same time to reduce latancy
    query = cnv_obj.turns[-1].formatted_text
    qa_policy_context = merchant_semantic_search(
        merchant_id=merchant_id, query=query)
    context_data.append(qa_policy_context)
    context = "\n".join(filter(lambda c: c is not None and c.strip(), context_data))
    if len(context) == 0:
        raise RetrieverFailure
    logger.debug(f'Prompt Context:{context}')
    prompt = llm_retrieval(query=query, data=context) and gen_prompt(vendor, context)
    return {'task': task} | answer_with_prompt(cnv_obj, prompt, model=llm_model, turns=TURNS, json_output=True)
