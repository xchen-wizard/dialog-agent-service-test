from __future__ import annotations

import argparse
import asyncio
import logging
import os

from dialog_agent_service.constants import CLEAR_HISTORY
from dialog_agent_service.constants import HISTORY_CLEARED
from dialog_agent_service.conversational_agent.conversation import handle_conversation_response
from dialog_agent_service.conversational_agent.conversation_utils import process_past_k_turns
from dialog_agent_service.conversational_agent.conversation_utils import run_inference
ENDPOINT_ID = os.getenv('T5_VERTEX_AI_ENDPOINT_ID')
PROJECT_ID = os.getenv('VERTEX_AI_PROJECT_ID')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-id', '--merchant_id',
        help='vendor id to run interpreter', required=True,
    )
    parser.add_argument(
        '-v', '--vendor', help='vendor name to run interpreter', required=True,
    )
    parser.add_argument(
        '-u', '--user_id',
        help='user id to run interpreter', required=False,
    )
    parser.add_argument(
        '-sc', '--service_channel_id',
        help='service channel id to run interpreter', required=False,
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    task_routing_config = {
        'CreateOrUpdateOrderCart': {'responseType': 'automated'},
        'RecommendProduct': {'responseType': 'automated'},
        'AnswerProductQuestions': {'responseType': 'automated'},
        'AnswerMiscellaneousQuestions': {'responseType': 'automated'},
        'None': {'responseType': 'automated'},
    }

    response = """
Thanks for texting!
How can we help you today?
"""
    docs = []
    current_cart = {}
    while 1:
        print(response)
        docs.append(('outbound', response))
        if response == HISTORY_CLEARED:  # terminate the test run
            break
        utt = input()
        docs.append(('inbound', utt))
        print(f'Current Cart: {current_cart}')
        clear_history = utt.strip().upper() == CLEAR_HISTORY

        test_args = {
            'docs': docs, 'vendor_name': args.vendor,
            'clear_history': clear_history,
        }

        if args.user_id and args.service_channel_id:
            ret = asyncio.run(
                handle_conversation_response(
                    args.merchant_id, int(args.user_id), int(
                        args.service_channel_id,
                    ), -1, 24,
                    test_merchant='', task_routing_config=task_routing_config, test_args=test_args,
                ),
            )
        else:
            ret = asyncio.run(
                run_inference(
                    docs, args.vendor, args.merchant_id, project_id=PROJECT_ID, endpoint_id=ENDPOINT_ID,
                    current_cart=current_cart, task_routing_config=task_routing_config,
                ),
            )

        if 'cart' in ret:
            current_cart = ret['cart']
        print(ret)
        if ret['handoff']:
            print('---Enter response manually below---')
            response = input()
        else:
            response = ret['response']
