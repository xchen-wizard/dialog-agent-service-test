from __future__ import annotations

import glob
import json
import logging
from collections import namedtuple
import os
from typing import List
from typing import Tuple

from fuzzywuzzy import fuzz
from fuzzywuzzy import process

from .conversation_parser import Conversation
from .response import gen_cart_response
from .response import gen_non_specific_product_response
from .response import gen_variant_selection_response
from dialog_agent_service.db import get_merchant, merchant_semantic_search, product_search, product_semantic_search
from dialog_agent_service.search.SemanticSearch import SemanticSearch
from .chatgpt import product_qa, merchant_qa, recommend

max_conversation_chars_task = 600
max_conversation_chars_cart = 1500
max_conversation_chars_products = 1000
logger = logging.getLogger(__name__)

ProductResponseUnion = namedtuple(
    'ProductResponseUnion', ['products', 'response'],
)
FUZZY_MATCH_THRESHOLD = 85
MAX_CONVERSATION_CHARS = 600
FAQ_THRESHOLD = 1.6
# ToDo: not ideal, replace later
with open('../test_data/products_variants_prices.json') as f:
    VARIANTS_OBJ = json.load(f)
    logger.info('loaded product variants and prices!')

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

    def infer(self, docs, vendor, merchant_id, predict_fn, task_routing_config: dict = {}):
        """
        :param conversation: Conversation formatted as follows:
        Seller: Are you interested in..
        Buyer: Yes
        Seller: Ok..
        Buyer: I had a question
        Note that it should always end with Buyer
        :return: dict with different outputs of interest
        """

        TASKS = ['CreateOrUpdateOrderCart', 'AnswerProductQuestions', 'AnswerSellerQuestions', 'RecommendProduct']
    
        for t in TASKS:
            if not task_routing_config.get(t):
                task_routing_config[t] = {'responseType': 'assisted'}

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
        input, _ = create_input_target_task(
            conversation, '', task_descriptions=self.task_descriptions,
        )
        task = predict_fn(input)[0]
        logger.info(f"DETECTED TASK:{task}")
        logger.info(f"TASK ROUTING CONFIG:{task_routing_config}")
        response = ''
        cart = []
        model_predicted_cart = []
        source = 'model'
        is_suggested = True

        if task_routing_config[task]['responseType'] == 'cx':
            return {'task': task, 'suggested': False}

        if 'CreateOrUpdateOrderCart' in task:
            product_input, _ = create_input_target_cart(conversation, '')
            products = predict_fn(product_input)[0]
            if products != 'None':
                qty_input, _ = create_input_target_cart(
                    conversation, products + ';', qty_infer=True,
                )
                qty_list = predict_fn(qty_input)
                model_predicted_cart = list(zip(products.split(','), qty_list))
                for product, qty in model_predicted_cart:
                    if qty.isdigit():
                        cart.append((product, int(qty)))
                    else:
                        logger.error(
                            f'Quantity {qty} predicted for product {product} not of the right type. Skipping.',
                        )
                cart, response = resolve_cart(merchant_id, cart, response)

        conversation += 'Seller: '
        if 'AnswerProductQuestions' in task:
            product_input, _ = create_input_target_products(conversation, "")
            products = predict_fn(product_input)[0]
            logger.info(f"PRODUCT FUZZY-WUZZY SEARCH: {products}")
            context = ""
            for product in products.split(","):
                product_results = product_semantic_search(merchant_id, product)[
                    'productVariantSemanticSearch'][0:1]  # first result only
                logger.info(
                    f"PRODUCT:{product}: SEMANTIC SEARCH RESULTS: {product_results}")
                for pr in product_results:
                    context += format_product_result(pr)
                    context += "\n"

            logger.info(f"CONTEXT:{context}")

            conversation += "Seller: "
            llm_response = product_qa(cnv_obj, context, vendor)

            logger.info(f"LLM RESPONSE: {llm_response}")

            # TODO - check llm_response
            response += llm_response

        if 'AnswerSellerQuestions' in task:
            # First check FAQ: we give precedence to it
            answer, score = None, 0.0
            try:
                merchant_site_id = get_merchant(merchant_id)['site_id']
                answer, score = semantic_search_obj.faq_search(
                    merchant_site_id, last_turn.formatted_text,
                )
            except Exception as e:
                logger.error(f'Error querying ES: {e}')
            if answer and score > FAQ_THRESHOLD:
                logger.info('found answer through ES!')
                response += answer
                source = 'faq'
            else:
                merchant_data = merchant_semantic_search(
                    merchant_id, last_turn.formatted_text)
                response += merchant_qa(cnv_obj, merchant_data, vendor)
        if 'RecommendProduct' in task:
            product_query = last_turn.formatted_text
            product_results = product_semantic_search(merchant_id, product_query)[
                'productVariantSemanticSearch'][0:3]  # TODO: first 3 only
            logger.info(
                f"QUERY:{product_query}: SEMANTIC SEARCH RESULTS: {product_results}")

            context = ""
            for pr in product_results:
                context += format_product_result(pr)
                context += '\n'

            logger.info(f"CONTEXT:{context}")

            llm_response = recommend(cnv_obj, context, vendor)
            logger.info(f"LLM RESPONSE: {llm_response}")

            # TODO - check llm_response
            response += llm_response

        ret_dict = {
            'task': task,
            'cart': cart,
            'model_predicted_cart': model_predicted_cart,
            'response': response,
            'source': source,
            'suggested': task_routing_config[task]['responseType'] == 'assisted'
        }
        if not ret_dict['response']:
            del ret_dict['response']
        if not ret_dict['cart']:
            del ret_dict['cart']
        logger.debug(f'Returning json object: {ret_dict}')
        return ret_dict


def format_product_result(pr):
    output = ""
    display_name = pr.get("product", {}).get("name") + " - " + pr.get("name")
    desc = pr.get("description")
    output += f"product name is {display_name},"
    output += f"product description is {desc}"

    return output


def create_input_target_task(conversation, target_str, **kwargs):
    return [f"""
predict task based on task descriptions below:
{kwargs['task_descriptions']}
The below is an interaction between buyer and seller:
{conversation[-max_conversation_chars_task:]}
Write a comma separated list of tasks that the buyer wants us to do right now.
"""], [target_str]


def create_input_target_cart(conversation, target_str, **kwargs):
    inputs = [f"""
answer products of interest:
{conversation[-max_conversation_chars_cart:]}
Write a comma separated list of products that the buyer is interested in purchasing.
"""] if not kwargs.get('qty_infer', False) else []
    products_qty = target_str.split(';')
    products = products_qty[0].strip()
    targets = [products]
    if len(products_qty) > 1:
        targets.extend([s.strip() for s in products_qty[1].strip().split(',')])
        products = products.split(',')
        for product in products:
            inputs.append(
                f"""
answer product quantity:
{conversation[-max_conversation_chars_cart:]}
How many {product} does the buyer want?
                """,
            )
    return inputs, targets


def create_input_target_products(conversation, target_str, **kwargs):
    return [
        f"""
        products the question is about:
        The below is an interaction between buyer and seller at the end of which buyer has a question about some products.
        {conversation[-max_conversation_chars_products:]}
        Write a comma separated list of products that the buyer has question(s) on.
        """
    ], [target_str]


def resolve_cart(merchant_id: str, cart: list[tuple[str, int]], response: str):
    resolved_cart = []
    for product, qty in cart:
        products, product_response = match_product_variant(
            merchant_id, product,
        )
        if products:
            resolved_cart.extend([(p[0], p[1], qty) for p in products])
        if product_response:
            response = '\n' + product_response
    # TODO: Cart summary will be enabled only after backednd integration
    response = gen_cart_response(
        resolved_cart,
    ) + '\n' + response
    return [(name, qty) for (name, _, qty) in resolved_cart], response


def match_product_variant(merchant_id: str, product_name: str) -> ProductResponseUnion:
    merchant_id = str(merchant_id)  # type: ignore
    product_matches = process.extract(
        product_name, VARIANTS_OBJ[merchant_id].keys(), scorer=fuzz.token_set_ratio,
    )
    significant_matches = [
        tup[0]
        for tup in product_matches if tup[1] > FUZZY_MATCH_THRESHOLD
    ]
    if len(significant_matches) > 2:
        logger.debug(
            f'{product_name} matched to many product names: {significant_matches}. No match returned',
        )
        return ProductResponseUnion(
            None, gen_non_specific_product_response(
                product_name, significant_matches,
            ),
        )
    else:
        products = []
        response = ''
        for product_match in significant_matches:
            variants_dict = VARIANTS_OBJ[merchant_id][product_match]
            if len(variants_dict) == 1:
                products.append(
                    (
                        product_match + ' - ' + min(variants_dict.keys()),
                        min(variants_dict.values()),
                    ),
                )
            else:
                variant_matches = [
                    (
                        product_match + ' - ' + tup[0], variants_dict[tup[0]],
                    )
                    for tup in process.extract(product_name, variants_dict.keys(), scorer=fuzz.token_set_ratio)
                    if tup[1] > FUZZY_MATCH_THRESHOLD
                ]
                if len(variant_matches) > 0:
                    products.extend(variant_matches)
                else:
                    response += '\n' + gen_variant_selection_response(
                        product_match, variants_dict,
                    )

        return ProductResponseUnion(products, response)
