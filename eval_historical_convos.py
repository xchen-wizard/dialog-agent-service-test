from __future__ import annotations

import argparse
import asyncio
import logging
import os
import pickle
import time

import pandas as pd

from dialog_agent_service.actions.cart_actions import cart_delete
from dialog_agent_service.conversational_agent.conversation import handle_conversation_response
from dialog_agent_service.conversational_agent.conversation_utils import process_past_k_turns
from dialog_agent_service.conversational_agent.conversation_utils import run_inference
from dialog_agent_service.utils.cart_utils import sync_virtual_cart
ENDPOINT_ID = os.getenv('T5_VERTEX_AI_ENDPOINT_ID')
PROJECT_ID = os.getenv('VERTEX_AI_PROJECT_ID')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
file_handler = logging.FileHandler('goatful_test_10_convos_part2.log', 'w+')
stream_handler = logging.StreamHandler()
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

if __name__ == '__main__':
    # make sure the task routing config is up to date with the env you're testing
    task_routing_config = {
        'None': {'responseType': 'automated'}, 'Unknown': {'responseType': 'automated'},
        'CancelOrder': {'responseType': 'automated'}, 'ReturnOrder': {'responseType': 'automated'},
        'FinalizeOrder': {'responseType': 'automated'}, 'GiveOrderStatus': {'responseType': 'automated'},
        'RecommendProduct': {'responseType': 'assisted'}, 'ResolveOrderIssue': {'responseType': 'automated'},
        'UpdateAccountDetails': {'responseType': 'automated'}, 'AnswerProductQuestions': {'responseType': 'automated'},
        'AnswerServiceQuestions': {'responseType': 'automated'}, 'CreateOrUpdateOrderCart': {'responseType': 'automated'},
        'AnswerQuestionAboutOrder': {'responseType': 'automated'},
        'AnswerMiscellaneousQuestions': {'responseType': 'automated'},
    }

    with open('/Users/xchen/data/convos.pkl', 'rb') as f:
        conversations = pickle.load(f)
    # for testing
    merchant_id = '29'
    user_id = 198330
    historical_msgs, suggested_msgs, convo_ids, tasks, durations = [], [], [], [], []
    suggested, handoffs, carts, product_mentions, sessions = [], [], [], [], []
    for i, conversation in enumerate(conversations[10: 20]):
        logger.info('-----------------------------')
        current_cart = sync_virtual_cart(merchant_id, user_id)
        while current_cart:
            cart_id = cart_delete(current_cart.get('id'))
            logger.info(f'deleted existing cart: {cart_id}')
            current_cart = sync_virtual_cart(merchant_id, user_id)
        docs = []
        skip = False
        for j, turn in enumerate(conversation.turns):
            docs.append((turn.direction, turn.formatted_text))
            logger.info(turn)
            historical_msgs.append(str(turn))
            convo_ids.append(i)
            # skip the first turn because it's always a USER opt-in prompt somehow
            if j != 0 and turn.direction == 'inbound' and not skip:
                start = time.time()
                ret = asyncio.run(
                    handle_conversation_response(
                        merchant_id=merchant_id,
                        user_id=user_id,
                        service_channel_id=50,
                        k=-1,
                        window=24,
                        test_merchant='G.O.A.T. Fuel',
                        task_routing_config=task_routing_config,
                        test_args={
                            'docs': docs, 'vendor_name': 'G.O.A.T. Fuel', 'clear_history': False,
                        },
                    ),
                )
                end = time.time()
                # ret = asyncio.run(run_inference(
                #     docs, "G.O.A.T. Fuel", 29, project_id=PROJECT_ID, endpoint_id=ENDPOINT_ID,
                #     current_cart=current_cart, task_routing_config={}))
                current_cart = ret['cart'] if ret.get(
                    'cart') is not None else {}
                logger.info(f'current cart: {current_cart}')
                logger.info(f"Predicted Response: {ret.get('response', '')}")
                logger.info(f"Predicated Task: {ret['task']}")
                suggested_msgs.append(ret.get('response', ''))
                tasks.append(ret['task'])
                handoffs.append(ret.get('handoff'))
                durations.append(end-start)
                carts.append(ret.get('cart', ''))
                product_mentions.append(ret.get('model_predicted_cart', ''))
                suggested.append(ret.get('suggested', ''))

                if ret.get('handoff'):
                    logger.info(
                        'handoff happened, skipping sending the rest till session is ended')
                    skip = True

            else:
                suggested_msgs.append('')
                tasks.append('')
                handoffs.append('')
                durations.append('')
                carts.append('')
                product_mentions.append('')
                suggested.append('')
                if turn.get_session() == 'end':
                    # end of a session clear cart
                    cart_id = current_cart.get(
                        'id') and cart_delete(current_cart.get('id'))
                    # set current_cart to empty - no need to do it unless you use run_inference directly
                    # current_cart = {}
                    logger.info(
                        f'session ends. deleted cart: {cart_id}, set in memory cart to empty')
                    skip = False
            sessions.append(turn.get_session())

    df = pd.DataFrame({
        'convoId': convo_ids,
        'historical_messages': historical_msgs,
        'bot_messages': suggested_msgs,
        'tasks': tasks,
        'handoffs': handoffs,
        'suggested': suggested,
        'durations': durations,
        'carts': carts,
        'product_mentions': product_mentions,
        'sessions': sessions,
    })

    df.to_csv(
        '/Users/xchen/data/historical_convos_goatfuel_part2_v2.csv', index=False)
    df.to_json(
        '/Users/xchen/data/historical_convos_goatfuel_part2_v2.json',
        lines=True, orient='records',
    )
