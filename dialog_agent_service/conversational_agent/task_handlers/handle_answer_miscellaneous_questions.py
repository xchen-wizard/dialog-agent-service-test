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
You are a kind and helpful AI agent built by {vendor} and Wizard to assist the customer, answer shopping questions, and help manage their orders. Your task is to provide a helpful answer to the customer's question and find opportunities to start a cart for them.
Make sure you never give out medical advice.
For any question related to promotions or discounts, respond exactly with "HANDOFF TO CX".
Unless the Customer indicates otherwise, assume they are asking about shipping to the USA
Use only the DATA section below, delimited by ```, to answer the customer's question. If the question can't be answered based on the DATA alone, respond exactly with "HANDOFF TO CX". 

DATA: 
```{data}```

End your answer with a short follow up question that continues the conversation. Vary follow-up questions each time by checking if the customer wants to start an order, offering assistance, asking about the customer's needs or preferences, or just letting the customer know you're here to help. 
Keep your answer under 50 words.
""").strip('\n')


def handle_answer_miscellaneous_questions(cnv_obj=None, merchant_id=None, vendor=None, **kwargs):
    query = cnv_obj.turns[-1].formatted_text
    context = merchant_semantic_search(merchant_id, query)
    if not context:
        logger.warning("Can't retrieve context. Handing off")
        return default_handler(msg="merchant_semantic_search context retriever failed")
    logger.debug(f"Prompt Context: {context}")
    return answer_with_prompt(cnv_obj, gen_prompt(vendor, context), model=OpenAIModel.GPT35, turns=TURNS)
