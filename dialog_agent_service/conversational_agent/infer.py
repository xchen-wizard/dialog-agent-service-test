from __future__ import annotations

import glob
import logging

logger = logging.getLogger(__name__)


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
            self.task_descriptions = f.read()
        self.response_prediction_prompt = dict()
        fact_sheets = glob.glob(f'{data_dir}/*/fact_sheet.txt')
        for fact_sheet in fact_sheets:
            vendor = fact_sheet.split('/')[2]
            with open(fact_sheet) as f:
                facts = f.read()
            self.response_prediction_prompt[vendor] = f'{vendor} response: {facts}\n'

    def predict(self, text):
        input = self.tokenizer(text, padding=True, return_tensors='pt')
        outputs = self.model.generate(**input, max_new_tokens=128)
        return self.tokenizer.batch_decode(outputs, skip_special_tokens=True)

    def infer(self, conversation, vendor, predict_fn):
        """
        :param conversation: Conversation formatted as follows:
        Seller: Are you interested in..
        Buyer: Yes
        Seller: Ok..
        Buyer: I had a question
        Note that it should always end with Buyer
        :return: dict with different outputs of interest
        """
        # first predict task
        task = predict_fn(
            create_input_task(
                conversation, task_descriptions=self.task_descriptions,
            ),
        )[0]
        if task not in {'StartOrBuildOrder', 'FinalizeOrder'}:
            conversation += 'Seller: '
            response = predict_fn(
                self.response_prediction_prompt[vendor] + conversation,
            )[0]
            return {'task': task, 'response': response}
        if task == 'FinalizeOrder':
            return {'task': task}
        if task == 'StartOrBuildOrder':
            products = predict_fn(create_input_cart(conversation))[0]
            if products == 'None':
                return {'task': task, 'cart': []}
            else:
                products_list = products.split(',')
            # TODO: We are not finetuning on quantity yet. This will change in future and then this will not be hardcoded here.
            qty_text = [
                f"""
question answering:
{conversation}
How many {product} does the buyer want?
"""
                for product in products_list
            ]
            qty_list = predict_fn(qty_text)
            return {'task': task, 'cart': list(zip(products_list, qty_list))}
        # if all fails
        logger.error(f'the returned task {task} is not accounted for')
        return {}


def create_input_task(conversation, **kwargs):
    return f"""
question answering:
{kwargs['task_descriptions']}
The below is an interaction between buyer and seller:
{conversation}
Write a comma separated list of tasks that the buyer wants us to do right now.
"""


def create_input_cart(conversation, **kwargs):
    return f"""
question answering:
{conversation}
Write a comma separated list of products that the buyer is interested in purchasing.
"""
