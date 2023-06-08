from __future__ import annotations

import logging
import os

from dialog_agent_service.utils.cart_utils import active_cart_to_virtual_cart

from .conversation_parser import Conversation
from .task_handlers import task_handler
from dialog_agent_service.search.SemanticSearch import SemanticSearch
max_conversation_chars_task = 600
logger = logging.getLogger(__name__)
semantic_search_obj = SemanticSearch()


class T5InferenceService:
    def __init__(self, data_dir, model_name=None, model_dir=None):
        """
        obj = T5InferenceService("google/flan-t5-xl", "model_dir", "test_data", ["Under Luna", "AAVRANI", "MYOS Pet"])
        :param model_name: pre-trained model name
        :param model_dir: model directory with finetuned model
        :param data_dir: directory with product sheet and example dialogues
        """
        if model_name is not None and model_dir is not None:
            from transformers import T5Tokenizer, T5ForConditionalGeneration
            self.tokenizer = T5Tokenizer.from_pretrained(model_name)
            self.model = T5ForConditionalGeneration.from_pretrained(model_dir)
        with open(f'{data_dir}/task_descriptions.txt') as f:
            logger.info(f'loading task_descriptions.txt from {data_dir}')
            self.task_descriptions = f.read()

    def predict(self, text):
        input = self.tokenizer(text, padding=True, return_tensors='pt')
        outputs = self.model.generate(**input, max_new_tokens=128)
        return self.tokenizer.batch_decode(outputs, skip_special_tokens=True)

    def infer(self, docs, vendor, merchant_id, predict_fn, current_cart={}, task_routing_config: dict = {}):
        """
        :param conversation: Conversation formatted as follows:
        Seller: Are you interested in..
        Buyer: Yes
        Seller: Ok..
        Buyer: I had a question
        Note that it should always end with Buyer
        :return: dict with different outputs of interest
        """

        merchant_id = str(merchant_id)
        cnv_obj = Conversation(docs)
        if cnv_obj.n_turns == 0:
            logger.error('Infer called with empty conversation. Aborting.')
            return dict()
        last_turn = cnv_obj.turns[-1]
        conversation = str(cnv_obj)
        logger.debug(f'Conversation Context: {conversation}')
        if last_turn.direction != 'inbound':
            logger.error(
                'Infer called after an outbound. Aborting. Please only call when the latest turn is inbound',
            )
            return dict()
        # first predict task
        input = create_input_task(
            conversation, task_descriptions=self.task_descriptions,
        )
        final_tasks = predict_fn(input)[0]
        tasks = [task.strip() for task in final_tasks.split(',')]
        logger.info(f'Tasks Detected:{tasks}')
        logger.debug(f'Task Routing Config:{task_routing_config}')
        cart = None
        model_predicted_cart = None
        is_suggested = False
        handoff = False
        cart_id = None
        cart_state_id = None
        message_type = None

        def fetch_task_response_type(task):
            return task_routing_config.get(task, {}).get('responseType', "assisted")

        if any(fetch_task_response_type(task) == 'cx' for task in tasks):
            response = None
            handoff = True
        else:
            res_acc = [
                task_handler(task, cnv_obj=cnv_obj, vendor=vendor, merchant_id=merchant_id,
                             predict_fn=predict_fn, current_cart=current_cart)
                for task in tasks
            ]
            logger.info(f"Accumulated result from task handlers: {res_acc}")
            final_tasks = ','.join([res['task']
                                   for res in res_acc if 'task' in res])
            res_handoff = next(
                (res for res in res_acc if res.get('handoff', False)), None)
            if res_handoff is not None:
                response = f"Handoff initiated. Tasks: {final_tasks}, {res_handoff.get('response', '')}"
                handoff = True
                if os.getenv('ENVIRONMENT') == 'prod':
                    is_suggested = True
            else:
                response = '\n'.join([
                    res['response']
                    for res in res_acc if 'response' in res
                ])
                cart = [res['cart'] for res in res_acc if 'cart' in res]
                if cart:
                    cart = cart[0]  # Only one task will return cart
                else:
                    cart = None
                model_predicted_cart = [
                    res['model_predicted_cart']
                    for res in res_acc if 'model_predicted_cart' in res
                ]
                if model_predicted_cart:
                    model_predicted_cart = model_predicted_cart[0]
                else:
                    model_predicted_cart = None
                cart_id = [res['cartId'] for res in res_acc if 'cartId' in res]
                if cart_id:
                    cart_id = cart_id[0]
                cart_state_id = [res['cartStateId']
                                 for res in res_acc if 'cartStateId' in res]
                if cart_state_id:
                    cart_state_id = cart_state_id[0]
                message_type = [res['messageType']
                                for res in res_acc if 'messageType' in res]
                if message_type:
                    message_type = message_type[0]

        is_suggested = is_suggested or not all(
            fetch_task_response_type(task) == 'automated' for task in tasks)
        handoff = handoff or is_suggested
        ret_dict = {
            'task': final_tasks,
            'response': response,
            'suggested': is_suggested,
            'handoff': handoff,
            'cartId': cart_id,
            'cartStateId': cart_state_id,
            'messageType': message_type
        }
        if cart is not None:
            ret_dict['cart'] = cart
        if model_predicted_cart is not None:
            ret_dict['model_predicted_cart'] = model_predicted_cart
        logger.debug(f'Returning json object: {ret_dict}')
        return ret_dict


def create_input_task(conversation, **kwargs):
    return [f"""
predict task based on task descriptions below:
{kwargs['task_descriptions']}
The below is an interaction between buyer and seller:
{conversation[-max_conversation_chars_task:]}
Write a comma separated list of tasks that the buyer wants us to do right now.
"""]
