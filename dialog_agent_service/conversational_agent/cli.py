import argparse
import os
from dialog_agent_service.conversational_agent.conversation import handle_conversation_response
from dialog_agent_service.conversational_agent.conversation_utils import run_inference
import asyncio
import logging
ENDPOINT_ID = os.getenv('T5_VERTEX_AI_ENDPOINT_ID')
PROJECT_ID = os.getenv('VERTEX_AI_PROJECT_ID')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-id", "--merchant_id", help="vendor id to run interpreter", required=True)
    parser.add_argument("-v", "--vendor", help="vendor name to run interpreter", required=True)
    parser.add_argument("-u", "--user_id", help="user id to run interpreter", required=True)
    parser.add_argument("-sc", "--service_channel_id", help="service channel id to run interpreter", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    task_routing_config = {}
    """
    # Uncomment the below if needed.
    task_routing_config = {
        "CreateOrUpdateOrderCart": {"responseType": "automated"},
        "RecommendProduct": {"responseType": "automated"},
        "AnswerProductQuestions": {"responseType": "automated"},
        "AnswerMiscellaneousQuestions": {"responseType": "automated"},
        "None": {"responseType": "automated"}
    }
    """

    response = """
Thanks for texting!
How can we help you today?
"""
    docs = []
    current_cart = []
    while 1:
        print(response)
        docs.append(('outbound', response))
        utt = input()
        docs.append(('inbound', utt))
        print(f"Current Cart: {current_cart}")
        test_args = { 'docs': docs, 'vendor_name': args.vendor, 'clear_history': False}
        ret = asyncio.run(handle_conversation_response(args.merchant_id, int(args.user_id), int(args.service_channel_id), -1, 24, test_merchant='',task_routing_config=task_routing_config, test_args=test_args))
        '''ret = asyncio.run(run_inference(
            docs, args.vendor, args.merchant_id, project_id=PROJECT_ID, endpoint_id=ENDPOINT_ID,
            current_cart=current_cart, task_routing_config=task_routing_config))'''
        if 'cart' in ret:
            current_cart = ret['cart']
        print(ret)
        if ret["suggested"]:
            print("---Enter response manually below---")
            response = input()
        else:
            response = ret["response"]