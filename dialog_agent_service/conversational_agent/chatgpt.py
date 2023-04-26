import openai
from .conversation_parser import Conversation, Turn

model = "gpt-3.5-turbo"


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
    response = openai.Completion.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt}
        ] + conv_to_chatgpt_format(cnv_obj, 5)
    )
    return response["choices"][0]["message"]["content"]


def product_qa(cnv_obj: Conversation, data: str, vendor: str):
    prompt = f"""
    You are a helpful salesperson for {vendor} and are trying to help the user find the right product.
    Use the given product data below to answer user's question. If the question can't be answered based on the data given, say "HANDOFF TO CX". Limit responses to no more than 50 words.
    Product Data: {data}
    """
    return answer_with_prompt(cnv_obj, prompt)


def merchant_qa(cnv_obj: Conversation, data: str, vendor: str):
    prompt = f"""
    You are a kind and helpful e-commerce customer support agent that works for {vendor}.
    Answer the question based on the  context below, and if the question can't be answered based on the context, say "HANDOFF TO CX".
    Limit responses to no more than 50 words. Use the Instruction sections to further refine your response.
    Context: {data}
    Instructions:
- if we are responding to an inbound for the first time, start with a greeting like "Hi there!" or "Thanks for your question!" before answering the question. Otherwise if we're in the middle of a conversation answer the question directly.
- if the customer is asking about how to get free shipping, when we answer their question about free shipping thresholds, we should also check if there are other ongoing promotions and let them about any that exist (like a first text order discount).
- unless the customer specifies otherwise, we should assume they are asking about shipping to the USA
    """
    return answer_with_prompt(cnv_obj, prompt)


def recommend(cnv_obj: Conversation, data: str, vendor: str):
    prompt = f"""
    You are a salesperson for {vendor}. Help the user find the right product based on the context provided below.
    If there is not enough data in the context to make a recommendation, feel free to ask the user for more information
    so you can make a recommendation.
    Limit responses to no more than 50 words. 
    Context: {data}
    """
    return answer_with_prompt(cnv_obj, prompt)