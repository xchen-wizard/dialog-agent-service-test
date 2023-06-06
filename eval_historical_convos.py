import argparse
import os
from dialog_agent_service.conversational_agent.conversation import handle_conversation_response
from dialog_agent_service.conversational_agent.conversation_utils import run_inference
from dialog_agent_service.utils.cart_utils import sync_virtual_cart
from dialog_agent_service.actions.cart_actions import cart_delete
import asyncio
import logging
import pickle
ENDPOINT_ID = os.getenv('T5_VERTEX_AI_ENDPOINT_ID')
PROJECT_ID = os.getenv('VERTEX_AI_PROJECT_ID')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


if __name__ == '__main__':
    task_routing_config = {
        "CreateOrUpdateOrderCart": {"responseType": "automated"},
        "RecommendProduct": {"responseType": "automated"},
        "AnswerProductQuestions": {"responseType": "automated"},
        "AnswerMiscellaneousQuestions": {"responseType": "automated"},
        "None": {"responseType": "automated"}
    }
    with open('/Users/xchen/data/convos.pkl', 'rb') as f:
        conversations = pickle.load(f)
    # for testing
    merchant_id = '29'
    user_id = 198330

    for conversation in conversations:
        print("-----------------------------")
        current_cart = sync_virtual_cart(merchant_id, user_id)
        if current_cart:
            cart_id = cart_delete(current_cart.get('id'))
            logger.info(f"deleted existing cart: {cart_id}")
        docs = []
        for turn in conversation.turns:
            docs.append((turn.direction, turn.formatted_text))
            print(turn)
            if turn.direction == "inbound":
                ret = asyncio.run(handle_conversation_response(
                    merchant_id=merchant_id,
                    user_id=user_id,
                    service_channel_id=50,
                    k=-1,
                    window=24,
                    test_merchant="G.O.A.T. Fuel",
                    task_routing_config=task_routing_config,
                    test_args={"docs": docs, "vendor_name": "G.O.A.T. Fuel", "clear_history": False}))
                # ret = asyncio.run(run_inference(
                #     docs, "G.O.A.T. Fuel", 29, project_id=PROJECT_ID, endpoint_id=ENDPOINT_ID,
                #     current_cart=current_cart, task_routing_config={}))
                print(f"Predicted Response: {ret.get('response', '')}")
                print(f"Predicated Task: {ret['task']}")
                if 'cart' in ret:
                    current_cart = ret['cart']