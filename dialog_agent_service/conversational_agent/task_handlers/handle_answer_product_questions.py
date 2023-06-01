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
Follow the following steps:
1. Find out the span from the DATA section below that is relevant for answering the user's question and call it SPAN. SPAN is a tuple of starting and ending position in the DATA. If there is no relevant information in DATA, then SPAN is null.
DATA
```{data}```

2. If SPAN is null, respond exactly with "HANDOFF TO CX".
3. Find out if user's question can be answered with complete certainty using SPAN, call it ANSWER_POSSIBLE.
4. If ANSWER_POSSIBLE is false then respond exactly with "HANDOFF TO CX". 
5. If ANSWER_POSSIBLE is true, then find out if the user's question is asking for medical advice, call it MEDICAL.
6. If MEDICAL is true, then respond exactly with "HANDOFF TO CX".
7. If MEDICAL is false, but SPAN indicates that we don't have a great answer to user's question, then respond exactly with "HANDOFF TO CX". 
8. Otherwise, create your response using SPAN following these guidelines:
    - Be Kind and emphathetic
    - End your answer with a short follow up question that continues the conversation, preferably find opportunities to add things to the cart. 
    - Keep your answer under 50 words.
9. Solve the entailment problem whether SPAN entails RESPONSE, and call it SPAN_ENTAILS_RESPONSE.
10. Format your output as a json, e.g. {{"SPAN": "(start_position, end_position)", "ANSWER_POSSIBLE": true/false, "MEDICAL": true/false, "RESPONSE": "...", "SPAN_ENTAILS_RESPONSE": true/false}}
Output:""").strip('\n')


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
