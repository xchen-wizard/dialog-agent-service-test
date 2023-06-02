import logging
from .handle_answer_miscellaneous_questions import handle_answer_miscellaneous_questions
from dialog_agent_service.retrievers.product_retriever import product_lookup, product_variants_to_context
from textwrap import dedent
from ..chatgpt import answer_with_prompt
from dialog_agent_service.constants import OpenAIModel
logger = logging.getLogger(__name__)
max_conversation_chars_products = 1000
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
```{data}```
2. Answer the buyer's question using only the DATA section. Call it RESPONSE. Follow the following guidelines when crafting your response:
    - Answer as a kind and empathetic AI agent built by {vendor} and Wizard
    - End your answer with a short follow up question that continues the conversation. Vary follow-up questions each time by checking if the customer wants to start an order, offering assistance, asking about the customer's needs or preferences, or just letting the customer know you're here to help.
    - Keep your answer under 50 words.
3. Set CONTAINED to true if every information present in RESPONSE is also present in DATA.
4. Output a json in the following format: {{"ANSWER_POSSIBLE": true/false, "RESPONSE": "...", "CONTAINED": true/false}}
Output:
""").strip('\n')


def handle_answer_product_questions(predict_fn=None, merchant_id=None, cnv_obj=None, vendor=None, **kwargs):
    product_input = create_input_products(str(cnv_obj))
    product_mentions_output = predict_fn(product_input)[0]
    logger.info(f"Product question about: {product_mentions_output}")
    if product_mentions_output:
        product_mentions = product_mentions_output.split(",")
        product_context = [
            product_variants_to_context(product_lookup(merchant_id, product_mention))
            for product_mention in product_mentions
        ]
        context_str = "\n".join([c for c in product_context if c is not None])
        context_str = context_str.strip()
        if context_str:
            logger.debug(f"Prompt Context:{context_str}")
            prompt = gen_prompt(vendor, context_str)
            return answer_with_prompt(cnv_obj, prompt, model=OpenAIModel.GPT35, turns=TURNS, json_output=True)
    logger.warning("In the absence of product mentions, we resort to default QA task answer miscellaneous qa")
    return handle_answer_miscellaneous_questions(cnv_obj=cnv_obj, merchant_id=merchant_id, vendor=vendor)
