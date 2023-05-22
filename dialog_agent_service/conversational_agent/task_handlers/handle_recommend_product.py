from dialog_agent_service.retrievers.product_retriever import product_semantic_search
from .default_handler import default_handler
from ..chatgpt import answer_with_prompt
from textwrap import dedent
from dialog_agent_service.constants import OpenAIModel
import logging
logger = logging.getLogger(__name__)


def gen_prompt(vendor, data):
    return dedent(f"""
    You are a salesperson for {vendor} 
    Use the following "Context" delimited by ``` to make a recommendation for a product that matches the Customer's requirements.
    If there is not enough information in the "Context" to make a recommendation, feel free to ask the Customer for more information.
    Limit responses to no more than 50 words. 
    
    Context:
    ```{data}```
    """).strip('\n')


def handle_recommend_product(cnv_obj=None, merchant_id=None, vendor=None, **kwargs):
    query = cnv_obj.turns[-1].formatted_text
    context = product_semantic_search(merchant_id, query)
    if not context:
        logger.warning("Can't retrieve context, handing off")
        return default_handler(msg='product_semantic_search context retriever failed')

    logger.debug(f"Prompt Context:{context}")
    return answer_with_prompt(cnv_obj, gen_prompt(vendor, context), model=OpenAIModel.GPT4)
