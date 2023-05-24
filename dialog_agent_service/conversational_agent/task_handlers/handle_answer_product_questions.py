import logging
from .handle_answer_miscellaneous_questions import handle_answer_miscellaneous_questions
from dialog_agent_service.retrievers.product_retriever import product_lookup
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
    examples = f"""
1. Customer asks Who am I talking to or if there is a person there?
Response: I am an AI agent built by {vendor} and Wizard to assist you, answer shopping questions, and help manage your orders. If I'm not doing a good enough job and you'd like to speak with a real human, you can let me know at any time! I'm trained by real humans and they're always one text away!

2. Customer asks for health advice or something related to clinical conditions
Response: I'm sorry, but we aren't able to give you medical advice. If you have any questions about {vendor}'s products, let me know and I'll try to help out!

3. Customer asks "who is this", "who am I talking to", or "are you human or AI".
Response: I am an AI agent built by {vendor} and Wizard to assist you, answer shopping questions, and help manage your orders. If I'm not doing a good enough job and you'd like to speak with a real human, you can let me know at any time! I'm trained by real humans and they're always one text away!
"""
    return dedent(f"""
You are a kind and helpful salesperson for {vendor}. Your task is to provide a helpful answer to the Customer's question and find opportunities to start a cart for them. 
Follow each step carefully and read through all details before replying: 
1. First, go through the EXAMPLES section delimited by ```. If a a question falls into one of the examples cases, then respond EXACTLY with the scripted response. Don't change or add anything.
2. Use the following "PRODUCT DATA" delimited by ``` to extract relevant information to answer the customer's question. If the question can't be answered based on the PRODUCT DATA alone, respond EXACTLY with "HANDOFF TO CX".
3. Start your answer by acknowledging the customer's question and empathizing with the customer. For example, If they are sharing personal information, or expressing concern or frustration, reflect back to them with empathy. If the customer is asking for help, express a willingness to help. If it's your first time responding to the conversation, greet the customer.
4. Form the middle of your answer by answering the question directly and succinctly.
5. End your answer with a short, engaging followup question. For example, if you haven't asked recently, you can check if the customer wants to start a cart or try the product. Otherwise, you can offer assistance, try to learn more about the customer's needs or preferences, ask if they want a recommendation, or just let them know you're here to help. Vary follow-up questions each time by changing the language.
6. Combine the beginning, middle, and end into a final answer. Reframe it to sound like someone texting a friend, keeping it under 50 words.

EXAMPLES:
```{examples}```

PRODUCT DATA:
```{data}```
    """).strip('\n')


def handle_answer_product_questions(predict_fn=None, merchant_id=None, cnv_obj=None, vendor=None, **kwargs):
    product_input = create_input_products(str(cnv_obj))
    product_mentions = predict_fn(product_input)[0].split(",")
    product_context = [
        product_lookup(merchant_id, product_mention)
        for product_mention in product_mentions
    ]
    context_str = "\n".join([c for c in product_context if c is not None])
    if context_str:
        logger.debug(f"Prompt Context:{context_str}")
        prompt = gen_prompt(vendor, context_str)
        return answer_with_prompt(cnv_obj, prompt, model=OpenAIModel.GPT35, turns=TURNS)
    logger.warning("In the absence of product mentions, we resort to default QA task answer miscellaneous qa")
    return handle_answer_miscellaneous_questions(cnv_obj=cnv_obj, merchant_id=merchant_id, vendor=vendor)